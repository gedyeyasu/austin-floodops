from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring

from app.models import IncidentDecision, FloodEvent


def _csv_cell(value: object) -> object:
    """Prevent spreadsheet applications from evaluating untrusted text as a formula."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{value}"
    return value


def _safe_row(values: list[object]) -> list[object]:
    return [_csv_cell(value) for value in values]


def export_events_csv(events: list[FloodEvent]) -> str:
    """Export normalized evidence with provenance for records review."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["event_id", "source", "observed_at", "kind", "title", "severity", "location", "latitude", "longitude", "value", "unit", "provenance_url", "mode"])
    for e in events:
        writer.writerow(
            _safe_row([
                e.event_id,
                e.source,
                e.observed_at.isoformat(),
                e.kind,
                e.title,
                e.severity,
                e.location or "",
                e.latitude or "",
                e.longitude or "",
                e.value or "",
                e.unit or "",
                e.provenance_url,
                e.mode,
            ])
        )
    return output.getvalue()


def export_decisions_csv(decisions: list[IncidentDecision]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["incident_id", "created_at", "mode", "scenario_id", "summary", "risk_level", "confidence", "policy_status", "model_name", "evidence_event_ids", "citations", "action_type", "target"])
    for d in decisions:
        writer.writerow(
            _safe_row([
                d.incident_id,
                d.created_at.isoformat(),
                d.mode,
                d.scenario_id,
                d.summary.replace("\n", " "),
                d.risk_level,
                d.confidence,
                d.policy_status,
                d.model_name,
                ";".join(d.evidence_event_ids),
                ";".join(d.citations),
                d.proposed_action.action_type,
                d.proposed_action.target,
            ])
        )
    return output.getvalue()


def build_edxl_de(decision: IncidentDecision, events: list[FloodEvent]) -> bytes:
    """
    Build a draft EDXL Distribution Element (EDXL-DE) 1.0-shaped wrapper.
    Builds an unvalidated EDXL-DE interoperability export for review.
    """
    # EDXL-DE namespaces
    edxl_ns = "urn:oasis:names:tc:emergency:EDXL:DE:1.0"
    distribution = Element("EDXLDistribution", {"xmlns": edxl_ns})
    SubElement(distribution, "distributionID").text = f"austin-floodops-{decision.incident_id}"
    SubElement(distribution, "senderID").text = "austin-floodops-prototype"
    SubElement(distribution, "dateTimeSent").text = decision.created_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    SubElement(distribution, "distributionStatus").text = "Test"
    SubElement(distribution, "distributionType").text = "Report"
    SubElement(distribution, "combinedConfidentiality").text = "Unclassified"
    SubElement(distribution, "language").text = "en-US"

    # Prototype routing address; it is not an agency address or routing scheme.
    target_areas = SubElement(distribution, "explicitAddress")
    SubElement(target_areas, "explicitAddressScheme").text = "urn:austin-floodops:prototype:jurisdiction"
    SubElement(target_areas, "explicitAddressValue").text = "Austin-area emergency-operations exercise"

    # Content object wrapping CAP
    content_obj = SubElement(distribution, "contentObject")
    SubElement(content_obj, "combinedConfidentiality").text = "Unclassified"
    SubElement(content_obj, "contentDescription").text = f"FloodOps prototype incident {decision.risk_level} - {decision.summary}"
    SubElement(content_obj, "contentKeyword").text = "Flood, Texas, Austin, CAP, EDXL, Prototype"
    SubElement(content_obj, "incidentID").text = decision.incident_id
    SubElement(content_obj, "incidentDescription").text = decision.summary

    # Originator role
    SubElement(content_obj, "originatorRole").text = "Austin FloodOps decision-support prototype"

    SubElement(content_obj, "consumerRole").text = "Authorized prototype reviewer"

    # Embedded CAP XML as xmlContent
    xml_content = SubElement(content_obj, "xmlContent")
    embedded = SubElement(xml_content, "embeddedXMLContent")
    # This is a review marker, not a standards-conformant embedded CAP document.
    key_xml = SubElement(embedded, "keyXMLContent")
    SubElement(key_xml, "CAPAlert").text = f"CAP 1.2 Test alert for {decision.incident_id} - {decision.risk_level}"

    # Add non-XML content with provenance
    evidence_json = json.dumps(
        {
            "incident_id": decision.incident_id,
            "evidence": [{"event_id": e.event_id, "source": e.source, "provenance_url": e.provenance_url} for e in events],
            "metadata": {
                "state": "Texas",
                "prototype": True,
                "agency_authorized": False,
                "standards_validated": False,
            },
        },
        sort_keys=True,
    )
    non_xml = SubElement(content_obj, "nonXMLContent")
    SubElement(non_xml, "mimeType").text = "application/json"
    SubElement(non_xml, "size").text = str(len(evidence_json.encode("utf-8")))
    SubElement(non_xml, "digest").text = f"sha256:{hashlib.sha256(evidence_json.encode('utf-8')).hexdigest()}"
    SubElement(non_xml, "contentData").text = evidence_json

    return tostring(distribution, encoding="utf-8", xml_declaration=True)
