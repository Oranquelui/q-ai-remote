"""Diff generation service."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileDiff:
    rel_path: str
    before_sha256: str
    after_sha256: str
    changed_lines: int


@dataclass(frozen=True)
class DiffArtifact:
    path: Path
    summary: list[FileDiff]


def _sha256_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class DiffService:
    def __init__(self, out_dir: Path) -> None:
        self._out_dir = out_dir
        self._out_dir.mkdir(parents=True, exist_ok=True)

    def write_patch(
        self,
        plan_id: str,
        items: list[tuple[str, str, str]],
    ) -> DiffArtifact:
        """Create unified diff patch.

        Args:
            items: list of (rel_path, before_text, after_text)
        """
        patch_lines: list[str] = []
        summary: list[FileDiff] = []

        for rel_path, before_text, after_text in items:
            before_lines = before_text.splitlines(keepends=True)
            after_lines = after_text.splitlines(keepends=True)
            file_patch = list(
                difflib.unified_diff(
                    before_lines,
                    after_lines,
                    fromfile=f"a/{rel_path}",
                    tofile=f"b/{rel_path}",
                    lineterm="",
                )
            )
            patch_lines.extend(file_patch)
            changed = sum(
                1
                for line in file_patch
                if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
            )
            summary.append(
                FileDiff(
                    rel_path=rel_path,
                    before_sha256=_sha256_text(before_text),
                    after_sha256=_sha256_text(after_text),
                    changed_lines=changed,
                )
            )

        patch_path = self._out_dir / f"{plan_id}.patch"
        patch_path.write_text("\n".join(patch_lines) + ("\n" if patch_lines else ""), encoding="utf-8")
        return DiffArtifact(path=patch_path, summary=summary)
