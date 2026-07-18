from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response

from app.config import settings
from app.models import FirstResponderDispatchRequest, HealthResponse, IncidentRequest, OperatorFeedback, SimulationRequest
from app.responders.cap import ResponderUnavailable, build_cap_alert, send_cap
from app.responders.webeoc import WebEOCConfig, WebEOCUnavailable, send_to_webeoc
from app.security.hiddenlayer import HiddenLayerUnavailable, scan_interaction
from app.service import FloodOpsService
from app.streaming.kafka import KafkaUnavailable
from app.storage.supabase import SupabaseUnavailable


app = FastAPI(title="Austin FloodOps", version="0.1.0")
service = FloodOpsService.create(settings)


@app.get("/", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    integrations = [
        {"name": "NWS alerts", "configured": True, "verified": False, "detail": "Official weather.gov active-alerts endpoint"},
        {"name": "USGS water services", "configured": True, "verified": False, "detail": f"Instantaneous values for site {settings.usgs_site_id}"},
        {"name": "NVIDIA Nemotron", "configured": settings.has_nvidia_key, "verified": False, "detail": settings.nvidia_base_url},
        {"name": "Red Hat Streams/Kafka", "configured": settings.has_kafka, "verified": False, "detail": "Optional event-bus adapter"},
        {"name": "Supabase", "configured": settings.has_supabase, "verified": False, "detail": "SQLite local durable fallback is active"},
        {"name": "NemoClaw/OpenShell", "configured": settings.has_openshell, "verified": False, "detail": "Set OPENSHELL_GATEWAY after selecting a gateway"},
        {"name": "HiddenLayer runtime", "configured": settings.has_hiddenlayer, "verified": False, "detail": "Tenant-supplied Interactions API endpoint"},
        {"name": "First-responder CAP webhook", "configured": settings.has_first_responder, "verified": False, "detail": "Approval-gated generic CAP 1.2 sender"},
        {"name": "Texas TDEM WebEOC", "configured": settings.has_webeoc, "verified": False, "detail": "Approval-gated AddData SOAP adapter"},
    ]
    status = "ok" if settings.has_nvidia_key else "degraded"
    return HealthResponse(status=status, mode=settings.data_mode, integrations=integrations)


@app.post("/api/assess")
async def assess(request: IncidentRequest) -> dict:
    events, decision, error = await service.assess(request.mode, request.scenario_id)
    return {"events": events, "decision": decision, "error": error, "live": request.mode == "live" and not error}


@app.post("/api/simulate")
async def simulate(request: SimulationRequest) -> dict:
    events = await service.gather(request.mode, request.scenario_id)
    if events:
        service.store.save_events(events)
    estimate = service.simulate(events, mode=request.mode, scenario_id=request.scenario_id, horizon_minutes=request.horizon_minutes)
    return {"events": events, "estimate": estimate}


@app.get("/api/events")
async def events() -> list[dict]:
    return [event.model_dump(mode="json") for event in service.store.list_events()]


@app.get("/api/decisions")
async def decisions() -> list[dict]:
    return [decision.model_dump(mode="json") for decision in service.store.list_decisions()]


@app.post("/api/integrations/kafka/probe")
async def kafka_probe() -> dict:
    if not settings.has_kafka:
        return {"status": "unconfigured", "detail": "Set KAFKA_BOOTSTRAP_SERVERS before running the producer/consumer probe."}
    try:
        events = service.store.list_events(limit=1)
        published = service.event_bus().publish(events) if events else 0
        consumed = list(service.event_bus().consume(max_records=max(1, published))) if published else []
        return {"status": "verified", "published": published, "consumed": len(consumed), "event_ids": [item.event_id for item in consumed]}
    except KafkaUnavailable as exc:
        return {"status": "blocked", "detail": str(exc)}


@app.post("/api/integrations/hiddenlayer/probe")
async def hiddenlayer_probe() -> dict:
    if not settings.has_hiddenlayer:
        return {"status": "unconfigured", "detail": "Set HIDDENLAYER_INTERACTIONS_URL and HIDDENLAYER_API_KEY."}
    try:
        result = await scan_interaction(
            service.hiddenlayer(), input_text="Austin FloodOps integration probe", output_text="allow"
        )
        return {"status": "verified", "result": result}
    except HiddenLayerUnavailable as exc:
        return {"status": "blocked", "detail": str(exc)}


@app.post("/api/integrations/supabase/probe")
async def supabase_probe() -> dict:
    if not settings.has_supabase:
        return {"status": "unconfigured", "detail": "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."}
    try:
        return await service.supabase().probe()
    except SupabaseUnavailable as exc:
        return {"status": "blocked", "detail": str(exc)}


@app.post("/api/decisions/{incident_id}/approve")
async def approve(incident_id: str) -> dict:
    decision = next((item for item in service.store.list_decisions() if item.incident_id == incident_id), None)
    if decision is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    result = service.approve(decision)
    return {"incident_id": incident_id, "status": result.status, "reason": result.reason}


@app.get("/api/decisions/{incident_id}/cap")
async def cap_export(incident_id: str) -> Response:
    decision = next((item for item in service.store.list_decisions() if item.incident_id == incident_id), None)
    if decision is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return Response(content=build_cap_alert(decision), media_type="application/cap+xml")


@app.post("/api/decisions/{incident_id}/first-responder")
async def first_responder(incident_id: str, payload: FirstResponderDispatchRequest) -> dict:
    decision = next((item for item in service.store.list_decisions() if item.incident_id == incident_id), None)
    if decision is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    if not payload.confirm:
        return {"status": "blocked", "detail": "Set confirm=true after reviewing the CAP payload."}
    if decision.policy_status != "allowed":
        return {"status": "blocked", "detail": "Approve the reversible action before sending a responder message."}
    channel = "first-responder-cap"
    if service.store.delivery_exists(incident_id, channel):
        return {"status": "already_delivered", "incident_id": incident_id}
    try:
        status = await send_cap(
            url=settings.first_responder_webhook_url,
            token=settings.first_responder_webhook_token,
            incident_id=incident_id,
            payload=build_cap_alert(decision),
        )
    except ResponderUnavailable as exc:
        return {"status": "blocked", "detail": str(exc)}
    service.store.record_delivery(incident_id, channel, status)
    return {"status": "delivered", "incident_id": incident_id, "response_status": status}


@app.post("/api/decisions/{incident_id}/webeoc")
async def webeoc(incident_id: str, payload: FirstResponderDispatchRequest) -> dict:
    decision = next((item for item in service.store.list_decisions() if item.incident_id == incident_id), None)
    if decision is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    if not payload.confirm:
        return {"status": "blocked", "detail": "Set confirm=true after reviewing the CAP payload."}
    if decision.policy_status != "allowed":
        return {"status": "blocked", "detail": "Approve the reversible action before sending to WebEOC."}
    channel = "tdem-webeoc"
    if service.store.delivery_exists(incident_id, channel):
        return {"status": "already_delivered", "incident_id": incident_id}
    config = WebEOCConfig(
        api_url=settings.webeoc_api_url,
        username=settings.webeoc_username,
        password=settings.webeoc_password,
        position=settings.webeoc_position,
        incident=settings.webeoc_incident,
        board_name=settings.webeoc_board_name,
        input_view_name=settings.webeoc_input_view_name,
    )
    try:
        result = await send_to_webeoc(config, incident_id=incident_id, cap_payload=build_cap_alert(decision))
    except WebEOCUnavailable as exc:
        return {"status": "blocked", "detail": str(exc)}
    service.store.record_delivery(incident_id, channel, result)
    return {"status": "delivered", "incident_id": incident_id, "webeoc_result": result}


@app.post("/api/decisions/{incident_id}/feedback")
async def feedback(incident_id: str, payload: OperatorFeedback) -> dict:
    decision = next((item for item in service.store.list_decisions() if item.incident_id == incident_id), None)
    if decision is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    feedback_id = service.feedback(incident_id, payload)
    if settings.has_supabase:
        try:
            await service.supabase().save_feedback(incident_id, payload)
        except SupabaseUnavailable:
            pass
    return {"feedback_id": feedback_id, "memory": payload.correction}
