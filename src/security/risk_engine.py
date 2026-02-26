"""Risk scoring engine for plans."""

from __future__ import annotations

from dataclasses import dataclass

from src.config.policy import PolicyConfig
from src.models.plan import PlanOp, RiskLevel, RiskReport


@dataclass(frozen=True)
class RiskOutcome:
    score: int
    level: RiskLevel
    reasons: list[str]
    blocked: bool


class RiskEngine:
    def __init__(self, policy: PolicyConfig) -> None:
        self._policy = policy

    def evaluate_ops(self, ops: list[PlanOp]) -> RiskOutcome:
        scoring = self._policy.risk_scoring
        reasons: list[str] = []
        score = 0

        per_op = {
            "list_dir": scoring.list_dir,
            "read_file": scoring.read_file,
            "create_file": scoring.create_file,
            "patch_file": scoring.patch_file,
        }

        touched: set[str] = set()
        for op in ops:
            op_score = per_op.get(op.type, 100)
            score += op_score
            reasons.append(f"{op.type} +{op_score}")
            touched.add(op.path)

            if op.type == "patch_file" and op.patch:
                changed_lines = sum(1 for line in op.patch.splitlines() if line.startswith(("+", "-")))
                lines_score = min(20, (changed_lines // 20) * scoring.per_20_changed_lines)
                if lines_score:
                    score += lines_score
                    reasons.append(f"changed_lines({changed_lines}) +{lines_score}")
            elif op.type == "create_file" and op.content:
                line_count = max(1, len(op.content.splitlines()))
                lines_score = min(20, (line_count // 20) * scoring.per_20_changed_lines)
                if lines_score:
                    score += lines_score
                    reasons.append(f"new_lines({line_count}) +{lines_score}")

        if len(touched) > 1:
            extra_files_score = min(18, (len(touched) - 1) * scoring.per_extra_file)
            score += extra_files_score
            reasons.append(f"multi_file({len(touched)}) +{extra_files_score}")

        score = min(100, score)
        level = self._to_level(score)
        blocked = level.value in set(self._policy.risk_block_levels)

        return RiskOutcome(score=score, level=level, reasons=reasons, blocked=blocked)

    @staticmethod
    def _to_level(score: int) -> RiskLevel:
        if score >= 80:
            return RiskLevel.CRITICAL
        if score >= 60:
            return RiskLevel.HIGH
        if score >= 30:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


def to_report(outcome: RiskOutcome) -> RiskReport:
    return RiskReport(
        score=outcome.score,
        level=outcome.level,
        reasons=outcome.reasons,
        blocked=outcome.blocked,
    )
