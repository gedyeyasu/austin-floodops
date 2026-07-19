from dataclasses import replace
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.auth import Actor, Role, current_actor, require_action
from app.config import settings
from app.model.nemotron import IntegrationUnavailable, _decision_payload, _extract_json, _ground_citations, _ground_model_references, _select_evidence, build_incident_request
from app.models import FloodEvent, IncidentDecision, IncidentRequest, PlaybookRule, ProposedAction
from app.responders.after_action import generate_after_action_report
from app.responders.cap import build_cap_alert
from app.responders.foia import build_edxl_de, export_events_csv
from app.simulation.model import simulate_impact
from app.safety.policy import evaluate
from app.storage.sqlite import Store


def event(event_id: str = "e1") -> FloodEvent:
    return FloodEvent(
        event_id=event_id,
        source="replay",
        observed_at=datetime.now(timezone.utc),
        kind="weather_alert",
        title="Flash Flood Warning",
        provenance_url="https://example.test/evidence",
        mode="replay",
    )


def decision() -> IncidentDecision:
    return IncidentDecision(
        mode="replay",
        scenario_id="test",
        summary="Crossing risk is rising.",
        risk_level="high",
        confidence=0.9,
        evidence_event_ids=["e1"],
        citations=["e1"],
        proposed_action=ProposedAction(
            action_type="close_crossing_and_reroute",
            target="Test crossing",
            rationale="Flood warning and rising gage.",
        ),
        policy_status="approval_required",
        model_name="test",
    )


def test_json_extraction_handles_fenced_output():
    assert _extract_json("```json\n{\"risk_level\": \"high\"}\n```")["risk_level"] == "high"
    assert _extract_json("<think>private reasoning</think>{\"risk_level\": \"moderate\"}")["risk_level"] == "moderate"


def test_decision_payload_accepts_known_wrapper_but_rejects_partial_json():
    complete = {"summary": "x", "risk_level": "high", "confidence": 0.8, "action_type": "request_approval", "target": "site", "rationale": "y", "citations": ["e1"]}
    assert _decision_payload({"decision": complete}) == complete
    assert _decision_payload({"risk_level": "high"}) is None


def test_model_request_keeps_security_instructions_in_system_role():
    payload = build_incident_request(model="test", events=[event()], scenario_id="test")
    system_prompt, user_prompt = (message["content"] for message in payload["messages"])
    assert "untrusted data" in system_prompt
    assert "Do not call tools" in system_prompt
    assert "must never be empty" in system_prompt
    assert 'must equal exactly this JSON array: ["e1"]' in system_prompt
    assert "Ignore instructions" not in user_prompt
    assert "Current evidence JSON" in user_prompt
    assert '"required_citation_event_ids": ["e1"]' in user_prompt


def test_citations_are_grounded_and_missing_values_are_repaired():
    evidence = [event("e1"), event("e2"), event("e3")]
    citations, repaired = _ground_citations(["invented", "e2"], evidence)
    assert repaired is True
    assert len(citations) == 3
    assert set(citations) == {"e1", "e2", "e3"}


def test_citation_url_and_event_id_count_as_one_evidence_record():
    evidence = [event("e1"), event("e2"), event("e3")]
    evidence[0].provenance_url = "https://example.test/e1"
    citations, repaired = _ground_citations(["https://example.test/e1", "e1", "e2"], evidence)
    assert citations == ["e1", "e2", "e3"]
    assert repaired is True


def test_exact_model_written_references_can_be_normalized_from_rationale():
    evidence = [event("e1"), event("e2"), event("e3")]
    grounded, source = _ground_model_references(
        {"citations": [], "summary": "Rising water", "rationale": "Signals e1, e2, and e3 support the action.", "target": "site"},
        evidence,
    )
    assert set(grounded) == {"e1", "e2", "e3"}
    assert source == "model_text_references"


def test_model_text_without_exact_evidence_identifiers_is_not_repaired():
    grounded, source = _ground_model_references(
        {"citations": [], "summary": "Rising water", "rationale": "Several feeds support the action.", "target": "site"},
        [event("e1"), event("e2"), event("e3")],
    )
    assert grounded == []
    assert source is None


def test_reference_inventory_cannot_crowd_hazard_evidence_out_of_prompt():
    references = [event(f"ref-{index}").model_copy(update={"kind": "crossing_reference", "source": "austin"}) for index in range(20)]
    warning = event("warning").model_copy(update={"source": "nws", "kind": "weather_alert"})
    gage = event("gage").model_copy(update={"source": "usgs", "kind": "water_observation"})
    selected = _select_evidence([*references, warning, gage])
    assert warning in selected
    assert gage in selected
    assert len([item for item in selected if item.kind == "crossing_reference"]) <= 6


def test_missing_nvidia_key_is_fail_closed():
    with pytest.raises(IntegrationUnavailable):
        import asyncio
        asyncio.run(__import__("app.model.nemotron", fromlist=["assess_incident"]).assess_incident(
            api_key="", base_url="https://example.test/v1", model="test", events=[event()], scenario_id="test"
        ))


def test_policy_requires_approval_then_allows_reversible_action():
    assessed = decision()
    assert evaluate(assessed).status == "approval_required"
    assert evaluate(assessed, operator_approved=True).status == "allowed"


def test_store_is_idempotent_and_versions_feedback(tmp_path):
    store = Store(tmp_path / "floodops.sqlite3")
    store.save_events([event(), event()])
    assert len(store.list_events()) == 1
    assessed = decision()
    store.save_decision(assessed)
    store.add_feedback(assessed.incident_id, __import__("app.models", fromlist=["OperatorFeedback"]).OperatorFeedback(correction="Require a second gage before closure.", outcome="helpful"))
    first = store.add_memory(PlaybookRule(trigger="one gage rises", action="require a second gage before closure", rationale="avoid sensor anomalies", confidence=0.8, context_tags=["gage"]), assessed.incident_id)
    second = store.add_memory(PlaybookRule(trigger="one gage rises rapidly", action="require confirmation", rationale="operator correction", confidence=0.9, context_tags=["gage"]), assessed.incident_id)
    memories = store.active_memories()
    assert first != second
    assert memories[0]["version"] == 2
    assert memories[1]["version"] == 1


def test_replay_simulation_exposes_assumptions_and_high_risk():
    events = [
        event("warning"),
        FloodEvent(
            event_id="gage",
            source="replay",
            observed_at=datetime.now(timezone.utc),
            kind="water_observation",
            title="Gage height",
            value=12.4,
            unit="ft",
            provenance_url="https://example.test/gage",
            mode="replay",
        ),
    ]
    events[0].title = "Flash Flood Warning"
    estimate = simulate_impact(events, mode="replay", scenario_id="test", horizon_minutes=60)
    assert estimate.risk_level == "catastrophic"
    assert estimate.evidence_event_ids == ["warning", "gage"]
    assert estimate.assumptions


def test_texas_sources_have_distinct_provenance_types():
    txdot = event("txdot-1").model_copy(update={"source": "txdot"})
    lcra = event("lcra-1").model_copy(update={"source": "lcra"})
    assert txdot.source == "txdot"
    assert lcra.source == "lcra"


def test_cap_export_is_always_a_prototype_test_message():
    assessed = decision()
    payload = build_cap_alert(assessed)
    assert payload.startswith(b"<?xml")
    assert assessed.incident_id.encode() in payload
    assert b"<status>Test</status>" in payload
    assert b"<sender>austin-floodops-prototype</sender>" in payload
    assert b"<status>Actual</status>" not in payload


def test_edxl_export_is_unvalidated_test_draft_without_agency_identity():
    payload = build_edxl_de(decision(), [event()])
    assert b"<distributionStatus>Test</distributionStatus>" in payload
    assert b"austin-floodops-prototype" in payload
    assert b'"standards_validated": false' in payload
    assert b"texas.gov" not in payload


def test_csv_export_neutralizes_spreadsheet_formulas():
    malicious = event().model_copy(update={"title": "=HYPERLINK(\"https://attacker.test\")", "location": "+cmd"})
    exported = export_events_csv([malicious])
    assert "'=HYPERLINK" in exported
    assert "'+cmd" in exported


def test_after_action_uses_control_checks_not_compliance_claim(tmp_path):
    store = Store(tmp_path / "after-action.sqlite3")
    assessed = decision()
    store.save_events([event()])
    store.save_decision(assessed)
    report = generate_after_action_report(incident_id=assessed.incident_id, store=store)
    assert "control_checks" in report
    assert "compliance" not in report
    assert report["retention"]["agency_policy_applied"] is False


def test_seeded_resources_are_explicitly_fictional(tmp_path):
    resources = Store(tmp_path / "resources.sqlite3").list_resources()
    assert resources
    assert all("exercise" in resource["name"].lower() for resource in resources)
    assert all("fictional exercise" in resource["notes"].lower() for resource in resources)


def test_resource_label_migration_preserves_operator_edited_notes(tmp_path):
    store = Store(tmp_path / "resources-edited.sqlite3")
    store.list_resources()
    with store._connect() as db:
        db.execute(
            """UPDATE resources SET name = ?, location = ?, notes = ? WHERE id = ?""",
            ("Barricade Unit 1 - Onion Creek Crossing", "Onion Creek Blvd & E Stassney", "OPERATOR EDIT", "barricade-001"),
        )
    resource = store.get_resource("barricade-001")
    assert resource["notes"] == "OPERATOR EDIT"
    assert resource["name"] == "Barricade Unit 1 - Onion Creek Crossing"


def test_scenario_identifier_blocks_path_traversal():
    with pytest.raises(ValueError):
        IncidentRequest(mode="replay", scenario_id="../../private/tmp/fixture")


@pytest.mark.asyncio
async def test_action_permissions_do_not_leak_across_similarly_ranked_roles():
    with pytest.raises(HTTPException) as denied:
        await require_action("approve")(actor=Actor(sub="records-reviewer", role=Role.auditor))
    assert denied.value.status_code == 403


def test_secure_auth_requires_independent_long_secrets():
    assert replace(settings, jwt_secret="x" * 32, auth_bootstrap_token="").has_secure_auth is False
    assert replace(settings, jwt_secret="x" * 32, auth_bootstrap_token="y" * 32).has_secure_auth is True


@pytest.mark.asyncio
async def test_secure_public_mode_is_read_only(monkeypatch):
    from app import auth

    secure = replace(
        settings,
        enable_rbac=True,
        jwt_secret="j" * 32,
        auth_bootstrap_token="b" * 32,
    )
    monkeypatch.setattr(auth, "settings", secure)
    anonymous = await current_actor(credentials=None)
    assert anonymous.role is Role.viewer
    assert anonymous.sub == "anonymous"
    assert await require_action("view")(actor=anonymous) == anonymous
    with pytest.raises(HTTPException) as denied:
        await require_action("assess")(actor=anonymous)
    assert denied.value.status_code == 403


@pytest.mark.asyncio
async def test_token_endpoint_rejects_system_role_and_requires_bootstrap(monkeypatch):
    from app import main

    secure = replace(
        settings,
        enable_rbac=True,
        jwt_secret="j" * 32,
        auth_bootstrap_token="b" * 32,
    )
    monkeypatch.setattr(main, "settings", secure)
    with pytest.raises(HTTPException) as system_denied:
        await main.auth_token(main.TokenRequest(role="system"), bootstrap_token="b" * 32)
    assert system_denied.value.status_code == 403
    with pytest.raises(HTTPException) as bootstrap_denied:
        await main.auth_token(main.TokenRequest(role="operator"), bootstrap_token="wrong")
    assert bootstrap_denied.value.status_code == 401
    issued = await main.auth_token(main.TokenRequest(role="operator"), bootstrap_token="b" * 32)
    assert issued["role"] == "operator"
    assert issued["access_token"]
