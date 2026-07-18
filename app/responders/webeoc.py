from __future__ import annotations

from dataclasses import dataclass
from xml.etree.ElementTree import Element, SubElement, fromstring, tostring

import httpx


SOAP_ENV = "http://schemas.xmlsoap.org/soap/envelope/"
WEBEOC_NS = "urn:com:esi911:webeoc7:api:1.0"


class WebEOCUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class WebEOCConfig:
    api_url: str = ""
    username: str = ""
    password: str = ""
    position: str = ""
    incident: str = ""
    board_name: str = ""
    input_view_name: str = ""

    @property
    def configured(self) -> bool:
        return all(
            (
                self.api_url,
                self.username,
                self.password,
                self.position,
                self.incident,
                self.board_name,
                self.input_view_name,
            )
        )


def add_data_envelope(config: WebEOCConfig, xml_data: bytes) -> bytes:
    envelope = Element(f"{{{SOAP_ENV}}}Envelope")
    body = SubElement(envelope, f"{{{SOAP_ENV}}}Body")
    add_data = SubElement(body, f"{{{WEBEOC_NS}}}AddData")
    credentials = SubElement(add_data, "credentials")
    for key, value in (
        ("Username", config.username),
        ("Password", config.password),
        ("Position", config.position),
        ("Incident", config.incident),
    ):
        SubElement(credentials, key).text = value
    SubElement(add_data, "BoardName").text = config.board_name
    SubElement(add_data, "InputViewName").text = config.input_view_name
    SubElement(add_data, "XmlData").text = xml_data.decode("utf-8")
    return tostring(envelope, encoding="utf-8", xml_declaration=True)


async def send_to_webeoc(config: WebEOCConfig, *, incident_id: str, cap_payload: bytes) -> int:
    if not config.configured:
        raise WebEOCUnavailable("WebEOC board, position, incident, and credentials are not configured.")
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f'"{WEBEOC_NS}/AddData"',
        "Idempotency-Key": f"austin-floodops:{incident_id}",
    }
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.post(config.api_url, content=add_data_envelope(config, cap_payload), headers=headers)
            response.raise_for_status()
            root = fromstring(response.content)
    except (httpx.HTTPError, ValueError) as exc:
        raise WebEOCUnavailable(f"WebEOC request failed: {exc}") from exc
    result = next((node.text for node in root.iter() if node.tag.endswith("AddDataResult")), None)
    if not result:
        raise WebEOCUnavailable("WebEOC response did not include AddDataResult.")
    return int(result)
