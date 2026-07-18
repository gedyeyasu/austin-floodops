from datetime import timezone
import json
from pathlib import Path

from app.models import FloodEvent
from app.sources.austin import parse_austin_crossings, parse_austin_road_closures
from app.sources.nws import parse_nws_alerts
from app.sources.txdot import parse_txdot_closures
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


def test_austin_crossing_contract_parses_real_timestamp_and_geometry():
    payload = [{
        "objectid": "42",
        "crossing_description": "Onion Creek exercise crossing",
        "crossing_type": "Low water",
        "gage_number": 17,
        "modified_date": "2026-07-18T12:00:00Z",
        "the_geom": {"coordinates": [-97.75, 30.18]},
    }]
    events = parse_austin_crossings(payload)
    assert len(events) == 1
    assert events[0].observed_at.tzinfo == timezone.utc
    assert events[0].latitude == 30.18
    assert events[0].longitude == -97.75
    assert events[0].value is None
    assert events[0].kind == "crossing_reference"


def test_austin_road_contract_uses_nonempty_timestamp():
    events = parse_austin_road_closures([{
        "id": "road-1",
        "location": "Test Road",
        "status": "closed",
        "closure_start": "2026-07-18T12:00:00Z",
    }])
    assert len(events) == 1
    assert events[0].observed_at.tzinfo == timezone.utc


def test_txdot_contract_initializes_items_and_preserves_stable_provenance():
    payload = {"closures": [{
        "id": "closure-7",
        "road": "Test Road",
        "reason": "Flood water",
        "updatedAt": "2026-07-18T12:00:00Z",
        "latitude": "30.20",
        "longitude": "-97.70",
    }]}
    first = parse_txdot_closures(payload)
    second = parse_txdot_closures(payload)
    assert len(first) == 1
    assert first[0].event_id == second[0].event_id
    assert first[0].source == "txdot"
    assert first[0].freshness_seconds is not None
