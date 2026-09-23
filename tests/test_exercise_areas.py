from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import exercise_areas
from app.auth import Actor, Role, current_actor


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(exercise_areas, "settings", SimpleNamespace(db_path=tmp_path / "areas.sqlite3"))
    app = FastAPI()
    app.include_router(exercise_areas.router)
    app.dependency_overrides[current_actor] = lambda: Actor(sub="test", role=Role.system)
    with TestClient(app) as client:
        yield client


def area():
    return {"id": str(uuid4()), "name": "Test area", "geometry": {"type": "Polygon", "coordinates": [[[-97.75, 30.26], [-97.73, 30.26], [-97.73, 30.28], [-97.75, 30.26]]]}}


def test_save_list_and_retry_without_duplicate(client):
    payload = area()
    assert client.post("/api/exercise-areas", json=payload).json() == payload
    assert client.post("/api/exercise-areas", json=payload).json() == payload
    assert client.get("/api/exercise-areas").json() == [payload]
    payload["name"] = "Another area"
    assert client.post("/api/exercise-areas", json=payload).status_code == 409


@pytest.mark.parametrize("geometry", [
    {"type": "Point", "coordinates": [-97, 30]},
    {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]},
    {"type": "Polygon", "coordinates": [[[0, 0], [0, 0], [0, 0], [0, 0]]]},
    {"type": "Polygon", "coordinates": [[[181, 30], [0, 0], [1, 1], [181, 30]]]},
])
def test_reject_invalid_geometry_without_saving(client, geometry):
    payload = area()
    payload["geometry"] = geometry
    assert client.post("/api/exercise-areas", json=payload).status_code == 422
    assert client.get("/api/exercise-areas").json() == []


def test_viewer_cannot_create(client):
    client.app.dependency_overrides[current_actor] = lambda: Actor(sub="viewer", role=Role.viewer)
    assert client.post("/api/exercise-areas", json=area()).status_code == 403
    assert client.get("/api/exercise-areas").status_code == 200
