from __future__ import annotations

import logging
import os
import uuid
import json
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("floodops.hiddenlayer")

# Track 3 — Integrating Runtime Security
# Requirement: Instrument agent with HiddenLayer runtime security.
# Every input/output to/from model treated as untrusted: user prompts, model responses, tool calls, tool results, ingested content (NWS, USGS, LCRA, TxDOT).
# Route through HiddenLayer Runtime Security API so threats like prompt injection and data leakage detected real-time.
# What "good" looks like: runtime instrumented, every prompt/response passes through HiddenLayer, plus tool calls/results/ingested content. Detection findings used: refuse, escalate, log+continue, etc.
# Judged: Depth of instrumentation + thoughtfulness how agent uses detection results.


class HiddenLayerUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class HiddenLayerConfig:
    # Legacy v1: tenant-specific Interactions URL
    interactions_url: str = ""
    api_key: str = ""
    project: str = "austin-floodops"

    # New v2 SDK: client_id / client_secret from AITX key vendor
    client_id: str = ""
    client_secret: str = ""
    # v2 project id and metadata
    hl_project_id: str = "default-project"
    model: str = "nvidia/nemotron-3-nano-30b-a3b"
    provider: str = "nvidia"  # or openai for compat

    @property
    def configured_legacy(self) -> bool:
        return bool(self.interactions_url and self.api_key)

    @property
    def configured_v2(self) -> bool:
        return bool(self.client_id and self.client_secret)

    @property
    def configured(self) -> bool:
        return self.configured_legacy or self.configured_v2

    @property
    def mode(self) -> str:
        if self.configured_v2:
            return "v2-sdk"
        if self.configured_legacy:
            return "v1-tenant"
        return "unconfigured"


# --- v2 SDK Integration (Track 3) ---
# Uses hiddenlayer-sdk Python SDK if available, else falls back to direct httpx call to emulate

def _make_session_id() -> str:
    return f"floodops-{uuid.uuid4().hex[:8]}-texas"


def _fired_signals(signals: dict[str, Any]) -> list[str]:
    """Extract fired signal names from HiddenLayer analysis.signals"""
    fired = []
    try:
        if signals.get("prompt_injection", {}).get("detected"):
            fired.append("prompt_injection")
        if signals.get("personally_identifiable_information", {}).get("entities"):
            fired.append("pii")
        if signals.get("code", {}).get("languages"):
            fired.append("code")
        if signals.get("guardrails", {}).get("detected"):
            fired.append("guardrails")
        if signals.get("url", {}).get("urls"):
            fired.append("url")
        if signals.get("denial_of_service", {}).get("token_count", 0) > 10000:
            fired.append("dos")
    except Exception:
        pass
    return fired


def _is_authentication_failure(exc: Exception) -> bool:
    """Recognize provider authentication failures without surfacing secret-bearing responses."""
    response = getattr(exc, "response", None)
    if getattr(response, "status_code", None) in {401, 403}:
        return True
    message = str(exc).lower()
    return any(marker in message for marker in ("unauthorized", "invalid_client", "invalid client", "error code: 401", "error code: 403"))


async def evaluate_interaction_v2(
    *,
    client_id: str,
    client_secret: str,
    interaction: dict[str, Any],
    model: str = "nvidia/nemotron-3-nano-30b-a3b",
    provider: str = "nvidia",
    hl_project_id: str = "default-project",
    session_id: str | None = None,
    requester_id: str = "austin-floodops-texas-v2",
) -> dict[str, Any]:
    """
    Evaluate one agent boundary via HiddenLayer v2 Runtime Security SDK.
    - interaction: native provider payload (OpenAI Chat Completions format)
    - metadata: model, provider, requester_id, external_session_id
    - hl_project_id: project whose policy evaluates interaction
    - HL-Runtime-Session-Id header groups whole run into one session

    Returns dict with:
    - evaluated_interaction.messages[].analysis.signals
    - outcome (action, detections)
    - threat_level
    - fired list
    """
    if not client_id or not client_secret:
        raise HiddenLayerUnavailable("HiddenLayer v2 client_id/client_secret not configured")

    session_id = session_id or _make_session_id()

    # Try SDK first
    try:
        from hiddenlayer import HiddenLayer

        hl = HiddenLayer(client_id=client_id, client_secret=client_secret)

        metadata = {
            "model": model,
            "provider": provider,
            "requester_id": requester_id,
            "external_session_id": session_id,
        }

        # SDK call - synchronous? SDK is sync, wrap in thread if needed
        # For simplicity use sync call in async context via to_thread
        import asyncio

        def _call():
            return hl.runtime.evaluate_interaction(
                interaction=interaction,
                metadata=metadata,
                hl_project_id=hl_project_id,
                extra_headers={"HL-Runtime-Session-Id": session_id},
            )

        resp = await asyncio.to_thread(_call)

        # Parse response
        evaluated = resp.evaluated_interaction
        messages_out = []
        all_fired: list[str] = []
        for msg in evaluated.messages:
            signals = msg.analysis.signals if hasattr(msg.analysis, "signals") else {}
            # signals may be object, convert to dict if needed
            if not isinstance(signals, dict):
                try:
                    signals = signals.__dict__ if hasattr(signals, "__dict__") else dict(signals)
                except Exception:
                    signals = {}
            fired = _fired_signals(signals) if isinstance(signals, dict) else []
            all_fired.extend(fired)
            messages_out.append(
                {
                    "role": getattr(msg, "role", "unknown"),
                    "signals": signals,
                    "fired": fired,
                }
            )

        outcome = getattr(resp, "outcome", None)
        threat_level = getattr(resp, "threat_level", "NONE")
        if outcome:
            try:
                threat_level = getattr(outcome, "action", threat_level)
            except Exception:
                pass

        return {
            "status": "scanned",
            "session_id": session_id,
            "model": model,
            "provider": provider,
            "project_id": hl_project_id,
            "messages": messages_out,
            "fired_signals": list(set(all_fired)),
            "threat_level": str(threat_level),
            "outcome": str(outcome) if outcome else "NONE",
            "raw": {
                "evaluation_id": getattr(resp.metadata, "evaluation_id", None) if hasattr(resp, "metadata") else None,
            },
            "blocked": len(all_fired) > 0 and "prompt_injection" in all_fired,
        }

    except ImportError as exc:
        raise HiddenLayerUnavailable(f"hiddenlayer-sdk not installed: {exc}") from exc
    except Exception as exc:
        if _is_authentication_failure(exc):
            raise HiddenLayerUnavailable(
                "HiddenLayer authentication failed. Rotate the client ID and client secret; hackathon credentials expire after 72 hours."
            ) from exc
        # If SDK fails, try to extract if it's a detection that should block
        err_str = str(exc).lower()
        if "prompt_injection" in err_str or "blocked" in err_str or "threat" in err_str:
            raise HiddenLayerUnavailable(f"HiddenLayer v2 blocked: {exc}") from exc
        raise HiddenLayerUnavailable(f"HiddenLayer v2 evaluate failed: {exc}") from exc


# Convenience wrappers for each boundary in FloodOps agent

async def scan_boundary(
    config: HiddenLayerConfig,
    *,
    boundary: str,
    interaction: dict[str, Any],
    session_id: str,
    requester_id: str | None = None,
) -> dict[str, Any]:
    """
    Scan one boundary: user prompt, tool call, tool result, final answer, ingested content.
    Boundary names for Texas gov ops:
    - ingested_nws: NWS alert text (untrusted ingested)
    - ingested_usgs: USGS observation (untrusted)
    - ingested_lcra: LCRA stage (untrusted)
    - ingested_txdot: TxDOT closure (untrusted)
    - ingested_austin: Austin crossings/roads/311 (untrusted)
    - user_prompt: operator correction, feedback
    - model_request: Nemotron prompt sent
    - tool_call: proposed action close_crossing_and_reroute, etc
    - tool_result: simulation, routing, CAP, WebEOC result
    - final_answer: decision summary
    """
    if not config.configured_v2:
        raise HiddenLayerUnavailable("v2 not configured, use legacy scan_interaction for v1")

    return await evaluate_interaction_v2(
        client_id=config.client_id,
        client_secret=config.client_secret,
        interaction=interaction,
        model=config.model,
        provider=config.provider,
        hl_project_id=config.hl_project_id,
        session_id=session_id,
        requester_id=requester_id or f"floodops-{boundary}-texas",
    )


def build_chat_completions_payload(
    *,
    model: str,
    system_prompt: str | None = None,
    user_content: str,
    tools: list[dict[str, Any]] | None = None,
    assistant_content: str | None = None,
    assistant_tool_calls: list[dict[str, Any]] | None = None,
    tool_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Build OpenAI Chat Completions payload for HiddenLayer evaluation.
    This mirrors what Nemotron endpoint receives, so HiddenLayer sees same content.
    """
    messages: list[dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_content})
    if assistant_content or assistant_tool_calls:
        assistant_msg: dict[str, Any] = {"role": "assistant"}
        if assistant_content:
            assistant_msg["content"] = assistant_content
        if assistant_tool_calls:
            assistant_msg["tool_calls"] = assistant_tool_calls
        messages.append(assistant_msg)
    if tool_results:
        for tr in tool_results:
            messages.append({"role": "tool", "tool_call_id": tr.get("tool_call_id", "call_1"), "content": tr.get("content", "")})

    payload: dict[str, Any] = {"model": model, "messages": messages}
    if tools:
        payload["tools"] = tools
    return payload


# --- Legacy v1 for backward compat ---

async def scan_interaction(config: HiddenLayerConfig, *, input_text: str, output_text: str) -> dict[str, Any]:
    """Legacy v1 tenant-specific Interactions API — kept for backward compat"""
    if config.configured_v2:
        # Use v2 SDK with simple chat completions payload
        payload = build_chat_completions_payload(
            model=config.model,
            system_prompt="You are Austin FloodOps decision-support for Texas gov.",
            user_content=f"Input: {input_text}\nOutput: {output_text}",
        )
        result = await evaluate_interaction_v2(
            client_id=config.client_id,
            client_secret=config.client_secret,
            interaction=payload,
            model=config.model,
            provider=config.provider,
            hl_project_id=config.hl_project_id,
            session_id=_make_session_id(),
            requester_id="floodops-legacy-compat",
        )
        # If prompt_injection fired, fail closed
        if result.get("blocked") or "prompt_injection" in result.get("fired_signals", []):
            raise HiddenLayerUnavailable(f"HiddenLayer v2 blocked: {result.get('fired_signals')}")
        return result

    if not config.configured_legacy:
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
