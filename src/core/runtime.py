"""Application runtime wiring."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from src.adapters.chat_factory import create_chat_client
from src.adapters.planner_factory import create_planner_client
from src.audit.audit_logger import AuditLogger
from src.audit.report_builder import ReportArtifact, ReportBuilder
from src.config.policy import PolicyConfig, ensure_storage_dirs, load_policy
from src.config.secrets import load_runtime_secrets
from src.core.approval_service import ApprovalError, ApprovalService
from src.core.db import PlanStore
from src.core.diff_service import DiffService
from src.core.executor import ExecutionResult, Executor
from src.core.planner import PlannerService
from src.models.plan import Plan
from src.security.rate_limit import LimitPolicy, RateLimitExceeded, RateLimiter


class RuntimePolicyError(RuntimeError):
    """Access rejected due to policy."""


@dataclass(frozen=True)
class LogsView:
    plan_id: str
    final_status: str
    diff_path: str
    html_report_path: str
    jsonl_path: str


@dataclass(frozen=True)
class PlanListItem:
    plan_id: str
    short_token: str
    status: str
    risk_level: str
    risk_score: int
    created_at: str
    expires_at: str


class AppRuntime:
    def __init__(
        self,
        workspace_root: Path,
        policy_path: Path,
        secret_service_name: str = "qcodeanzenn",
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.policy: PolicyConfig = load_policy(policy_path)
        ensure_storage_dirs(self.workspace_root, self.policy.storage)
        self.instance_id = self.policy.instance.id
        self.secret_service_name = secret_service_name

        db_path = self.workspace_root / self.policy.storage.sqlite
        self.store = PlanStore(db_path)
        schema_sql = (self.workspace_root / "db/schema.sql").read_text(encoding="utf-8")
        self.store.apply_schema(schema_sql)

        self.approval = ApprovalService(
            store=self.store,
            blocked_risk_levels=set(self.policy.risk_block_levels),
        )

        engine_mode = self.policy.engine.mode
        secrets = load_runtime_secrets(
            service_name=secret_service_name,
            require_codex_api_key=(engine_mode == "codex_api"),
            require_claude_api_key=(engine_mode == "claude_api"),
        )
        self.telegram_bot_token = secrets.telegram_bot_token

        plan_client = create_planner_client(
            policy=self.policy,
            workspace_root=self.workspace_root,
            codex_api_key=secrets.codex_api_key,
            claude_api_key=secrets.claude_api_key,
        )
        self.chat_client = create_chat_client(
            policy=self.policy,
            workspace_root=self.workspace_root,
            codex_api_key=secrets.codex_api_key,
            claude_api_key=secrets.claude_api_key,
        )
        self.planner = PlannerService(
            workspace_root=self.workspace_root,
            policy=self.policy,
            plan_client=plan_client,
            approval_service=self.approval,
        )
        self.diff = DiffService(self.workspace_root / self.policy.storage.audit_diff_dir)
        self.executor = Executor(
            workspace_root=self.workspace_root,
            policy=self.policy,
            approval_service=self.approval,
            diff_service=self.diff,
        )
        self.audit = AuditLogger(self.workspace_root / self.policy.storage.audit_jsonl_dir, store=self.store)
        self.report = ReportBuilder(self.workspace_root / self.policy.storage.audit_html_dir)
        self.rates = RateLimiter()

    def _enforce_allowlist(self, user_id: int) -> None:
        allowlist = self.policy.allowlist_user_ids
        if self.policy.fail_closed_when_empty and not allowlist:
            raise RuntimePolicyError("allowlist is empty and fail-closed is enabled")
        if allowlist and user_id not in allowlist:
            raise RuntimePolicyError("user is not in allowlist")

    def _check_rate(self, user_id: int, kind: str) -> None:
        cfg = self.policy.rate_limit
        if kind == "command":
            limit = LimitPolicy(max_events=cfg.command_per_minute, window_sec=60)
        elif kind == "plan":
            limit = LimitPolicy(max_events=cfg.plan_per_minute, window_sec=60)
        elif kind == "approve":
            limit = LimitPolicy(max_events=cfg.approve_per_minute, window_sec=60)
        else:
            limit = LimitPolicy(max_events=cfg.command_per_minute, window_sec=60)
        self.rates.check(user_id=user_id, channel=kind, policy=limit)

    def _enforce_plan_owner(self, plan_id: str, user_id: int) -> None:
        owner_user_id = self.store.get_plan_owner_user_id(plan_id)
        if owner_user_id is None or owner_user_id != user_id:
            raise ApprovalError("plan not found")

    def create_plan(self, request_text: str, user_id: int, chat_id: int) -> Plan:
        self._enforce_allowlist(user_id)
        self._check_rate(user_id, "plan")

        result = self.planner.create_plan(request_text=request_text, user_id=user_id, chat_id=chat_id)
        self.audit.append(
            plan_id=result.plan.plan_id,
            event_type="PLAN_CREATED",
            status=result.plan.status.value,
            payload={
                "risk_level": result.plan.risk.level.value,
                "risk_score": result.plan.risk.score,
                "ops_count": len(result.plan.ops),
            },
        )
        return result.plan

    def approve_and_execute(
        self,
        plan_id: str,
        short_token: str,
        user_id: int,
    ) -> tuple[ExecutionResult, ReportArtifact, Path]:
        self._enforce_allowlist(user_id)
        self._check_rate(user_id, "approve")
        self._enforce_plan_owner(plan_id=plan_id, user_id=user_id)

        self.approval.approve(plan_id=plan_id, short_token=short_token)
        plan = self.approval.get_plan(plan_id)

        self.audit.append(
            plan_id=plan_id,
            event_type="APPROVED",
            status="APPROVED",
            payload={"approved_by": user_id},
        )

        exec_started = time.perf_counter()
        try:
            result = self.executor.execute_approved_plan(plan)
        except RuntimeError as exc:
            duration_ms = int((time.perf_counter() - exec_started) * 1000)
            self.audit.append(
                plan_id=plan.plan_id,
                event_type="EXECUTION_FAILED",
                status="FAILED",
                payload={"error": str(exc)},
            )
            jsonl_path = self.audit.jsonl_path_for(plan.plan_id)
            chain_head = self.audit.last_hash_for(plan.plan_id)
            self.store.insert_audit_summary(
                plan_id=plan.plan_id,
                final_status="FAILED",
                risk_score=plan.risk.score,
                risk_level=plan.risk.level.value,
                op_count=len(plan.ops),
                write_op_count=0,
                diff_path=None,
                html_report_path=None,
                jsonl_path=str(jsonl_path),
                chain_head_hash=chain_head,
                duration_ms=duration_ms,
            )
            raise

        for op in result.op_summaries:
            self.audit.append(
                plan_id=plan.plan_id,
                event_type="OP_EXECUTED",
                status=op.status,
                payload={"summary": op.summary},
                op_id=op.op_id,
                op_type=op.op_type,
                target_path=op.path,
            )

        jsonl_path = self.audit.jsonl_path_for(plan.plan_id)
        diff_path = result.diff_artifact.path if result.diff_artifact else None
        report = self.report.build(plan=plan, result=result, jsonl_path=jsonl_path, diff_path=diff_path)

        chain_head = self.audit.last_hash_for(plan.plan_id)
        self.store.insert_audit_summary(
            plan_id=plan.plan_id,
            final_status=result.status,
            risk_score=plan.risk.score,
            risk_level=plan.risk.level.value,
            op_count=len(plan.ops),
            write_op_count=result.write_op_count,
            diff_path=str(diff_path) if diff_path else None,
            html_report_path=str(report.path),
            jsonl_path=str(jsonl_path),
            chain_head_hash=chain_head,
            duration_ms=result.duration_ms,
        )
        return result, report, jsonl_path

    def reject_plan(self, plan_id: str, user_id: int) -> str:
        self._enforce_allowlist(user_id)
        self._enforce_plan_owner(plan_id=plan_id, user_id=user_id)
        out = self.approval.reject(plan_id)
        self.audit.append(
            plan_id=plan_id,
            event_type="REJECTED",
            status=out.status,
            payload={"rejected_by": user_id},
        )
        return out.status

    def get_status(self, plan_id: str, user_id: int) -> str:
        self._enforce_allowlist(user_id)
        self._check_rate(user_id, "command")
        self._enforce_plan_owner(plan_id=plan_id, user_id=user_id)
        return self.approval.get_status(plan_id)

    def get_logs(self, plan_id: str, user_id: int) -> LogsView:
        self._enforce_allowlist(user_id)
        self._check_rate(user_id, "command")
        self._enforce_plan_owner(plan_id=plan_id, user_id=user_id)

        row = self.store.get_audit_summary(plan_id)
        if row is None:
            plan_row = self.store.get_plan(plan_id)
            if plan_row is None:
                raise ApprovalError("plan not found")
            if plan_row.status not in {"FAILED", "EXECUTED"}:
                raise ApprovalError("audit summary not found")

            jsonl_path = self.audit.jsonl_path_for(plan_id)
            if not jsonl_path.exists():
                raise ApprovalError("audit summary not found")

            return LogsView(
                plan_id=plan_id,
                final_status=plan_row.status,
                diff_path="(no diff artifact)",
                html_report_path="(not generated)",
                jsonl_path=str(jsonl_path),
            )

        diff_path = row["diff_path"] or "(no write ops)"
        html_report_path = row["html_report_path"] or "(not generated)"
        return LogsView(
            plan_id=row["plan_id"],
            final_status=row["final_status"],
            diff_path=diff_path,
            html_report_path=html_report_path,
            jsonl_path=row["jsonl_path"],
        )

    def get_runtime_status(self, user_id: int) -> dict[str, str]:
        self._enforce_allowlist(user_id)
        self._check_rate(user_id, "command")
        return {
            "instance_id": self.instance_id,
            "engine_mode": self.policy.engine.mode,
            "policy_id": self.policy.version,
        }

    def list_recent_plans(self, user_id: int, limit: int = 20) -> list[PlanListItem]:
        self._enforce_allowlist(user_id)
        self._check_rate(user_id, "command")
        rows = self.store.list_plans_for_user(user_id=user_id, limit=limit)
        out: list[PlanListItem] = []
        for row in rows:
            out.append(
                PlanListItem(
                    plan_id=str(row["plan_id"]),
                    short_token=str(row["short_token"]),
                    status=str(row["status"]),
                    risk_level=str(row["risk_level"]),
                    risk_score=int(row["risk_score"]),
                    created_at=str(row["created_at"]),
                    expires_at=str(row["expires_at"]),
                )
            )
        return out

    def list_pending_plans(self, user_id: int, limit: int = 10) -> list[PlanListItem]:
        self._enforce_allowlist(user_id)
        self._check_rate(user_id, "command")
        rows = self.store.list_plans_for_user(user_id=user_id, limit=limit, status="PENDING_APPROVAL")
        out: list[PlanListItem] = []
        for row in rows:
            out.append(
                PlanListItem(
                    plan_id=str(row["plan_id"]),
                    short_token=str(row["short_token"]),
                    status=str(row["status"]),
                    risk_level=str(row["risk_level"]),
                    risk_score=int(row["risk_score"]),
                    created_at=str(row["created_at"]),
                    expires_at=str(row["expires_at"]),
                )
            )
        return out

    def answer_chat(self, user_id: int, user_text: str) -> str:
        self._enforce_allowlist(user_id)
        self._check_rate(user_id, "command")
        answer = self.chat_client.answer(user_text=user_text)
        text = (answer or "").strip()
        if not text:
            raise RuntimeError("chat answer is empty")
        # Telegram single-message practical upper bound handling.
        return text[:3500]

    def export_plan_json(self, plan_id: str) -> str:
        plan = self.approval.get_plan(plan_id)
        return json.dumps(plan.model_dump(mode="json"), ensure_ascii=True, indent=2)
