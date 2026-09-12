from collections.abc import Sequence

from backend.intelligence.memory.models import (
    Experience,
    RelevanceScore,
    RetrievalQuery,
    RetrievalResult,
    RetrievedExperience,
)


class RetrievalEngine:
    """Deterministically retrieves and scores historical experiences."""

    def retrieve(
        self, query: RetrievalQuery, experiences: Sequence[Experience]
    ) -> RetrievalResult:
        """
        Calculates a deterministic relevance score for each experience against the query.
        Returns the top results sorted by score descending.
        """
        results = []

        for exp in experiences:
            score_val = 0
            reasons = []

            # Simulation Constraint
            if query.is_simulated is not None:
                if query.is_simulated != exp.is_simulated:
                    score_val -= 50
                    reasons.append("MISMATCH: simulation status")
                else:
                    score_val += 5
                    reasons.append("MATCH: simulation status")

            # Target Component
            if query.target_component and query.target_component == exp.target_component:
                score_val += 20
                reasons.append("MATCH: target_component")

            # Action Type
            if query.action_type and str(query.action_type) == exp.action_type:
                score_val += 15
                reasons.append("MATCH: action_type")

            # Outcome State
            if query.outcome_state and str(query.outcome_state) == exp.outcome_state:
                score_val += 10
                reasons.append("MATCH: outcome_state")

            # Feedback Type
            if query.feedback_type and str(query.feedback_type) == exp.feedback_type:
                score_val += 5
                reasons.append("MATCH: feedback_type")

            # Expected Outcome
            if query.expected_outcome and query.expected_outcome == exp.expected_outcome:
                score_val += 5
                reasons.append("MATCH: expected_outcome")

            # Observed Outcome
            if query.observed_outcome and query.observed_outcome == exp.observed_outcome:
                score_val += 5
                reasons.append("MATCH: observed_outcome")

            # Learning Signal Type
            if query.learning_signal_type and str(query.learning_signal_type) == exp.learning_signal_type:
                score_val += 5
                reasons.append("MATCH: learning_signal_type")

            # Environment
            if query.environment and query.environment == exp.environment:
                score_val += 10
                reasons.append("MATCH: environment")

            # Keep only items that have at least some relevance (and are not heavily penalized)
            if score_val > 0:
                relevance = RelevanceScore(score=score_val, reasons=reasons)
                results.append(RetrievedExperience(experience=exp, relevance=relevance))

        # Sort by score descending, then experience_id ascending for deterministic tie-breaking
        results.sort(key=lambda x: (-x.relevance.score, x.experience.experience_id))

        return RetrievalResult(
            query=query,
            results=results,
            is_simulated=query.is_simulated if query.is_simulated is not None else False,
        )
