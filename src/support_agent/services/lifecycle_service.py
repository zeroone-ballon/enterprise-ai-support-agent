"""Human approval state machine with append-only auditing and mock execution."""

from collections.abc import Callable
from datetime import UTC, datetime
from threading import RLock

from support_agent.domain import (
    Approval,
    ApprovalDecision,
    ApprovalStatus,
    AssistResponse,
    AuditEvent,
    AuditEventType,
    ExecutionRequest,
    ExecutionResult,
    Incident,
    MockExecutionReceipt,
    RecommendationStatus,
    RejectionDecision,
)
from support_agent.domain.ports import ExecutionPort, LifecycleRepository
from support_agent.services.assist_service import AssistService


class InvalidTransitionError(ValueError):
    """Raised when a requested lifecycle transition is not allowed."""


class MockExecutor:
    """Return an execution receipt without touching any external system."""

    def execute(
        self,
        response: AssistResponse,
        request: ExecutionRequest,
        executed_at: datetime,
    ) -> MockExecutionReceipt:
        return MockExecutionReceipt(
            recommendation_id=response.recommendation_id,
            executor=request.executor,
            executed_at=executed_at,
        )


class RecommendationLifecycleService:
    """Coordinate creation, human decisions, mock execution, and audit history."""

    def __init__(
        self,
        assist_service: AssistService,
        repository: LifecycleRepository,
        *,
        clock: Callable[[], datetime] | None = None,
        executor: ExecutionPort | None = None,
    ) -> None:
        self._assist_service = assist_service
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._executor = executor or MockExecutor()
        self._lock = RLock()

    def create(self, incident: Incident) -> AssistResponse:
        with self._lock:
            response = self._assist_service.assist(incident)
            self._repository.create(response)
            self._append_event(
                response.recommendation_id,
                AuditEventType.CREATED,
                "system",
                {"incident_id": incident.incident_id},
            )
            return response

    def get(self, recommendation_id: str) -> AssistResponse:
        return self._repository.get(recommendation_id)

    def approve(
        self,
        recommendation_id: str,
        decision: ApprovalDecision,
    ) -> AssistResponse:
        with self._lock:
            response = self._repository.get(recommendation_id)
            self._require_pending(response)
            if response.recommendation.status is RecommendationStatus.ABSTAINED:
                raise InvalidTransitionError("an abstained recommendation cannot be approved")

            decided_at = self._clock()
            updated = response.model_copy(
                update={
                    "approval": Approval(
                        status=ApprovalStatus.APPROVED,
                        reviewer=decision.reviewer,
                        reason=decision.reason,
                        decided_at=decided_at,
                    )
                }
            )
            self._repository.save(updated)
            self._append_event(
                recommendation_id,
                AuditEventType.APPROVED,
                decision.reviewer,
                {"reason": decision.reason or ""},
            )
            return updated

    def reject(
        self,
        recommendation_id: str,
        decision: RejectionDecision,
    ) -> AssistResponse:
        with self._lock:
            response = self._repository.get(recommendation_id)
            self._require_pending(response)
            decided_at = self._clock()
            updated = response.model_copy(
                update={
                    "approval": Approval(
                        status=ApprovalStatus.REJECTED,
                        reviewer=decision.reviewer,
                        reason=decision.reason,
                        decided_at=decided_at,
                    )
                }
            )
            self._repository.save(updated)
            self._append_event(
                recommendation_id,
                AuditEventType.REJECTED,
                decision.reviewer,
                {"reason": decision.reason},
            )
            return updated

    def execute(
        self,
        recommendation_id: str,
        request: ExecutionRequest,
    ) -> ExecutionResult:
        with self._lock:
            response = self._repository.get(recommendation_id)
            if response.approval.status is not ApprovalStatus.APPROVED:
                raise InvalidTransitionError("mock execution requires approved status")

            executed_at = self._clock()
            receipt = self._executor.execute(response, request, executed_at)
            updated = response.model_copy(
                update={
                    "approval": response.approval.model_copy(
                        update={"status": ApprovalStatus.EXECUTED, "executed_at": executed_at}
                    )
                }
            )
            self._repository.save(updated)
            self._append_event(
                recommendation_id,
                AuditEventType.EXECUTED,
                request.executor,
                {"side_effects": "false"},
            )
            return ExecutionResult(recommendation=updated, receipt=receipt)

    def audit(self, recommendation_id: str) -> list[AuditEvent]:
        return self._repository.list_events(recommendation_id)

    def _append_event(
        self,
        recommendation_id: str,
        event_type: AuditEventType,
        actor: str,
        details: dict[str, str],
    ) -> None:
        sequence = len(self._repository.list_events(recommendation_id)) + 1
        self._repository.append_event(
            AuditEvent(
                sequence=sequence,
                recommendation_id=recommendation_id,
                event_type=event_type,
                actor=actor,
                occurred_at=self._clock(),
                details=details,
            )
        )

    @staticmethod
    def _require_pending(response: AssistResponse) -> None:
        if response.approval.status is not ApprovalStatus.PENDING:
            raise InvalidTransitionError("decision requires pending_approval status")
