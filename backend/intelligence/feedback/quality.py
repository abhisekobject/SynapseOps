from datetime import UTC, datetime

from backend.intelligence.feedback.models import (
    EvidenceCompleteness,
    EvidenceConsistency,
    FeedbackQuality,
)
from backend.intelligence.outcomes.models import OutcomeAssessment, OutcomeState


class FeedbackQualityAssessor:
    """Evaluates the quality of evidence underlying an OutcomeAssessment."""

    def assess(self, assessment: OutcomeAssessment) -> FeedbackQuality:
        """Deterministically evaluates evidence completeness, consistency, and freshness."""

        # 1. Evidence Completeness
        if not assessment.evidence or assessment.outcome_status == OutcomeState.UNKNOWN:
            completeness = EvidenceCompleteness.MISSING
        else:
            completeness = EvidenceCompleteness.COMPLETE

        # 2. Evidence Consistency
        if assessment.outcome_status == OutcomeState.PARTIAL:
            consistency = EvidenceConsistency.CONFLICTING
        elif assessment.outcome_status in (OutcomeState.VERIFIED_SUCCESS, OutcomeState.VERIFIED_FAILURE):
            consistency = EvidenceConsistency.CONSISTENT
        else:
            consistency = EvidenceConsistency.UNKNOWN

        # 3. Freshness (arbitrarily defined as < 1 hour for v0, though normally we'd check timestamps)
        time_since_assessment = (datetime.now(UTC) - assessment.assessed_at).total_seconds()
        is_fresh = time_since_assessment < 3600

        return FeedbackQuality(
            evidence_completeness=completeness,
            evidence_consistency=consistency,
            is_fresh=is_fresh,
            is_simulated=assessment.is_simulated,
            confidence=assessment.confidence,
        )
