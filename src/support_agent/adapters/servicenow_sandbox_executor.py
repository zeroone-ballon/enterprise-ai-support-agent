"""ServiceNow-compatible executor that records locally and never calls a network."""

import sqlite3
from datetime import datetime
from pathlib import Path

from support_agent.domain import (
    AssistResponse,
    ExecutionRequest,
    MockExecutionReceipt,
    ServiceNowSandboxAction,
)


class ServiceNowSandboxExecutor:
    """Translate approved recommendations into a durable local outbox contract."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def execute(
        self,
        response: AssistResponse,
        request: ExecutionRequest,
        executed_at: datetime,
    ) -> MockExecutionReceipt:
        action = self.build_action(response, executed_at)
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                "INSERT INTO servicenow_sandbox_actions VALUES (?, ?, ?, ?)",
                (
                    action.action_id,
                    action.recommendation_id,
                    action.model_dump_json(),
                    action.created_at.isoformat(),
                ),
            )
        return MockExecutionReceipt(
            recommendation_id=response.recommendation_id,
            executor=request.executor,
            executed_at=executed_at,
            summary=(
                f"ServiceNow sandbox action {action.action_id} recorded; "
                "no HTTP call was made."
            ),
        )

    @staticmethod
    def build_action(
        response: AssistResponse,
        created_at: datetime,
    ) -> ServiceNowSandboxAction:
        evidence_ids = ",".join(item.knowledge_id for item in response.evidence)
        proposed_response = (
            response.recommendation.suggested_response or response.recommendation.summary
        )
        return ServiceNowSandboxAction(
            action_id=f"SN-SBX-{response.recommendation_id}",
            recommendation_id=response.recommendation_id,
            target_correlation_id=response.incident_id,
            fields={
                "work_notes": proposed_response,
                "u_ai_recommendation_id": response.recommendation_id,
                "u_ai_evidence_ids": evidence_ids or "none",
                "u_ai_execution_mode": "sandbox",
            },
            created_at=created_at,
        )

    def list_actions(self) -> list[ServiceNowSandboxAction]:
        with sqlite3.connect(self._database_path) as connection:
            rows = connection.execute(
                "SELECT payload_json FROM servicenow_sandbox_actions ORDER BY created_at"
            ).fetchall()
        return [ServiceNowSandboxAction.model_validate_json(row[0]) for row in rows]
