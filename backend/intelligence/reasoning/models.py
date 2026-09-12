from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.events.models import Event
from backend.intelligence.models import RCAResult
from backend.state.models import SystemSnapshot


class IncidentContext(BaseModel):
    """Structured evidence context provided to the AI Reasoning engine.

    This contains strictly bounded, verified structural evidence from Phase 4-6.
    """
    analysis_window_minutes: int = Field(
        description="The time window in minutes evaluated for this incident."
    )
    active_events: list[Event] = Field(
        default_factory=list,
        description="Active events (anomalies, failures) within the system.",
    )
    rca_result: RCAResult | None = Field(
        default=None,
        description="The deterministic root-cause analysis output from Phase 6.",
    )
    system_state: SystemSnapshot | None = Field(
        default=None,
        description="Current system state snapshot, containing service health summaries.",
    )
    topology_nodes: list[str] = Field(
        default_factory=list,
        description="List of component IDs in the known dependency graph.",
    )
    topology_edges: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of dependency edges [{'source': A, 'target': B}] meaning A depends on B.",
    )


class IncidentReasoningResult(BaseModel):
    """The structured, validated output from the AI Reasoning engine."""

    summary: str = Field(
        description="A clear, high-level summary of the incident."
    )
    observed_facts: list[str] = Field(
        default_factory=list,
        description="A list of strict, observed facts derived directly from telemetry and events.",
    )
    likely_root_causes: list[str] = Field(
        default_factory=list,
        description="List of component IDs identified as likely root causes. Must match RCA candidates.",
    )
    propagation_interpretation: str = Field(
        description="Explanation of how the incident propagated across the dependency graph."
    )
    uncertainty: str = Field(
        description="Explicit description of what is uncertain or ambiguous about the incident."
    )
    missing_evidence: list[str] = Field(
        default_factory=list,
        description="List of telemetry or metrics that were expected but missing or unavailable.",
    )
    conflicting_evidence: list[str] = Field(
        default_factory=list,
        description="List of signals that conflict with each other or the primary RCA hypothesis.",
    )
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        description="Confidence level of the AI reasoning interpretation based on available evidence."
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when this reasoning was generated.",
    )
