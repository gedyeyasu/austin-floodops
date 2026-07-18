import json
from pathlib import Path

from app.models import FloodEvent
from app.sources.nws import parse_nws_alerts
from app.sources.usgs import parse_usgs_observations


FIXTURES = Path(__file__).parent / "fixtures"


def test_nws_contract_produces_stable_flood_event():
    payload = json.loads((FIXTURES / "nws_alerts.json").read_text())
    first = parse_nws_alerts(payload)
    second = parse_nws_alerts(payload)
    assert len(first) == 1
    assert isinstance(first[0], FloodEvent)
    assert first[0].source == "nws"
    assert first[0].event_id == second[0].event_id
    assert first[0].severity == "severe"


def test_usgs_contract_uses_latest_observation_and_stable_id():
    payload = json.loads((FIXTURES / "usgs_iv.json").read_text())
    events = parse_usgs_observations(payload, "08158000", "00065")
    assert len(events) == 1
    assert isinstance(events[0], FloodEvent)
    assert events[0].source == "usgs"
    assert events[0].value == 11.4
    assert "08158000-00065" in events[0].event_id
