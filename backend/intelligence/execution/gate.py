from datetime import UTC, datetime

from backend.intelligence.execution.models import ExecutionAuthorization
from backend.intelligence.safety.models import ApprovalStatus, PlanIntegrity


class AuthorizationError(Exception):
    """Raised when execution authorization is invalid or insufficient."""
    pass


class IntegrityError(Exception):
    """Raised when the requested execution plan does not cryptographically match the authorized plan."""
    pass


class ExecutionGate:
    """The strict boundary that verifies authorization immediately prior to execution."""

    def authorize(self, auth_request: ExecutionAuthorization) -> None:
        """
        Validates that the provided authorization satisfies all requirements for execution.
        Raises an exception if any check fails. Returns None if successful.
        """

        # 1. State Verification
        if auth_request.approval.status != ApprovalStatus.APPROVED:
            raise AuthorizationError(f"Cannot execute. Approval status is {auth_request.approval.status}, must be APPROVED.")

        # 2. Expiration Verification
        if datetime.now(UTC) > auth_request.approval.expires_at:
            raise AuthorizationError("Cannot execute. The approval has expired.")

        # 3. Integrity Verification
        current_hash = PlanIntegrity.compute_hash(auth_request.plan)
        if current_hash != auth_request.approval.plan_hash:
            raise IntegrityError(
                "Cannot execute. Plan hash mismatch. "
                "The requested execution plan differs from the approved plan."
            )

        # 4. Identity matching
        if auth_request.approval.plan_id != auth_request.plan.plan_id:
            raise IntegrityError("Cannot execute. Plan ID mismatch.")

        # 5. Permission Verification
        if "recovery.plan.execute" not in auth_request.auth_context.permissions:
            raise AuthorizationError("Cannot execute. Principal lacks 'recovery.plan.execute' permission.")
