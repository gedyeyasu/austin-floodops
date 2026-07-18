from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.service import FloodOpsService

logger = logging.getLogger("austin_floodops.heartbeat")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HeartbeatEngine:
    """
    Autonomous heartbeat. Enterprise fix:
    - run_cycle returns dict with cycles, new_events, sources, consecutive_failures, last_error, decision_outcome
    - flexible __init__ supports positional/keyword variations used by tests and older code
      HeartbeatEngine(service, 30)
      HeartbeatEngine(service, poll_seconds=30)
      HeartbeatEngine(service, interval_seconds=30, scenario_id=...)
    """

    def __init__(
        self,
        service: FloodOpsService,
        interval_seconds: int = 30,
        scenario_id: str = "austin-autonomous-heartbeat",
        *args,
        **kwargs,
    ):
        # Flexible handling of alternative kw names
        if "poll_seconds" in kwargs:
            interval_seconds = kwargs.pop("poll_seconds")
        if "interval" in kwargs:
            interval_seconds = kwargs.pop("interval")
        if "scenario" in kwargs:
            scenario_id = kwargs.pop("scenario")

        # If args contains interval as second positional passed as string/int?
        # Dataclass originally allowed interval_seconds as second arg; we already support.

        self.service = service
        self.interval_seconds = int(interval_seconds)
        self.scenario_id = scenario_id
        self._stop = asyncio.Event()
        # tolerate extra kwargs silently
        self._extra = kwargs

    async def run_cycle(self) -> dict[str, Any]:
        previous = self.service.store.heartbeat_state()
        state: dict[str, Any] = {
            "running": True,
            "cycles": int(previous.get("cycles", 0)) + 1,
            "last_started_at": _now(),
        }
        try:
            events, sources = await self.service.gather_live_with_status()
            degraded_sources = [name for name, result in sources.items() if result.get("status") != "ok"]
            new_events = self.service.store.filter_new_events(events)
            decision = None
            error = f"Source degraded: {', '.join(degraded_sources)}" if degraded_sources else None
            if new_events:
                _, decision, assessment_error = await self.service.assess_events(new_events, self.scenario_id)
                if assessment_error:
                    error = "; ".join(item for item in (error, assessment_error) if item)
            state.update(
                {
                    "last_completed_at": _now(),
                    "last_success_at": previous.get("last_success_at") if error else _now(),
                    "last_error": error,
                    "consecutive_failures": 0 if not error else int(previous.get("consecutive_failures", 0)) + 1,
                    "sources": sources,
                    "events_seen": len(events),
                    "new_events": len(new_events),
                    "decision_outcome": decision.policy_status if decision else "no_new_events",
                    "last_decision_id": decision.incident_id if decision else previous.get("last_decision_id"),
                }
            )
            logger.info(
                "heartbeat cycle=%s events=%s new=%s decision=%s error=%s",
                state["cycles"],
                len(events),
                len(new_events),
                state["decision_outcome"],
                bool(error),
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            state.update(
                {
                    "last_completed_at": _now(),
                    "last_error": f"{type(exc).__name__}: {exc}",
                    "consecutive_failures": int(previous.get("consecutive_failures", 0)) + 1,
                    "events_seen": 0,
                    "new_events": 0,
                    "decision_outcome": "degraded",
                }
            )
            logger.warning("heartbeat cycle=%s degraded=%s", state["cycles"], type(exc).__name__)
        self.service.store.save_heartbeat_state(state)
        return state

    async def run(self) -> None:
        self.service.store.save_heartbeat_state({"running": True, "started_at": _now()})
        while not self._stop.is_set():
            await self.run_cycle()
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=max(1, self.interval_seconds))
            except TimeoutError:
                continue
        self.service.store.save_heartbeat_state({"running": False, "stopped_at": _now()})

    def stop(self) -> None:
        self._stop.set()
