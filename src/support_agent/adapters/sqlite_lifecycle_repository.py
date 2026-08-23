"""Durable SQLite lifecycle repository."""

import sqlite3
from pathlib import Path
from threading import RLock

from support_agent.adapters.lifecycle_errors import (
    DuplicateRecommendationError,
    RecommendationNotFoundError,
)
from support_agent.adapters.sqlite_migrations import apply_migrations
from support_agent.domain import AssistResponse, AuditEvent, ExecutionResult


class SqliteLifecycleRepository:
    """Persist recommendation state, audit events, and idempotent execution results."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            apply_migrations(connection)

    def create(self, response: AssistResponse) -> None:
        with self._lock, self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO recommendations VALUES (?, ?)",
                    (response.recommendation_id, response.model_dump_json()),
                )
            except sqlite3.IntegrityError as error:
                raise DuplicateRecommendationError(response.recommendation_id) from error

    def get(self, recommendation_id: str) -> AssistResponse:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT response_json FROM recommendations WHERE recommendation_id = ?",
                (recommendation_id,),
            ).fetchone()
        if row is None:
            raise RecommendationNotFoundError(recommendation_id)
        return AssistResponse.model_validate_json(row[0])

    def save(self, response: AssistResponse) -> None:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "UPDATE recommendations SET response_json = ? WHERE recommendation_id = ?",
                (response.model_dump_json(), response.recommendation_id),
            )
            if cursor.rowcount == 0:
                raise RecommendationNotFoundError(response.recommendation_id)

    def append_event(self, event: AuditEvent) -> None:
        with self._lock, self._connect() as connection:
            expected = connection.execute(
                "SELECT COUNT(*) + 1 FROM audit_events WHERE recommendation_id = ?",
                (event.recommendation_id,),
            ).fetchone()[0]
            if event.sequence != expected:
                raise ValueError("audit event sequence must be contiguous")
            try:
                connection.execute(
                    "INSERT INTO audit_events VALUES (?, ?, ?)",
                    (event.recommendation_id, event.sequence, event.model_dump_json()),
                )
            except sqlite3.IntegrityError as error:
                raise RecommendationNotFoundError(event.recommendation_id) from error

    def list_events(self, recommendation_id: str) -> list[AuditEvent]:
        self.get(recommendation_id)
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT event_json FROM audit_events WHERE recommendation_id = ? ORDER BY sequence",
                (recommendation_id,),
            ).fetchall()
        return [AuditEvent.model_validate_json(row[0]) for row in rows]

    def get_execution(self, recommendation_id: str, idempotency_key: str) -> ExecutionResult | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """SELECT result_json FROM execution_results
                   WHERE recommendation_id = ? AND idempotency_key = ?""",
                (recommendation_id, idempotency_key),
            ).fetchone()
        return ExecutionResult.model_validate_json(row[0]) if row else None

    def save_execution(
        self,
        recommendation_id: str,
        idempotency_key: str,
        result: ExecutionResult,
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO execution_results VALUES (?, ?, ?)",
                (recommendation_id, idempotency_key, result.model_dump_json()),
            )
