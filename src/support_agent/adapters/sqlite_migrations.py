"""Ordered, repeatable SQLite schema migrations."""

import sqlite3

MIGRATIONS: tuple[tuple[int, str], ...] = (
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS recommendations (
            recommendation_id TEXT PRIMARY KEY,
            response_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_events (
            recommendation_id TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            event_json TEXT NOT NULL,
            PRIMARY KEY (recommendation_id, sequence),
            FOREIGN KEY (recommendation_id) REFERENCES recommendations(recommendation_id)
        );
        """,
    ),
    (
        2,
        """
        CREATE TABLE IF NOT EXISTS execution_results (
            recommendation_id TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            result_json TEXT NOT NULL,
            PRIMARY KEY (recommendation_id, idempotency_key),
            FOREIGN KEY (recommendation_id) REFERENCES recommendations(recommendation_id)
        );
        """,
    ),
    (
        3,
        """
        CREATE TABLE IF NOT EXISTS servicenow_sandbox_actions (
            action_id TEXT PRIMARY KEY,
            recommendation_id TEXT NOT NULL UNIQUE,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (recommendation_id) REFERENCES recommendations(recommendation_id)
        );
        """,
    ),
)


def apply_migrations(connection: sqlite3.Connection) -> None:
    """Apply each missing migration exactly once inside SQLite transactions."""

    connection.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
               version INTEGER PRIMARY KEY,
               applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
           )"""
    )
    applied = {
        row[0] for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
    }
    for version, sql in MIGRATIONS:
        if version in applied:
            continue
        connection.executescript(sql)
        connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
