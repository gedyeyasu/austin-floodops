"""Local exercise records; deliberately separate from operational incidents."""
from __future__ import annotations

import json
import math
import sqlite3
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.auth import require_action
from app.config import settings

router = APIRouter(prefix="/api/exercise-areas", tags=["Synthetic UI exercise"])


class AreaInput(BaseModel):
    id: UUID
    name: str = Field(min_length=1, max_length=100)
    geometry: dict

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Give the area a name")
        return value

    @field_validator("geometry")
    @classmethod
    def polygon_only(cls, value: dict) -> dict:
        rings = value.get("coordinates")
        if value.get("type") != "Polygon" or not isinstance(rings, list) or len(rings) != 1:
            raise ValueError("Use one Polygon with a single exterior ring")
        ring = rings[0]
        if not isinstance(ring, list) or not 4 <= len(ring) <= 1000:
            raise ValueError("Use 3 to 999 vertices and a closing coordinate")
        for point in ring:
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError("Each coordinate must contain longitude and latitude")
            if any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) for n in point):
                raise ValueError("Coordinates must be finite numbers")
            if not -180 <= point[0] <= 180 or not -90 <= point[1] <= 90:
                raise ValueError("Coordinates are outside geographic bounds")
        if ring[0] != ring[-1] or len({tuple(p) for p in ring[:-1]}) < 3:
            raise ValueError("Close the ring and include at least three distinct vertices")
        return {"type": "Polygon", "coordinates": rings}


def connection():
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(settings.db_path)
    db.execute("CREATE TABLE IF NOT EXISTS ui_exercise_areas (id TEXT PRIMARY KEY, name TEXT NOT NULL, geometry TEXT NOT NULL)")
    return db


@router.get("", dependencies=[Depends(require_action("view"))])
def list_areas():
    db = connection()
    try:
        rows = db.execute("SELECT id, name, geometry FROM ui_exercise_areas ORDER BY rowid DESC").fetchall()
        return [{"id": row[0], "name": row[1], "geometry": json.loads(row[2])} for row in rows]
    finally:
        db.close()


@router.post("", dependencies=[Depends(require_action("assess"))])
def create_area(area: AreaInput):
    db = connection()
    record = {"id": str(area.id), "name": area.name, "geometry": area.geometry}
    try:
        existing = db.execute("SELECT name, geometry FROM ui_exercise_areas WHERE id = ?", (record["id"],)).fetchone()
        if existing:
            if existing[0] != area.name or json.loads(existing[1]) != area.geometry:
                raise HTTPException(409, "This request ID already belongs to another area")
            return record
        with db:
            db.execute("INSERT INTO ui_exercise_areas VALUES (?, ?, ?)", (record["id"], area.name, json.dumps(area.geometry)))
        return record
    finally:
        db.close()
