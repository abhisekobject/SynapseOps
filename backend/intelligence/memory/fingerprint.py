import hashlib
import json


class FingerprintGenerator:
    """Generates a deterministic SHA-256 fingerprint for an Experience."""

    @staticmethod
    def generate(
        target_component: str,
        action_type: str,
        expected_outcome: str,
        observed_outcome: str,
        outcome_state: str,
        feedback_type: str,
        learning_signal_type: str,
        is_simulated: bool,
        environment: str,
    ) -> str:
        """
        Hashes the core semantic state of an episode.
        Does NOT include volatile IDs, timestamps, or metadata.
        """
        state_dict = {
            "action_type": action_type,
            "environment": environment,
            "expected_outcome": expected_outcome,
            "feedback_type": feedback_type,
            "is_simulated": is_simulated,
            "learning_signal_type": learning_signal_type,
            "observed_outcome": observed_outcome,
            "outcome_state": outcome_state,
            "target_component": target_component,
        }

        # Deterministic JSON serialization
        canonical_json = json.dumps(state_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
