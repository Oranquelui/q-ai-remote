"""Filesystem path guard for Q CodeAnzenn MVP."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path


class PathGuardViolation(RuntimeError):
    """Raised when a path violates policy rules."""


@dataclass(frozen=True)
class SafePath:
    rel_path: str
    abs_path: Path


def _normalize_rel(rel_path: str) -> str:
    value = rel_path.strip().replace("\\", "/")
    if not value:
        raise PathGuardViolation("empty path is not allowed")
    if value.startswith("/"):
        raise PathGuardViolation("absolute path is not allowed")
    if value.startswith("//") or value.startswith("\\\\"):
        raise PathGuardViolation("UNC path is not allowed")
    if len(value) >= 2 and value[1] == ":":
        raise PathGuardViolation("drive-letter path is not allowed")
    if value.startswith("./"):
        value = value[2:]
    if value == ".":
        return value

    parts = value.split("/")
    if any(part in ("", ".") for part in parts):
        raise PathGuardViolation("invalid path segment")
    if any(part == ".." for part in parts):
        raise PathGuardViolation("parent traversal is not allowed")
    return "/".join(parts)


def _is_windows_reparse_point(path: Path) -> bool:
    if os.name != "nt":
        return False
    try:
        st = os.lstat(path)
    except OSError:
        return False
    attrs = getattr(st, "st_file_attributes", 0)
    return bool(attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _reject_linked_segments(workspace_root: Path, rel_path: str) -> None:
    if rel_path == ".":
        return

    current = workspace_root
    for part in rel_path.split("/"):
        current = current / part
        if current.exists():
            if current.is_symlink():
                raise PathGuardViolation(f"symlink segment is blocked: {part}")
            if _is_windows_reparse_point(current):
                raise PathGuardViolation(f"junction/reparse segment is blocked: {part}")


def _ensure_within_workspace(workspace_root: Path, candidate: Path) -> None:
    root = workspace_root.resolve(strict=True)
    try:
        common = os.path.commonpath([str(root), str(candidate)])
    except ValueError as exc:
        raise PathGuardViolation("path drive mismatch") from exc
    if common != str(root):
        raise PathGuardViolation("path escapes workspace")


def _is_allowed_prefix(rel_path: str, allowed_prefixes: list[str]) -> bool:
    if rel_path == ".":
        return True

    normalized = rel_path.rstrip("/")
    for prefix in allowed_prefixes:
        p = prefix.strip().replace("\\", "/").rstrip("/")
        if not p:
            continue
        if normalized == p or normalized.startswith(p + "/"):
            return True
    return False


def _is_blocked(rel_path: str, blocked_patterns: list[str]) -> bool:
    return any(fnmatch(rel_path, pattern) for pattern in blocked_patterns)


def enforce_allowed_path(
    workspace_root: Path,
    rel_path: str,
    allowed_prefixes: list[str],
    blocked_patterns: list[str],
) -> SafePath:
    normalized = _normalize_rel(rel_path)

    if not _is_allowed_prefix(normalized, allowed_prefixes):
        raise PathGuardViolation("path is outside allowed prefixes")
    if _is_blocked(normalized, blocked_patterns):
        raise PathGuardViolation("path matches blocked pattern")

    _reject_linked_segments(workspace_root, normalized)

    candidate = (workspace_root / normalized).absolute()
    _ensure_within_workspace(workspace_root, candidate)

    return SafePath(rel_path=normalized, abs_path=candidate)
