from datetime import UTC, datetime

from backend.intelligence.safety.models import (
    ApprovalRequestResponse,
    ApprovalStatus,
    AuthorizationContext,
)


class ApprovalEngine:
    """Manages Human Approval state machine and enforces Separation of Duties."""

    def approve(
        self,
        approval: ApprovalRequestResponse,
        auth_context: AuthorizationContext,
        plan_hash: str,
    ) -> ApprovalRequestResponse:
        """Approve a pending request."""

        # 1. Integrity Check
        if approval.plan_hash != plan_hash:
            raise ValueError("Plan hash mismatch. The plan has been modified since approval was requested.")

        # 2. State Check
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval is currently {approval.status}. Only PENDING approvals can be approved.")

        # 3. Expiration Check
        if datetime.now(UTC) > approval.expires_at:
            approval.status = ApprovalStatus.EXPIRED
            raise ValueError("Approval request has expired.")

        # 4. Separation of Duties Check
        if approval.requested_by == auth_context.principal:
            raise PermissionError("Separation of duties violation: Requester cannot approve their own request.")

        # 5. Permission Check
        if "recovery.plan.approve" not in auth_context.permissions:
            raise PermissionError("Principal lacks 'recovery.plan.approve' permission.")

        # Success
        approval.status = ApprovalStatus.APPROVED
        return approval

    def reject(
        self,
        approval: ApprovalRequestResponse,
        auth_context: AuthorizationContext,
        plan_hash: str,
    ) -> ApprovalRequestResponse:
        """Reject a pending request."""

        if approval.plan_hash != plan_hash:
            raise ValueError("Plan hash mismatch.")

        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval is currently {approval.status}. Only PENDING approvals can be rejected.")

        approval.status = ApprovalStatus.REJECTED
        return approval
