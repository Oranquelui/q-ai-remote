"""Plan lifecycle service.

State transitions:
PENDING_APPROVAL -> APPROVED -> EXECUTED|FAILED
PENDING_APPROVAL -> REJECTED
"""

from __future__ import annotations

import json
import secrets
import string
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from pydantic import ValidationError

from src.core.db import PlanStore
from src.models.plan import Plan

_BASE62 = string.ascii_letters + string.digits


class ApprovalError(RuntimeError):
    """Approval transition error."""


@dataclass(frozen=True)
class ApprovalResult:
    plan_id: str
    status: str


def generate_short_token(length: int = 8) -> str:
    if length < 6:
        raise ValueError("short token length must be >= 6")
    return "".join(secrets.choice(_BASE62) for _ in range(length))


class ApprovalService:
    def __init__(self, store: PlanStore, blocked_risk_levels: Optional[set[str]] = None) -> None:
        self._store = store
        self._blocked_risk_levels = blocked_risk_levels or {"HIGH", "CRITICAL"}

    def create_pending_plan(self, plan: Plan) -> None:
        if plan.status.value != "PENDING_APPROVAL":
            raise ApprovalError("new plan must start at PENDING_APPROVAL")
        self._store.insert_plan(plan)

    def approve(self, plan_id: str, short_token: str) -> ApprovalResult:
        row = self._store.get_plan(plan_id)
        if not row:
            raise ApprovalError("plan not found")
        if row.status != "PENDING_APPROVAL":
            raise ApprovalError(f"plan is not approvable from state={row.status}")
        if row.risk_level in self._blocked_risk_levels:
            raise ApprovalError(f"plan risk level blocked: {row.risk_level}")
        if row.short_token != short_token:
            raise ApprovalError("short token mismatch")

        expires_at = datetime.fromisoformat(row.expires_at)
        now = datetime.now(timezone.utc)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            self._store.update_status(plan_id, "EXPIRED")
            raise ApprovalError("plan approval window expired")

        self._store.update_status(plan_id, "APPROVED", timestamp_col="approved_at")
        return ApprovalResult(plan_id=plan_id, status="APPROVED")

    def reject(self, plan_id: str) -> ApprovalResult:
        row = self._store.get_plan(plan_id)
        if not row:
            raise ApprovalError("plan not found")
        if row.status != "PENDING_APPROVAL":
            raise ApprovalError(f"plan is not rejectable from state={row.status}")

        self._store.update_status(plan_id, "REJECTED", timestamp_col="rejected_at")
        return ApprovalResult(plan_id=plan_id, status="REJECTED")

    def mark_executed(self, plan_id: str) -> None:
        self._store.update_status(plan_id, "EXECUTED", timestamp_col="executed_at")

    def mark_failed(self, plan_id: str) -> None:
        self._store.update_status(plan_id, "FAILED", timestamp_col="executed_at")

    def get_plan(self, plan_id: str) -> Plan:
        row = self._store.get_plan(plan_id)
        if not row:
            raise ApprovalError("plan not found")
        try:
            return Plan.model_validate(json.loads(row.plan_json))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ApprovalError("stored plan is invalid") from exc

    def get_status(self, plan_id: str) -> str:
        row = self._store.get_plan(plan_id)
        if not row:
            raise ApprovalError("plan not found")
        return row.status
