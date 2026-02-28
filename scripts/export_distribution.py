#!/usr/bin/env python3
"""Create a distribution-ready folder from this repository.

Distribution export goals:
- Exclude dev-only folders (tests/.taskmaster/data/.venv/.git/参考)
- Include only runtime-required files/directories
- Sanitize config/policy.yaml for first-time users
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Iterable

import yaml

# Minimal set for end users.
INCLUDE_FILES = [
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "SECURITY.md",
    "requirements.txt",
    ".gitignore",
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    "config/policy.yaml",
    "config/instances/.gitkeep",
    "docs/manual_beginner_ja.md",
    "docs/intro_copy_ja.md",
]
INCLUDE_DIRS = [
    "src",
    "scripts",
    "db",
    "schemas",
]

IGNORE_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".DS_Store",
    ".git",
    ".venv",
    ".taskmaster",
    "tests",
    "data",
    "参考",
}
IGNORE_FILE_SUFFIXES = {".pyc", ".pyo"}


def _ignore(_path: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        p = Path(name)
        if name in IGNORE_DIR_NAMES:
            ignored.add(name)
            continue
        if p.suffix in IGNORE_FILE_SUFFIXES:
            ignored.add(name)
    return ignored


def _copy_file(repo_root: Path, out_root: Path, rel: str) -> None:
    src = repo_root / rel
    if not src.exists():
        raise FileNotFoundError(f"required file not found: {rel}")
    dst = out_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _copy_dir(repo_root: Path, out_root: Path, rel: str) -> None:
    src = repo_root / rel
    if not src.exists() or not src.is_dir():
        raise FileNotFoundError(f"required directory not found: {rel}")
    dst = out_root / rel
    shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=True)


def _sanitize_policy(out_root: Path) -> None:
    policy_path = out_root / "config" / "policy.yaml"
    if not policy_path.exists():
        return
    payload = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("config/policy.yaml must be a YAML object")

    instance = payload.setdefault("instance", {})
    if isinstance(instance, dict):
        instance["id"] = "default"

    users = payload.setdefault("users", {})
    if isinstance(users, dict):
        users["allowlist_user_ids"] = []
        users["fail_closed_when_empty"] = True

    policy_path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _clean_output(path: Path, force: bool) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return
    if not force:
        raise FileExistsError(f"output path already exists: {path} (use --force)")
    shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def export_distribution(repo_root: Path, out_root: Path, force: bool) -> list[str]:
    _clean_output(out_root, force=force)

    copied: list[str] = []
    for rel in INCLUDE_FILES:
        _copy_file(repo_root, out_root, rel)
        copied.append(rel)
    for rel in INCLUDE_DIRS:
        _copy_dir(repo_root, out_root, rel)
        copied.append(rel + "/")

    _sanitize_policy(out_root)
    return copied


def _format_paths(paths: Iterable[str]) -> str:
    return "\n".join(f"- {p}" for p in paths)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export distribution-ready package")
    parser.add_argument(
        "--output",
        default="dist/q-ai-remote-distribution",
        help="output directory (default: dist/q-ai-remote-distribution)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite output directory if it already exists",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    out_root = (repo_root / args.output).resolve()

    copied = export_distribution(repo_root=repo_root, out_root=out_root, force=bool(args.force))
    print("Export completed.")
    print(f"Output: {out_root}")
    print("Copied:")
    print(_format_paths(copied))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
