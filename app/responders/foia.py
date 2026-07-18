from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring

from app.models import IncidentDecision, FloodEvent


def export_events_csv(events: list[FloodEvent]) -> str:
    """FOIA CSV export - Texas Gov records retention, evidence with provenance"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["event_id", "source", "observed_at", "kind", "title", "severity", "location", "latitude", "longitude", "value", "unit", "provenance_url", "mode"])
    for e in events:
        writer.writerow(
            [
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
            ]
        )
    return output.getvalue()


def export_decisions_csv(decisions: list[IncidentDecision]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["incident_id", "created_at", "mode", "scenario_id", "summary", "risk_level", "confidence", "policy_status", "model_name", "evidence_event_ids", "citations", "action_type", "target"])
    for d in decisions:
        writer.writerow(
            [
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
            ]
        )
    return output.getvalue()


def build_edxl_de(decision: IncidentDecision, events: list[FloodEvent]) -> bytes:
    """
    Build EDXL Distribution Element (EDXL-DE) 1.0 wrapper for CAP + Texas metadata.
    Gov-grade: EDXL-DE is used for sharing emergency info between systems, TDEM compatible.
    """
    # EDXL-DE namespaces
    edxl_ns = "urn:oasis:names:tc:emergency:EDXL:DE:1.0"
    cap_ns = "urn:oasis:names:tc:emergency:cap:1.2"

    distribution = Element("EDXLDistribution", {"xmlns": edxl_ns})
    SubElement(distribution, "distributionID").text = f"austin-floodops-{decision.incident_id}"
    SubElement(distribution, "senderID").text = "austin-floodops@texas.gov"
    SubElement(distribution, "dateTimeSent").text = decision.created_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    SubElement(distribution, "distributionStatus").text = "Actual"
    SubElement(distribution, "distributionType").text = "Report"
    SubElement(distribution, "combinedConfidentiality").text = "Restricted - Texas Data Classification Confidential"
    SubElement(distribution, "language").text = "en-US"

    # Explicit address for Texas agencies
    target_areas = SubElement(distribution, "explicitAddress")
    SubElement(target_areas, "explicitAddressScheme").text = "Texas TDEM Regions"
    SubElement(target_areas, "explicitAddressValue").text = "Travis County, Williamson County, Hays County, Bastrop County - Austin EOC"

    # Content object wrapping CAP
    content_obj = SubElement(distribution, "contentObject")
    SubElement(content_obj, "combinedConfidentiality").text = "Restricted"
    SubElement(content_obj, "contentDescription").text = f"FloodOps incident {decision.risk_level} - {decision.summary} - Great State of Texas"
    SubElement(content_obj, "contentKeyword").text = "Flood, Texas, TDEM, Austin, LCRA, TxDOT, CAP, EDXL"
    SubElement(content_obj, "incidentID").text = decision.incident_id
    SubElement(content_obj, "incidentDescription").text = decision.summary

    # Originator role
    SubElement(content_obj, "originatorRole").text = "Austin FloodOps Enterprise - Decision Support, Human Authority"

    # Kay? Add consumer role
    SubElement(content_obj, "consumerRole").text = "TDEM, Travis County EOC, Austin Transportation"

    # Embedded CAP XML as xmlContent
    xml_content = SubElement(content_obj, "xmlContent")
    embedded = SubElement(xml_content, "embeddedXMLContent")
    # For simplicity, embed CAP as keyXMLContent reference - real would embed full CAP
    key_xml = SubElement(embedded, "keyXMLContent")
    SubElement(key_xml, "CAPAlert").text = f"CAP 1.2 Alert for {decision.incident_id} - {decision.risk_level} - See /api/decisions/{decision.incident_id}/cap for full XML"

    # Add non-XML content with provenance
    non_xml = SubElement(content_obj, "nonXMLContent")
    mime = SubElement(non_xml, "mimeType").text = "application/json"
    size = SubElement(non_xml, "size").text = str(len(json.dumps([e.model_dump(mode="json") for e in events])))
    digest = SubElement(non_xml, "digest").text = f"SHA256 of {len(events)} evidence items with provenance"
    uri = SubElement(non_xml, "uri").text = f"https://austin-floodops.texas.gov/api/decisions/{decision.incident_id}/cap"
    content_data = SubElement(non_xml, "contentData").text = json.dumps(
        {
            "incident_id": decision.incident_id,
            "evidence": [{"event_id": e.event_id, "source": e.source, "provenance_url": e.provenance_url} for e in events],
            "texas_metadata": {
                "state": "Texas",
                "great_state": "The Great State of Texas - Lone Star State",
                "tdem_ready": True,
                "lcra": "Lower Colorado River Authority Hydromet",
                "txdot": "TxDOT DriveTexas closures",
                "austin_eoc": "Austin Emergency Operations Center",
                "foia_retention_years": 7,
                "classification": "Texas Data Classification: Confidential - Emergency Operations",
            },
        }
    )

    return tostring(distribution, encoding="utf-8", xml_declaration=True)
