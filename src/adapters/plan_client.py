"""Shared planner client interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DraftPlan:
    ops: list[dict]
    summary: str


class PlanDraftClient(Protocol):
    def draft_plan(
        self,
        request_text: str,
        allowed_ops: list[str],
        allowed_prefixes: list[str],
    ) -> DraftPlan:
        """Create a safe draft plan from natural-language request."""

