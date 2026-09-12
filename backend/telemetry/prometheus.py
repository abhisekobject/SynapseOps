from datetime import UTC, datetime

import httpx
import structlog

from backend.core.config import Settings
from backend.telemetry.models import TelemetrySnapshot

logger = structlog.get_logger("telemetry.prometheus")


class PrometheusTelemetryAdapter:
    """Fetches telemetry from Prometheus (Phase 3) and normalizes it into Phase 4 Snapshots."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.prometheus_url = getattr(settings, "prometheus_url", "http://prometheus:9090")
        self._client = httpx.AsyncClient(timeout=5.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch_snapshot(self, service_id: str) -> TelemetrySnapshot | None:
        """Fetch the latest metrics for a specific service and return a TelemetrySnapshot."""
        svc_prefix = service_id.replace("-", "_")
        query = f'{{__name__=~"{svc_prefix}_.*"}}'

        try:
            response = await self._client.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": query},
            )
            if response.status_code != 200:
                logger.error("prometheus_query_failed", status=response.status_code, text=response.text)
                return None

            data = response.json()
            if data.get("status") != "success":
                logger.error("prometheus_query_error", error=data.get("error"))
                return None

            results = data.get("data", {}).get("result", [])
            if not results:
                return None

            metrics = {}
            for result in results:
                metric_name = result["metric"]["__name__"]
                value = float(result["value"][1])
                metrics[metric_name] = value

            snapshot = TelemetrySnapshot(
                service_id=service_id,
                timestamp=datetime.now(UTC),
                requests_per_second=metrics.get(f"{svc_prefix}_requests_per_second"),
                error_rate_percent=metrics.get(f"{svc_prefix}_error_rate_percent"),
                p50_latency_ms=metrics.get(f"{svc_prefix}_request_latency_p50_ms"),
                p95_latency_ms=metrics.get(f"{svc_prefix}_request_latency_p95_ms"),
                p99_latency_ms=metrics.get(f"{svc_prefix}_request_latency_p99_ms"),
                cpu_percent=metrics.get(f"{svc_prefix}_cpu_percent"),
                memory_mb=metrics.get(f"{svc_prefix}_memory_mb"),
                queue_depth=int(metrics.get(f"{svc_prefix}_queue_depth", 0)),
                database_latency_ms=metrics.get(f"{svc_prefix}_database_latency_ms"),
                is_healthy=bool(metrics.get(f"{svc_prefix}_healthy", 1)),
                active_failure_count=int(metrics.get(f"{svc_prefix}_active_failure_count", 0)),
            )
            return snapshot

        except httpx.RequestError as exc:
            logger.error("prometheus_connection_error", detail=str(exc))
            return None
