from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class HiddenLayerUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class HiddenLayerConfig:
    interactions_url: str = ""
    api_key: str = ""
    project: str = "austin-floodops"

    @property
    def configured(self) -> bool:
        return bool(self.interactions_url and self.api_key)


async def scan_interaction(config: HiddenLayerConfig, *, input_text: str, output_text: str) -> dict[str, Any]:
    """Send one model interaction to a configured HiddenLayer Interactions API.

    The URL is intentionally operator-supplied because tenant API paths differ;
    an unset or unreachable endpoint fails closed instead of pretending to scan.
    """
    if not config.configured:
        raise HiddenLayerUnavailable("HiddenLayer Interactions endpoint is not configured.")
    payload = {"project": config.project, "input": input_text, "output": output_text}
    headers = {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.post(config.interactions_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HiddenLayerUnavailable(f"HiddenLayer scan failed: {exc}") from exc
    verdict = str(result.get("verdict", result.get("decision", "allow"))).lower()
    if result.get("blocked") is True or verdict in {"block", "blocked", "deny", "denied", "unsafe"}:
        raise HiddenLayerUnavailable("HiddenLayer blocked the model interaction.")
    return result
