"""
SynapseOps Simulation — Failure Controller.

The FailureController is the single source of truth for what failures
are currently active in the simulated infrastructure.

Design:
- In-process: Active FailureScenario objects are stored in a dict keyed
  by scenario ID (UUID). This is fast, simple, and sufficient because
  the simulation is a single-instance development tool.
- Redis-backed: After every mutation, the full active failure state is
  published to a Redis key as JSON. Simulated services (which run as
  separate processes) read this key to know what failures to apply.
- Auto-expiry: A background asyncio task runs every second and expires
  scenarios that have exceeded their duration_seconds.
- Concurrency: A single asyncio.Lock guards all mutations to prevent
  race conditions when the background expiry task and API handlers run
  concurrently.

Lifecycle:
- `FailureController.create(redis_client, settings)` is the factory.
  Call it during application startup.
- `controller.start_expiry_task()` starts the background task.
  Call it inside the lifespan context, after create().
- `controller.stop()` cancels the background task gracefully.
  Call it during application shutdown.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import uuid  # noqa: TC003
from datetime import UTC, datetime

from redis.asyncio import Redis  # noqa: TC002

from backend.core.logging import get_logger
from backend.simulation.models import (
    ClearFailuresRequest,
    ClearFailuresResponse,
    FailureScenario,
    FailureTarget,
    InjectFailureRequest,
    InjectFailureResponse,
    SimulationState,
)

logger = get_logger("simulation.controller")

_REDIS_FAILURE_KEY = "sim:failures"
_EXPIRY_POLL_INTERVAL_SECONDS = 1.0


class FailureController:
    """Manages active failure scenarios for the simulated infrastructure.

    Attributes:
        _scenarios: Dict mapping scenario ID → FailureScenario.
        _lock: asyncio.Lock guarding all mutations.
        _redis: Async Redis client for publishing state.
        _expiry_task: Background asyncio task for auto-expiry.
    """

    def __init__(self, redis_client: Redis, redis_failure_key: str = _REDIS_FAILURE_KEY) -> None:
        self._scenarios: dict[uuid.UUID, FailureScenario] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self._redis: Redis = redis_client
        self._redis_failure_key = redis_failure_key
        self._expiry_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls, redis_client: Redis, redis_failure_key: str = _REDIS_FAILURE_KEY
    ) -> FailureController:
        """Create a FailureController instance.

        Args:
            redis_client: Async Redis client (shared with the main app).
            redis_failure_key: Redis key where failure state is published.

        Returns:
            A new FailureController (background task not yet started).
        """
        return cls(redis_client=redis_client, redis_failure_key=redis_failure_key)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_expiry_task(self) -> None:
        """Start the background task that auto-expires timed scenarios.

        Must be called from within a running asyncio event loop
        (e.g., inside the FastAPI lifespan context).
        """
        if self._expiry_task is not None and not self._expiry_task.done():
            return  # Already running
        self._expiry_task = asyncio.create_task(
            self._expiry_loop(),
            name="simulation_failure_expiry",
        )
        logger.info("Failure expiry background task started")

    async def stop(self) -> None:
        """Cancel and await the background expiry task."""
        if self._expiry_task and not self._expiry_task.done():
            self._expiry_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._expiry_task
        logger.info("Failure controller stopped")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def inject_failure(self, request: InjectFailureRequest) -> InjectFailureResponse:
        """Inject a new failure scenario.

        Creates a FailureScenario from the request, stores it, and
        publishes the updated state to Redis.

        Args:
            request: Validated InjectFailureRequest.

        Returns:
            InjectFailureResponse with the created scenario.

        Raises:
            ValueError: If the request lacks the required failure fields
                        (i.e., not a named scenario and fields are missing).
        """
        scenario = FailureScenario(
            name=request.name or "custom",
            failure_type=request.failure_type,  # type: ignore[arg-type]
            target=request.target,  # type: ignore[arg-type]
            severity=request.severity,
            duration_seconds=request.duration_seconds,
            description=request.description,
        )

        async with self._lock:
            self._scenarios[scenario.id] = scenario
            await self._publish_to_redis()

        logger.info(
            "Failure injected",
            scenario_id=str(scenario.id),
            name=scenario.name,
            failure_type=scenario.failure_type,
            target=scenario.target,
            severity=scenario.severity,
        )

        return InjectFailureResponse(
            scenario=scenario,
            message=(
                f"Failure '{scenario.name}' ({scenario.failure_type}) "
                f"injected on target '{scenario.target}' "
                f"with severity {scenario.severity:.2f}."
            ),
        )

    async def clear_failures(self, request: ClearFailuresRequest) -> ClearFailuresResponse:
        """Clear active failure scenarios.

        If request.target is None, clears ALL active scenarios.
        Otherwise, clears only scenarios targeting the specified component.

        Args:
            request: ClearFailuresRequest with optional target filter.

        Returns:
            ClearFailuresResponse with cleared count.
        """
        async with self._lock:
            if request.target is None or request.target == FailureTarget.ALL:
                cleared = len(self._scenarios)
                self._scenarios.clear()
                label = "all targets"
            else:
                to_clear = [
                    sid
                    for sid, s in self._scenarios.items()
                    if s.target == request.target or s.target == FailureTarget.ALL
                ]
                for sid in to_clear:
                    del self._scenarios[sid]
                cleared = len(to_clear)
                label = str(request.target)

            await self._publish_to_redis()

        logger.info("Failures cleared", cleared_count=cleared, target=label)

        return ClearFailuresResponse(
            cleared_count=cleared,
            message=f"Cleared {cleared} failure scenario(s) for {label}.",
        )

    async def get_state(self) -> SimulationState:
        """Return the current simulation state snapshot.

        Returns:
            SimulationState with all currently active scenarios.
        """
        async with self._lock:
            active = [s for s in self._scenarios.values() if s.active]

        return SimulationState(
            active_scenarios=active,
            snapshot_at=datetime.now(UTC),
        )

    async def get_active_failures_for(self, target: FailureTarget) -> list[FailureScenario]:
        """Return active failure scenarios affecting a specific target.

        Includes scenarios targeting the exact component AND scenarios
        targeting ALL (which apply to every component).

        Args:
            target: The component to query failures for.

        Returns:
            List of active FailureScenario objects.
        """
        async with self._lock:
            return [
                s
                for s in self._scenarios.values()
                if s.active and (s.target == target or s.target == FailureTarget.ALL)
            ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _publish_to_redis(self) -> None:
        """Serialize and publish the current failure state to Redis.

        Called while holding self._lock, so callers must already hold it.

        Failures to publish are logged as warnings but do not raise —
        the in-memory state remains the authoritative source.
        """
        try:
            payload = [s.model_dump(mode="json") for s in self._scenarios.values() if s.active]
            await self._redis.set(self._redis_failure_key, json.dumps(payload))
        except Exception as exc:
            logger.warning(
                "Failed to publish failure state to Redis",
                error=str(exc),
                error_type=type(exc).__name__,
            )

    async def _expire_scenarios(self) -> int:
        """Expire scenarios that have exceeded their duration_seconds.

        Returns:
            Number of scenarios expired in this pass.
        """
        now = datetime.now(UTC)
        expired_count = 0

        async with self._lock:
            to_expire = [sid for sid, s in self._scenarios.items() if s.is_expired(now=now)]
            if to_expire:
                for sid in to_expire:
                    del self._scenarios[sid]
                expired_count = len(to_expire)
                await self._publish_to_redis()

        if expired_count:
            logger.info("Failure scenarios expired", count=expired_count)

        return expired_count

    async def _expiry_loop(self) -> None:
        """Background loop that checks for expired scenarios every second."""
        logger.debug("Expiry loop started")
        while True:
            try:
                await asyncio.sleep(_EXPIRY_POLL_INTERVAL_SECONDS)
                await self._expire_scenarios()
            except asyncio.CancelledError:
                logger.debug("Expiry loop cancelled")
                break
            except Exception as exc:
                # Log but do not crash the loop
                logger.warning(
                    "Expiry loop encountered an error",
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
