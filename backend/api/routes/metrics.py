"""
SynapseOps API -- Prometheus Metrics Endpoint (Phase 3).

Exposes the main SynapseOps API metrics at GET /metrics in
Prometheus text-format (exposition format 0.0.4).

This endpoint is intentionally placed at the root level (not under
/api/v1/) to follow the Prometheus scraping convention.

Prometheus scrape config should target this endpoint directly::

    scrape_configs:
      - job_name: synapseops-api
        static_configs:
          - targets: ['api:8000']
        metrics_path: /metrics
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import Response

from backend.observability.metrics import get_metrics_output, update_active_failures

router = APIRouter(tags=["Observability"])


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description=(
        "Returns Prometheus text-format metrics for the SynapseOps API. "
        "Scrape this endpoint with Prometheus."
    ),
    response_class=Response,
    include_in_schema=True,
)
async def prometheus_metrics(request: Request) -> Response:
    """Return Prometheus text-format metrics.

    Before serialising, refreshes the active_failures gauge from the
    live FailureController state (if available).
    """
    # Refresh simulation failure count gauge
    try:
        controller = getattr(request.app.state, "failure_controller", None)
        if controller is not None:
            state = await controller.get_state()
            update_active_failures(state.total_active)
    except Exception:
        pass  # Metric update failure must never break the endpoint

    content = get_metrics_output()
    return Response(
        content=content,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
