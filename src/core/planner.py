"""Planner orchestration for /plan."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.adapters.plan_client import PlanDraftClient
from src.config.policy import PolicyConfig
from src.core.approval_service import ApprovalService, generate_short_token
from src.models.plan import Plan, PlanOp, PlanStatus, PolicySnapshot, RequestedBy
from src.security.path_guard import enforce_allowed_path
from src.security.risk_engine import RiskEngine, to_report


class PlannerError(RuntimeError):
    """Plan generation error."""


@dataclass(frozen=True)
class PlannedResult:
    plan: Plan
    summary: str


class PlannerService:
    def __init__(
        self,
        workspace_root: Path,
        policy: PolicyConfig,
        plan_client: PlanDraftClient,
        approval_service: ApprovalService,
    ) -> None:
        self._workspace_root = workspace_root.resolve()
        self._policy = policy
        self._plan_client = plan_client
        self._approval = approval_service
        self._risk_engine = RiskEngine(policy)

    def create_plan(self, request_text: str, user_id: int, chat_id: int) -> PlannedResult:
        draft = self._plan_client.draft_plan(
            request_text=request_text,
            allowed_ops=self._policy.allowed_ops,
            allowed_prefixes=self._policy.allowed_path_prefixes,
        )

        ops: list[PlanOp] = []
        for idx, raw in enumerate(draft.ops, start=1):
            op_id = f"op_{idx}"
            op_type = str(raw.get("type", "")).strip()
            path = _normalize_rel_path(str(raw.get("path", "")).strip())

            op = PlanOp(
                op_id=op_id,
                type=op_type,
                path=path,
                content=raw.get("content"),
                patch=raw.get("patch"),
            )

            # Enforce filesystem policy independently from model validation.
            enforce_allowed_path(
                workspace_root=self._workspace_root,
                rel_path=op.path,
                allowed_prefixes=self._policy.allowed_path_prefixes,
                blocked_patterns=self._policy.blocked_path_patterns,
            )
            ops.append(op)

        if not ops:
            raise PlannerError("generated plan has no operations")

        outcome = self._risk_engine.evaluate_ops(ops)
        risk = to_report(outcome)

        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(minutes=self._policy.plan.ttl_minutes)
        plan_id = "pln_" + created_at.strftime("%Y%m%d%H%M%S") + generate_short_token(6)
        short_token = generate_short_token(self._policy.plan.short_token_length)

        plan = Plan(
            plan_id=plan_id,
            short_token=short_token,
            status=PlanStatus.PENDING_APPROVAL,
            requested_by=RequestedBy(telegram_user_id=user_id, chat_id=chat_id),
            request_text=request_text,
            created_at=created_at,
            expires_at=expires_at,
            policy_snapshot=PolicySnapshot(
                policy_id=self._policy.version,
                allowed_path_prefixes=self._policy.allowed_path_prefixes,
                network_ops=False,
                shell_exec=False,
            ),
            ops=ops,
            risk=risk,
        )

        self._approval.create_pending_plan(plan)
        self._persist_plan_file(plan)

        return PlannedResult(plan=plan, summary=draft.summary)

    def _persist_plan_file(self, plan: Plan) -> None:
        plans_dir = self._workspace_root / self._policy.storage.plans_dir
        plans_dir.mkdir(parents=True, exist_ok=True)
        plan_path = plans_dir / f"{plan.plan_id}.json"
        plan_path.write_text(
            json.dumps(plan.model_dump(mode="json"), indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )


def _normalize_rel_path(path: str) -> str:
    norm = path.replace("\\", "/").strip()
    while "//" in norm:
        norm = norm.replace("//", "/")
    while len(norm) > 1 and norm.endswith("/"):
        norm = norm[:-1]
    return norm
