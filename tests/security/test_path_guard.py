from pathlib import Path

import pytest

from src.security.path_guard import PathGuardViolation, enforce_allowed_path


def test_reject_parent_traversal(tmp_path: Path) -> None:
    with pytest.raises(PathGuardViolation):
        enforce_allowed_path(tmp_path, "../etc/passwd", ["docs/"], [])


def test_allow_valid_prefix(tmp_path: Path) -> None:
    out = enforce_allowed_path(tmp_path, "docs/readme.md", ["docs/"], [])
    assert out.rel_path == "docs/readme.md"
