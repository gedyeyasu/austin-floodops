from __future__ import annotations

from datetime import timezone
from xml.etree.ElementTree import Element, SubElement, tostring

import httpx

from app.models import IncidentDecision


CAP_NS = "urn:oasis:names:tc:emergency:cap:1.2"


def _cap_time(value) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_cap_alert(decision: IncidentDecision) -> bytes:
    """Build a CAP 1.2 alert for a human-approved responder channel.

    Exporting the standards-based payload is local and side-effect free. The
    optional sender adapter is separate and requires an explicitly configured
    endpoint plus operator confirmation.
    """
    alert = Element("alert", {"xmlns": CAP_NS})
    for name, value in (
        ("identifier", f"austin-floodops-{decision.incident_id}"),
        ("sender", "austin-floodops"),
        ("sent", _cap_time(decision.created_at)),
        ("status", "Actual"),
        ("msgType", "Alert"),
        ("scope", "Restricted"),
    ):
        SubElement(alert, name).text = value
    info = SubElement(alert, "info")
    for name, value in (
        ("category", "Safety"),
        ("event", "Flood"),
        ("urgency", "Immediate" if decision.risk_level in {"high", "catastrophic"} else "Expected"),
        ("severity", "Extreme" if decision.risk_level == "catastrophic" else "Severe" if decision.risk_level == "high" else "Moderate"),
        ("certainty", "Likely"),
        ("headline", f"Austin FloodOps: {decision.risk_level} flood operations recommendation"),
        ("description", decision.summary),
        ("instruction", decision.proposed_action.rationale),
    ):
        SubElement(info, name).text = value
    area = SubElement(info, "area")
    SubElement(area, "areaDesc").text = decision.proposed_action.target
    return tostring(alert, encoding="utf-8", xml_declaration=True)


class ResponderUnavailable(RuntimeError):
    pass


async def send_cap(*, url: str, token: str, incident_id: str, payload: bytes) -> int:
    if not url or not token:
        raise ResponderUnavailable("First-responder webhook credentials are not configured.")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/cap+xml",
        "Idempotency-Key": f"austin-floodops:{incident_id}",
    }
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.post(url, content=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ResponderUnavailable(f"First-responder webhook failed: {exc}") from exc
    return response.status_code
