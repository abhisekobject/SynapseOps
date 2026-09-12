import asyncio
import time
from datetime import UTC, datetime

from backend.intelligence.execution.gate import AuthorizationError, ExecutionGate, IntegrityError
from backend.intelligence.execution.models import (
    ExecutionAuthorization,
    ExecutionResult,
    ExecutionStatus,
)
from backend.intelligence.execution.registry import ExecutorRegistry


class ExecutionEngine:
    """Coordinates the execution of an authorized RecoveryPlan."""

    def __init__(self, gate: ExecutionGate, timeout_seconds: float = 10.0):
        self.gate = gate
        self.timeout_seconds = timeout_seconds

    async def execute(self, auth: ExecutionAuthorization) -> list[ExecutionResult]:
        """
        Executes an authorized plan.
        Immediately rejects if authorization fails.
        Handles execution timeouts and failures safely without automatic retries.
        """
        # 1. Authorize - Fails explicitly if unauthorized
        try:
            self.gate.authorize(auth)
        except (AuthorizationError, IntegrityError) as e:
            # We return a REJECTED result for the first step as a record
            if not auth.plan.steps:
                raise ValueError("Plan contains no steps to reject.") from e

            first_step = auth.plan.steps[0]
            return [
                ExecutionResult(
                    plan_id=auth.plan.plan_id,
                    approval_id=auth.approval.approval_id,
                    plan_hash=auth.approval.plan_hash,
                    action_type=first_step.action_type,
                    target=first_step.target_component,
                    executor_type="NONE",
                    status=ExecutionStatus.REJECTED,
                    error_category=e.__class__.__name__,
                    error_message=str(e),
                )
            ]

        results = []

        # 2. Execute Steps
        for step in auth.plan.steps:
            started_at = datetime.now(UTC)
            start_time = time.monotonic()

            try:
                executor = ExecutorRegistry.get_executor(step.action_type)
            except ValueError as e:
                results.append(
                    ExecutionResult(
                        plan_id=auth.plan.plan_id,
                        approval_id=auth.approval.approval_id,
                        plan_hash=auth.approval.plan_hash,
                        action_type=step.action_type,
                        target=step.target_component,
                        executor_type="UNKNOWN",
                        status=ExecutionStatus.FAILED,
                        error_category="UnsupportedActionError",
                        error_message=str(e),
                        started_at=started_at,
                        completed_at=datetime.now(UTC),
                        duration_seconds=time.monotonic() - start_time,
                    )
                )
                # Stop executing further steps in this plan
                break

            executor_name = executor.__class__.__name__

            try:
                # 3. Timeout bounds
                success = await asyncio.wait_for(
                    executor.execute(step.target_component),
                    timeout=self.timeout_seconds,
                )
                status = ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILED

                results.append(
                    ExecutionResult(
                        plan_id=auth.plan.plan_id,
                        approval_id=auth.approval.approval_id,
                        plan_hash=auth.approval.plan_hash,
                        action_type=step.action_type,
                        target=step.target_component,
                        executor_type=executor_name,
                        status=status,
                        started_at=started_at,
                        completed_at=datetime.now(UTC),
                        duration_seconds=time.monotonic() - start_time,
                    )
                )

                if not success:
                    # Halt plan execution if a step fails
                    break

            except TimeoutError:
                results.append(
                    ExecutionResult(
                        plan_id=auth.plan.plan_id,
                        approval_id=auth.approval.approval_id,
                        plan_hash=auth.approval.plan_hash,
                        action_type=step.action_type,
                        target=step.target_component,
                        executor_type=executor_name,
                        status=ExecutionStatus.TIMEOUT,
                        error_category="TimeoutError",
                        error_message=f"Execution exceeded timeout of {self.timeout_seconds}s.",
                        started_at=started_at,
                        completed_at=datetime.now(UTC),
                        duration_seconds=time.monotonic() - start_time,
                    )
                )
                # Halt on timeout
                break

            except Exception as e:
                results.append(
                    ExecutionResult(
                        plan_id=auth.plan.plan_id,
                        approval_id=auth.approval.approval_id,
                        plan_hash=auth.approval.plan_hash,
                        action_type=step.action_type,
                        target=step.target_component,
                        executor_type=executor_name,
                        status=ExecutionStatus.FAILED,
                        error_category=e.__class__.__name__,
                        error_message=str(e),
                        started_at=started_at,
                        completed_at=datetime.now(UTC),
                        duration_seconds=time.monotonic() - start_time,
                    )
                )
                break

        return results
