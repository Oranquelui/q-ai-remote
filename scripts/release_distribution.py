#!/usr/bin/env python3
"""Export and push distribution package to public repository in one command."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _run(argv: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        argv,
        cwd=str(cwd),
        check=False,
        text=True,
        capture_output=True,
    )
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"command failed ({' '.join(argv)}): {detail}")
    return proc


def _ensure_clean_repo(repo_root: Path, allow_dirty: bool) -> None:
    _run(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo_root, check=True)
    if allow_dirty:
        return
    status = _run(["git", "status", "--porcelain"], cwd=repo_root, check=True).stdout.strip()
    if status:
        raise RuntimeError("working tree is dirty. Commit/stash changes or use --allow-dirty")


def _remote_url(repo_root: Path, remote: str) -> str:
    return _run(["git", "remote", "get-url", remote], cwd=repo_root, check=True).stdout.strip()


def _head_short_sha(repo_root: Path) -> str:
    return _run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root, check=True).stdout.strip()


def _wipe_except_git(path: Path) -> None:
    for item in path.iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def _copy_tree(src: Path, dst: Path) -> None:
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def _export_distribution(repo_root: Path, output: str) -> Path:
    argv = [
        sys.executable,
        str(repo_root / "scripts" / "export_distribution.py"),
        "--output",
        output,
        "--force",
    ]
    _run(argv, cwd=repo_root, check=True)
    out_root = (repo_root / output).resolve()
    if not out_root.exists():
        raise RuntimeError(f"distribution output was not created: {out_root}")
    return out_root


def release_distribution(
    repo_root: Path,
    remote: str,
    branch: str,
    output: str,
    allow_dirty: bool,
    dry_run: bool,
    message: str | None,
) -> tuple[str, str]:
    _ensure_clean_repo(repo_root=repo_root, allow_dirty=allow_dirty)
    head = _head_short_sha(repo_root)
    out_root = _export_distribution(repo_root=repo_root, output=output)
    remote_url = _remote_url(repo_root=repo_root, remote=remote)

    with tempfile.TemporaryDirectory(prefix="q-ai-remote-release-") as temp:
        release_root = Path(temp).resolve()
        _run(
            ["git", "clone", "--branch", branch, "--single-branch", remote_url, str(release_root)],
            cwd=repo_root,
            check=True,
        )
        _wipe_except_git(release_root)
        _copy_tree(src=out_root, dst=release_root)

        _run(["git", "add", "-A"], cwd=release_root, check=True)
        diff = _run(["git", "diff", "--cached", "--quiet"], cwd=release_root, check=False)
        if diff.returncode == 0:
            return "NO_CHANGES", head
        if diff.returncode != 1:
            raise RuntimeError("failed to evaluate distribution diff")

        commit_message = message or f"release: sync distribution package from dev {head}"
        _run(["git", "commit", "-m", commit_message], cwd=release_root, check=True)
        released_sha = _head_short_sha(release_root)
        if not dry_run:
            _run(["git", "push", "origin", branch], cwd=release_root, check=True)
        return released_sha, head


def main() -> int:
    parser = argparse.ArgumentParser(description="Export and push distribution package to remote.")
    parser.add_argument("--remote", default="dist", help="git remote name for distribution repo (default: dist)")
    parser.add_argument("--branch", default="master", help="target branch on distribution repo (default: master)")
    parser.add_argument(
        "--output",
        default="dist/q-ai-remote-distribution",
        help="distribution export output directory (default: dist/q-ai-remote-distribution)",
    )
    parser.add_argument("--allow-dirty", action="store_true", help="allow running from dirty dev working tree")
    parser.add_argument("--dry-run", action="store_true", help="create commit locally in temp clone without push")
    parser.add_argument("--message", help="custom release commit message")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    released_sha, head = release_distribution(
        repo_root=repo_root,
        remote=args.remote,
        branch=args.branch,
        output=args.output,
        allow_dirty=bool(args.allow_dirty),
        dry_run=bool(args.dry_run),
        message=args.message,
    )

    if released_sha == "NO_CHANGES":
        print("No distribution changes. Nothing to push.")
        print(f"Dev HEAD: {head}")
        return 0

    if args.dry_run:
        print("Dry run completed. Commit created in temporary clone (not pushed).")
    else:
        print("Distribution release pushed.")
    print(f"Dev HEAD: {head}")
    print(f"Distribution commit: {released_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

