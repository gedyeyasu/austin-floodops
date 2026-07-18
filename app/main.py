from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.config import settings
from app.models import HealthResponse, IncidentRequest, OperatorFeedback
from app.service import FloodOpsService


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
    ]
    status = "ok" if settings.has_nvidia_key else "degraded"
    return HealthResponse(status=status, mode=settings.data_mode, integrations=integrations)


@app.post("/api/assess")
async def assess(request: IncidentRequest) -> dict:
    events, decision, error = await service.assess(request.mode, request.scenario_id)
    return {"events": events, "decision": decision, "error": error, "live": request.mode == "live" and not error}


@app.get("/api/events")
async def events() -> list[dict]:
    return [event.model_dump(mode="json") for event in service.store.list_events()]


@app.get("/api/decisions")
async def decisions() -> list[dict]:
    return [decision.model_dump(mode="json") for decision in service.store.list_decisions()]


@app.post("/api/decisions/{incident_id}/approve")
async def approve(incident_id: str) -> dict:
    decision = next((item for item in service.store.list_decisions() if item.incident_id == incident_id), None)
    if decision is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    result = service.approve(decision)
    return {"incident_id": incident_id, "status": result.status, "reason": result.reason}


@app.post("/api/decisions/{incident_id}/feedback")
async def feedback(incident_id: str, payload: OperatorFeedback) -> dict:
    decision = next((item for item in service.store.list_decisions() if item.incident_id == incident_id), None)
    if decision is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    feedback_id = service.feedback(incident_id, payload)
    return {"feedback_id": feedback_id, "memory": payload.correction}

