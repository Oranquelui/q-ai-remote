"""Async run-state contract for background job orchestration.

This module intentionally introduces the lifecycle contract before any queue or
worker implementation. The current runtime remains synchronous, but future
background runners should use these statuses and transition guards.
"""

from __future__ import annotations

from enum import Enum


class RunTransitionError(RuntimeError):
    """Raised when a run state transition is invalid."""


class RunStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_INPUT = "WAITING_INPUT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @property
    def is_terminal(self) -> bool:
        return self in TERMINAL_RUN_STATUSES


TERMINAL_RUN_STATUSES = {
    RunStatus.COMPLETED,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
}

_ALLOWED_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.QUEUED: {RunStatus.RUNNING, RunStatus.CANCELLED},
    RunStatus.RUNNING: {
        RunStatus.WAITING_INPUT,
        RunStatus.COMPLETED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.WAITING_INPUT: {RunStatus.RUNNING, RunStatus.CANCELLED},
    RunStatus.COMPLETED: set(),
    RunStatus.FAILED: set(),
    RunStatus.CANCELLED: set(),
}


def allowed_next_statuses(current: RunStatus) -> set[RunStatus]:
    """Return the valid next states for the current run status."""

    return set(_ALLOWED_TRANSITIONS[current])


def validate_run_transition(current: RunStatus, new: RunStatus) -> None:
    """Validate a run status transition or raise a descriptive error."""

    if new not in _ALLOWED_TRANSITIONS[current]:
        raise RunTransitionError(f"invalid run status transition: {current.value} -> {new.value}")
