"""Lightweight SQLite audit logging with OpenTelemetry spans."""
from __future__ import annotations

import sqlite3
from contextvars import ContextVar
from datetime import datetime
from typing import Optional

from opentelemetry.trace import get_tracer

_db: ContextVar[Optional[sqlite3.Connection]] = ContextVar("audit_db", default=None)
_tracer = get_tracer(__name__)


def init_db(path: str = "audit.db") -> sqlite3.Connection:
    """Initialize the audit database and ensure the schema exists."""
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            actor TEXT,
            action TEXT,
            target TEXT,
            status TEXT,
            details TEXT
        )
        """
    )
    conn.commit()
    return conn


def bind_connection(conn: sqlite3.Connection):
    """Bind a connection to the request context for reuse inside the middleware."""
    return _db.set(conn)


def reset_connection(token) -> None:
    """Reset the connection context to the previous value."""
    _db.reset(token)


def log_action(
    actor: str,
    action: str,
    target: str,
    status: str = "success",
    details: str = "",
) -> None:
    """Persist an audit record for the provided action."""
    with _tracer.start_as_current_span("audit.log_action"):
        conn = _db.get()
        if conn is None:
            conn = init_db()
        conn.execute(
            "INSERT INTO audit (timestamp, actor, action, target, status, details) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), actor, action, target, status, details),
        )
        conn.commit()
