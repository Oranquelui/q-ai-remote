"""Safe executor for approved plans."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.config.policy import PolicyConfig
from src.core.approval_service import ApprovalError, ApprovalService
from src.core.diff_service import DiffArtifact, DiffService
from src.models.plan import Plan
from src.security.path_guard import PathGuardViolation, enforce_allowed_path


class ExecutionError(RuntimeError):
    """Raised when execution fails."""


@dataclass(frozen=True)
class OpExecutionSummary:
    op_id: str
    op_type: str
    path: str
    status: str
    summary: str


@dataclass(frozen=True)
class ExecutionResult:
    plan_id: str
    status: str
    op_summaries: list[OpExecutionSummary]
    diff_artifact: Optional[DiffArtifact]
    write_op_count: int
    duration_ms: int


class Executor:
    def __init__(
        self,
        workspace_root: Path,
        policy: PolicyConfig,
        approval_service: ApprovalService,
        diff_service: DiffService,
    ) -> None:
        self._workspace_root = workspace_root.resolve()
        self._policy = policy
        self._approval = approval_service
        self._diff = diff_service

    def execute_approved_plan(self, plan: Plan) -> ExecutionResult:
        status = self._approval.get_status(plan.plan_id)
        if status != "APPROVED":
            raise ExecutionError(f"plan is not executable from status={status}")

        started = time.perf_counter()
        op_summaries: list[OpExecutionSummary] = []
        write_items: list[tuple[str, str, str]] = []

        try:
            for op in plan.ops:
                if op.type not in self._policy.allowed_ops:
                    raise ExecutionError(f"operation type blocked: {op.type}")

                safe = enforce_allowed_path(
                    workspace_root=self._workspace_root,
                    rel_path=op.path,
                    allowed_prefixes=self._policy.allowed_path_prefixes,
                    blocked_patterns=self._policy.blocked_path_patterns,
                )

                abs_path = safe.abs_path

                if op.type == "list_dir":
                    if not abs_path.exists():
                        op_summaries.append(
                            OpExecutionSummary(
                                op_id=op.op_id,
                                op_type=op.type,
                                path=op.path,
                                status="SKIPPED",
                                summary="target_missing",
                            )
                        )
                        continue
                    if not abs_path.is_dir():
                        raise ExecutionError(f"list_dir target is not directory: {op.path}")
                    names = sorted([p.name for p in abs_path.iterdir()])
                    preview = ", ".join(names[:10])
                    op_summaries.append(
                        OpExecutionSummary(
                            op_id=op.op_id,
                            op_type=op.type,
                            path=op.path,
                            status="OK",
                            summary=f"entries={len(names)} preview=[{preview}]",
                        )
                    )
                    continue

                if op.type == "read_file":
                    if not abs_path.exists() or not abs_path.is_file():
                        raise ExecutionError(f"read_file target not found: {op.path}")
                    text = abs_path.read_text(encoding="utf-8")
                    op_summaries.append(
                        OpExecutionSummary(
                            op_id=op.op_id,
                            op_type=op.type,
                            path=op.path,
                            status="OK",
                            summary=f"bytes={len(text.encode('utf-8'))} lines={len(text.splitlines())}",
                        )
                    )
                    continue

                if op.type == "create_file":
                    if abs_path.exists():
                        raise ExecutionError(f"create_file target already exists: {op.path}")
                    abs_path.parent.mkdir(parents=True, exist_ok=True)
                    after_text = op.content or ""
                    abs_path.write_text(after_text, encoding="utf-8")
                    write_items.append((op.path, "", after_text))
                    op_summaries.append(
                        OpExecutionSummary(
                            op_id=op.op_id,
                            op_type=op.type,
                            path=op.path,
                            status="OK",
                            summary=f"created lines={len(after_text.splitlines())}",
                        )
                    )
                    continue

                if op.type == "patch_file":
                    if not abs_path.exists() or not abs_path.is_file():
                        raise ExecutionError(f"patch_file target not found: {op.path}")
                    before_text = abs_path.read_text(encoding="utf-8")
                    after_text = _parse_patch_to_new_content(op.patch or "")
                    abs_path.write_text(after_text, encoding="utf-8")
                    write_items.append((op.path, before_text, after_text))
                    op_summaries.append(
                        OpExecutionSummary(
                            op_id=op.op_id,
                            op_type=op.type,
                            path=op.path,
                            status="OK",
                            summary=f"patched lines_before={len(before_text.splitlines())} lines_after={len(after_text.splitlines())}",
                        )
                    )
                    continue

                raise ExecutionError(f"unsupported op type: {op.type}")

            diff_artifact = self._diff.write_patch(plan.plan_id, write_items) if write_items else None
            self._approval.mark_executed(plan.plan_id)
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ExecutionResult(
                plan_id=plan.plan_id,
                status="EXECUTED",
                op_summaries=op_summaries,
                diff_artifact=diff_artifact,
                write_op_count=len(write_items),
                duration_ms=duration_ms,
            )
        except (ExecutionError, PathGuardViolation, ApprovalError, UnicodeDecodeError) as exc:
            self._approval.mark_failed(plan.plan_id)
            raise ExecutionError(str(exc)) from exc


def _parse_patch_to_new_content(raw_patch: str) -> str:
    """MVP patch format: full-content replacement.

    Required envelope:
      <<<<QG_NEW_CONTENT
      ... new file body ...
      QG_NEW_CONTENT
    """
    header = "<<<<QG_NEW_CONTENT\n"
    footer = "\nQG_NEW_CONTENT"
    if not raw_patch.startswith(header) or not raw_patch.endswith(footer):
        raise ExecutionError("patch format invalid; expected QG_NEW_CONTENT envelope")
    return raw_patch[len(header) : -len(footer)]
