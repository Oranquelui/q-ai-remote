"""SQLite persistence helpers."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

from src.models.plan import Plan


@dataclass(frozen=True)
class PlanRow:
    plan_id: str
    short_token: str
    status: str
    risk_score: int
    risk_level: str
    created_at: str
    expires_at: str
    plan_json: str


class PlanStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def apply_schema(self, schema_sql: str) -> None:
        with self._conn() as conn:
            conn.executescript(schema_sql)

    def insert_plan(self, plan: Plan) -> None:
        payload = plan.model_dump(mode="json")
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO plans (
                    plan_id, short_token, status, request_text, plan_json,
                    risk_score, risk_level, requested_by_user_id, chat_id,
                    created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan.plan_id,
                    plan.short_token,
                    plan.status.value,
                    plan.request_text,
                    json.dumps(payload, ensure_ascii=True),
                    plan.risk.score,
                    plan.risk.level.value,
                    plan.requested_by.telegram_user_id,
                    plan.requested_by.chat_id,
                    plan.created_at.isoformat(),
                    plan.expires_at.isoformat(),
                ),
            )

    def get_plan(self, plan_id: str) -> Optional[PlanRow]:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT plan_id, short_token, status, risk_score, risk_level,
                       created_at, expires_at, plan_json
                FROM plans WHERE plan_id = ?
                """,
                (plan_id,),
            ).fetchone()
        if row is None:
            return None
        return PlanRow(
            plan_id=row["plan_id"],
            short_token=row["short_token"],
            status=row["status"],
            risk_score=row["risk_score"],
            risk_level=row["risk_level"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            plan_json=row["plan_json"],
        )

    def get_plan_owner_user_id(self, plan_id: str) -> Optional[int]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT requested_by_user_id FROM plans WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()
        if row is None:
            return None
        return int(row["requested_by_user_id"])

    def update_status(self, plan_id: str, status: str, timestamp_col: Optional[str] = None) -> None:
        with self._conn() as conn:
            if timestamp_col:
                conn.execute(
                    f"UPDATE plans SET status=?, {timestamp_col}=CURRENT_TIMESTAMP WHERE plan_id=?",
                    (status, plan_id),
                )
            else:
                conn.execute("UPDATE plans SET status=? WHERE plan_id=?", (status, plan_id))

    def insert_event(
        self,
        event_id: str,
        plan_id: str,
        event_type: str,
        status: str,
        payload_json: str,
        prev_hash: str,
        event_hash: str,
        op_id: Optional[str] = None,
        op_type: Optional[str] = None,
        target_path: Optional[str] = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO events (
                    event_id, plan_id, event_type, status, op_id, op_type,
                    target_path, payload_json, prev_hash, event_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    event_id,
                    plan_id,
                    event_type,
                    status,
                    op_id,
                    op_type,
                    target_path,
                    payload_json,
                    prev_hash,
                    event_hash,
                ),
            )

    def insert_audit_summary(
        self,
        plan_id: str,
        final_status: str,
        risk_score: int,
        risk_level: str,
        op_count: int,
        write_op_count: int,
        diff_path: Optional[str],
        html_report_path: Optional[str],
        jsonl_path: str,
        chain_head_hash: str,
        duration_ms: int,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO audit (
                    plan_id, final_status, risk_score, risk_level,
                    op_count, write_op_count, diff_path, html_report_path,
                    jsonl_path, chain_head_hash, started_at, finished_at, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?)
                """,
                (
                    plan_id,
                    final_status,
                    risk_score,
                    risk_level,
                    op_count,
                    write_op_count,
                    diff_path,
                    html_report_path,
                    jsonl_path,
                    chain_head_hash,
                    duration_ms,
                ),
            )

    def get_audit_summary(self, plan_id: str) -> Optional[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute(
                """
                SELECT plan_id, final_status, diff_path, html_report_path,
                       jsonl_path, chain_head_hash, duration_ms, started_at, finished_at
                FROM audit WHERE plan_id = ? ORDER BY id DESC LIMIT 1
                """,
                (plan_id,),
            ).fetchone()

    def list_plans_for_user(self, user_id: int, limit: int = 20, status: Optional[str] = None) -> list[sqlite3.Row]:
        safe_limit = max(1, min(int(limit), 50))
        with self._conn() as conn:
            if status:
                rows = conn.execute(
                    """
                    SELECT plan_id, short_token, status, risk_score, risk_level, created_at, expires_at
                    FROM plans
                    WHERE requested_by_user_id = ? AND status = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (user_id, status, safe_limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT plan_id, short_token, status, risk_score, risk_level, created_at, expires_at
                    FROM plans
                    WHERE requested_by_user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (user_id, safe_limit),
                ).fetchall()
        return list(rows)
