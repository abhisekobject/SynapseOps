import uuid
from collections import defaultdict
from datetime import UTC, datetime

import structlog

from backend.events.models import Event, EventSeverity, EventType
from backend.intelligence.graph import DependencyGraph
from backend.intelligence.models import RCACandidate, RCAEvidence, RCAResult

logger = structlog.get_logger("intelligence.rca")


class RCAEngine:
    """Deterministic, evidence-based Root Cause Analysis engine."""

    def __init__(self, graph: DependencyGraph) -> None:
        self._graph = graph

    def _map_event_to_node(self, event: Event) -> str:
        """Map an operational event or anomaly to a topology node."""
        if event.event_type in [
            EventType.DATABASE_LATENCY_INCREASE,
            EventType.ANOMALY_DATABASE_LATENCY,
        ]:
            return "database"
        return event.service_id

    def analyze(self, active_events: list[Event], window_minutes: int = 5) -> RCAResult:
        """Analyze current active events and return ranked root-cause candidates."""

        now = datetime.now(UTC)
        cutoff_time = now.timestamp() - (window_minutes * 60)

        # Filter for events relevant to our analysis window
        recent_events = [
            e for e in active_events
            if e.created_at.timestamp() >= cutoff_time or e.updated_at.timestamp() >= cutoff_time
        ]

        # Group events by their target topology node
        node_events: dict[str, list[Event]] = defaultdict(list)
        for ev in recent_events:
            node = self._map_event_to_node(ev)
            node_events[node].append(ev)

        candidates: list[RCACandidate] = []

        # All anomalous nodes are candidates
        anomalous_nodes = list(node_events.keys())

        for node in anomalous_nodes:
            score = 0.0
            evidence = []
            affected_components = []

            node_earliest_time = min(e.created_at for e in node_events[node])

            # 1. Evaluate temporal precedence & downstream propagation
            downstream = self._graph.get_transitive_dependents(node)
            propagated_count = 0

            for d_node in downstream:
                if d_node in anomalous_nodes:
                    d_earliest_time = min(e.created_at for e in node_events[d_node])
                    if node_earliest_time <= d_earliest_time:
                        propagated_count += 1
                        affected_components.append(d_node)
                        score += 0.2
                        evidence.append(
                            RCAEvidence(
                                type="temporal_precedence",
                                description=f"Anomaly on '{node}' preceded downstream anomaly on '{d_node}'",
                                weight=0.2,
                            )
                        )

            # 2. Direct dependency downstream checks
            direct_downstream = self._graph.get_direct_dependents(node)
            for d_node in direct_downstream:
                if d_node in affected_components:
                    score += 0.1
                    evidence.append(
                        RCAEvidence(
                            type="direct_dependency",
                            description=f"Direct dependent '{d_node}' is affected",
                            weight=0.1,
                        )
                    )

            # 3. Upstream checks (reduce score if upstream is also anomalous BEFORE this node)
            upstream = self._graph.get_transitive_dependencies(node)
            is_downstream_victim = False
            for u_node in upstream:
                if u_node in anomalous_nodes:
                    u_earliest_time = min(e.created_at for e in node_events[u_node])
                    if u_earliest_time <= node_earliest_time:
                        is_downstream_victim = True
                        break

            if is_downstream_victim:
                evidence.append(
                    RCAEvidence(
                        type="upstream_propagation",
                        description=f"Node '{node}' became anomalous AFTER its upstream dependency.",
                        weight=-0.3,
                    )
                )
                score -= 0.3
            else:
                score += 0.2
                evidence.append(
                    RCAEvidence(
                        type="origin_node",
                        description=f"Node '{node}' has no anomalous upstream dependencies.",
                        weight=0.2,
                    )
                )

            # 4. Severity Weighting
            has_critical = any(e.severity == EventSeverity.CRITICAL for e in node_events[node])
            if has_critical:
                score += 0.1
                evidence.append(
                    RCAEvidence(
                        type="severity",
                        description=f"Node '{node}' is experiencing CRITICAL severity issues.",
                        weight=0.1,
                    )
                )

            # 5. Signal Consistency
            if len(node_events[node]) > 1:
                score += 0.1
                evidence.append(
                    RCAEvidence(
                        type="signal_consistency",
                        description=f"Node '{node}' has multiple independent anomalous signals.",
                        weight=0.1,
                    )
                )

            # Clamp score
            score = max(0.0, min(1.0, score))

            confidence = "LOW"
            if score >= 0.8:
                confidence = "HIGH"
            elif score >= 0.5:
                confidence = "MEDIUM"

            candidates.append(
                RCACandidate(
                    component=node,
                    score=score,
                    evidence=evidence,
                    affected_components=affected_components,
                    confidence=confidence,
                )
            )

        # Sort by score descending. Deterministic tie-breaker: sort by component name alphabetically.
        candidates.sort(key=lambda c: (-c.score, c.component))

        return RCAResult(
            analysis_id=uuid.uuid4(),
            timestamp=now,
            window_minutes=window_minutes,
            candidates=candidates,
        )
