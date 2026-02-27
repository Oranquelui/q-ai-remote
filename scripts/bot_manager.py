#!/usr/bin/env python3
"""Multi-bot process manager for Q CodeAnzenn.

Purpose:
- Manage many Telegram bot instances from one repo
- Keep each instance isolated by instance_id
- Start/stop/restart/list/status without manual PID hunting
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

import yaml

INSTANCE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
DEFAULT_INSTANCE_ID = "default"


@dataclass(frozen=True)
class BotEntry:
    instance_id: str
    enabled: bool


@dataclass(frozen=True)
class BotStatus:
    instance_id: str
    enabled: bool
    running: bool
    pid: int | None
    policy_exists: bool


class BotManagerError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_repo_root(raw: str | None) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


def _config_paths(repo_root: Path) -> tuple[Path, Path, Path, Path]:
    registry = repo_root / "config" / "bots.yaml"
    active_instance = repo_root / "config" / ".active_instance"
    default_policy = repo_root / "config" / "policy.yaml"
    instance_policy_dir = repo_root / "config" / "instances"
    return registry, active_instance, default_policy, instance_policy_dir


def _runtime_dir(repo_root: Path, instance_id: str) -> Path:
    return repo_root / "data" / "runtime" / "bots" / instance_id


def _pid_file(repo_root: Path, instance_id: str) -> Path:
    return _runtime_dir(repo_root, instance_id) / "bot.pid"


def _stdout_file(repo_root: Path, instance_id: str) -> Path:
    return _runtime_dir(repo_root, instance_id) / "stdout.log"


def _stderr_file(repo_root: Path, instance_id: str) -> Path:
    return _runtime_dir(repo_root, instance_id) / "stderr.log"


def _validate_instance_id(instance_id: str) -> str:
    value = (instance_id or "").strip()
    if not value:
        raise BotManagerError("instance_id is required")
    if not INSTANCE_ID_RE.fullmatch(value):
        raise BotManagerError(f"invalid instance_id: {value}")
    return value


def _service_name(instance_id: str) -> str:
    if instance_id == DEFAULT_INSTANCE_ID:
        return "qcodeanzenn"
    return f"qcodeanzenn.{instance_id}"


def _policy_path(repo_root: Path, instance_id: str) -> Path:
    if instance_id == DEFAULT_INSTANCE_ID:
        return repo_root / "config" / "policy.yaml"
    return repo_root / "config" / "instances" / instance_id / "policy.yaml"


def _load_registry(repo_root: Path) -> dict[str, Any]:
    registry_path, _, _, _ = _config_paths(repo_root)
    if not registry_path.exists():
        return {"version": 1, "bots": []}
    raw = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise BotManagerError("config/bots.yaml must be an object")
    version = int(raw.get("version", 1))
    bots = raw.get("bots", [])
    if not isinstance(bots, list):
        raise BotManagerError("config/bots.yaml 'bots' must be an array")
    return {"version": version, "bots": bots}


def _save_registry(repo_root: Path, data: dict[str, Any]) -> Path:
    registry_path, _, _, _ = _config_paths(repo_root)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return registry_path


def _read_active_instance(repo_root: Path) -> str:
    _, active_file, _, _ = _config_paths(repo_root)
    if not active_file.exists():
        return DEFAULT_INSTANCE_ID
    raw = active_file.read_text(encoding="utf-8").strip()
    if not raw:
        return DEFAULT_INSTANCE_ID
    try:
        return _validate_instance_id(raw)
    except BotManagerError:
        return DEFAULT_INSTANCE_ID


def _discover_instance_ids(repo_root: Path) -> list[str]:
    _, _, default_policy, instance_policy_dir = _config_paths(repo_root)
    out: list[str] = []
    if default_policy.exists():
        out.append(DEFAULT_INSTANCE_ID)
    if instance_policy_dir.exists():
        for policy_file in sorted(instance_policy_dir.glob("*/policy.yaml")):
            instance_id = policy_file.parent.name
            try:
                out.append(_validate_instance_id(instance_id))
            except BotManagerError:
                continue
    dedup = []
    seen: set[str] = set()
    for row in out:
        if row in seen:
            continue
        dedup.append(row)
        seen.add(row)
    return dedup


def _entries(repo_root: Path) -> list[BotEntry]:
    data = _load_registry(repo_root)
    rows = data.get("bots", [])
    out: list[BotEntry] = []
    seen: set[str] = set()

    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            instance_id = _validate_instance_id(str(row.get("instance_id", "")))
        except BotManagerError:
            continue
        if instance_id in seen:
            continue
        enabled = bool(row.get("enabled", True))
        out.append(BotEntry(instance_id=instance_id, enabled=enabled))
        seen.add(instance_id)

    for instance_id in _discover_instance_ids(repo_root):
        if instance_id in seen:
            continue
        out.append(BotEntry(instance_id=instance_id, enabled=True))
        seen.add(instance_id)

    return sorted(out, key=lambda x: x.instance_id)


def _upsert_registry_entry(repo_root: Path, instance_id: str, enabled: bool = True) -> Path:
    data = _load_registry(repo_root)
    bots = data.setdefault("bots", [])
    if not isinstance(bots, list):
        raise BotManagerError("config/bots.yaml 'bots' must be an array")

    now = _utc_now()
    updated = False
    for row in bots:
        if not isinstance(row, dict):
            continue
        if str(row.get("instance_id", "")) == instance_id:
            row["enabled"] = bool(enabled)
            row["updated_at"] = now
            updated = True
            break

    if not updated:
        bots.append(
            {
                "instance_id": instance_id,
                "enabled": bool(enabled),
                "service_name": _service_name(instance_id),
                "policy_path": str(_policy_path(repo_root, instance_id).relative_to(repo_root)),
                "created_at": now,
                "updated_at": now,
            }
        )

    return _save_registry(repo_root, data)


def _read_pid(repo_root: Path, instance_id: str) -> int | None:
    path = _pid_file(repo_root, instance_id)
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    try:
        pid = int(raw)
    except ValueError:
        return None
    if pid <= 0:
        return None
    return pid


def _is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _status_for(repo_root: Path, entry: BotEntry) -> BotStatus:
    pid = _read_pid(repo_root, entry.instance_id)
    running = bool(pid and _is_pid_running(pid))
    if pid and not running:
        try:
            _pid_file(repo_root, entry.instance_id).unlink(missing_ok=True)
        except OSError:
            pass
        pid = None
    return BotStatus(
        instance_id=entry.instance_id,
        enabled=entry.enabled,
        running=running,
        pid=pid,
        policy_exists=_policy_path(repo_root, entry.instance_id).exists(),
    )


def _select_targets(repo_root: Path, instance_id: str | None, all_flag: bool) -> list[BotEntry]:
    entries = _entries(repo_root)
    if instance_id:
        target = _validate_instance_id(instance_id)
        for row in entries:
            if row.instance_id == target:
                return [row]
        return [BotEntry(instance_id=target, enabled=True)]

    if all_flag:
        return [x for x in entries if x.enabled]

    active = _read_active_instance(repo_root)
    for row in entries:
        if row.instance_id == active:
            return [row]
    return [BotEntry(instance_id=active, enabled=True)]


def _default_python_bin(repo_root: Path) -> str:
    venv_py = repo_root / ".venv" / "bin" / "python"
    if venv_py.exists():
        return str(venv_py)
    return sys.executable or "python3"


def _start_instance(repo_root: Path, instance_id: str, python_bin: str, restart: bool) -> str:
    entry = BotEntry(instance_id=instance_id, enabled=True)
    status = _status_for(repo_root, entry)
    if status.running:
        if not restart:
            return f"{instance_id}: already running pid={status.pid}"
        _stop_instance(repo_root, instance_id)

    run_dir = _runtime_dir(repo_root, instance_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    stdout_path = _stdout_file(repo_root, instance_id)
    stderr_path = _stderr_file(repo_root, instance_id)
    stdout_f = stdout_path.open("a", encoding="utf-8")
    stderr_f = stderr_path.open("a", encoding="utf-8")
    cmd = [python_bin, "-m", "src.main", "--instance-id", instance_id]
    proc = subprocess.Popen(
        cmd,
        cwd=str(repo_root),
        stdout=stdout_f,
        stderr=stderr_f,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    stdout_f.close()
    stderr_f.close()

    # Detect immediate startup failure (e.g. missing secret / invalid policy).
    deadline = time.time() + 1.5
    while time.time() < deadline:
        rc = proc.poll()
        if rc is not None:
            _pid_file(repo_root, instance_id).unlink(missing_ok=True)
            detail = _tail_text(stderr_path, 300) or _tail_text(stdout_path, 300)
            if detail:
                return f"{instance_id}: start failed rc={rc} ({detail})"
            return f"{instance_id}: start failed rc={rc}"
        time.sleep(0.1)

    _pid_file(repo_root, instance_id).write_text(str(proc.pid) + "\n", encoding="utf-8")
    _upsert_registry_entry(repo_root, instance_id=instance_id, enabled=True)
    return f"{instance_id}: started pid={proc.pid}"


def _tail_text(path: Path, limit: int = 300) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if text:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if lines:
            last = lines[-1]
            if len(last) <= limit:
                return last
            return last[-limit:]
    if len(text) <= limit:
        return text
    return text[-limit:]


def _stop_instance(repo_root: Path, instance_id: str, timeout_sec: float = 5.0) -> str:
    pid = _read_pid(repo_root, instance_id)
    if not pid:
        return f"{instance_id}: not running"
    if not _is_pid_running(pid):
        _pid_file(repo_root, instance_id).unlink(missing_ok=True)
        return f"{instance_id}: stale pid removed"

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        _pid_file(repo_root, instance_id).unlink(missing_ok=True)
        return f"{instance_id}: already stopped"

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if not _is_pid_running(pid):
            _pid_file(repo_root, instance_id).unlink(missing_ok=True)
            return f"{instance_id}: stopped"
        time.sleep(0.1)

    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass
    _pid_file(repo_root, instance_id).unlink(missing_ok=True)
    return f"{instance_id}: killed"


def cmd_register(args: argparse.Namespace) -> int:
    repo_root = _resolve_repo_root(args.repo_root)
    instance_id = _validate_instance_id(args.instance_id)
    path = _upsert_registry_entry(repo_root, instance_id=instance_id, enabled=not args.disabled)
    state = "disabled" if args.disabled else "enabled"
    print(f"registered: {instance_id} ({state}) -> {path}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    repo_root = _resolve_repo_root(args.repo_root)
    entries = _entries(repo_root)
    if not entries:
        print("no bot instances found")
        return 0

    print("instance_id\tenabled\trunning\tpid\tpolicy")
    for row in entries:
        st = _status_for(repo_root, row)
        pid_txt = str(st.pid) if st.pid else "-"
        print(f"{st.instance_id}\t{st.enabled}\t{st.running}\t{pid_txt}\t{st.policy_exists}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    repo_root = _resolve_repo_root(args.repo_root)
    targets = _select_targets(repo_root, instance_id=args.instance_id, all_flag=args.all)
    print("instance_id\tenabled\trunning\tpid\tpolicy")
    for row in targets:
        st = _status_for(repo_root, row)
        pid_txt = str(st.pid) if st.pid else "-"
        print(f"{st.instance_id}\t{st.enabled}\t{st.running}\t{pid_txt}\t{st.policy_exists}")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    repo_root = _resolve_repo_root(args.repo_root)
    targets = _select_targets(repo_root, instance_id=args.instance_id, all_flag=args.all)
    python_bin = args.python_bin or _default_python_bin(repo_root)

    if args.foreground:
        if len(targets) != 1:
            raise BotManagerError("--foreground requires a single target instance")
        target = targets[0].instance_id
        cmd = [python_bin, "-m", "src.main", "--instance-id", target]
        print(f"foreground start: {target}")
        return subprocess.call(cmd, cwd=str(repo_root))

    failed = 0
    for row in targets:
        line = _start_instance(repo_root, row.instance_id, python_bin=python_bin, restart=args.restart)
        print(line)
        if "start failed" in line:
            failed += 1
    return 1 if failed else 0


def cmd_stop(args: argparse.Namespace) -> int:
    repo_root = _resolve_repo_root(args.repo_root)
    targets = _select_targets(repo_root, instance_id=args.instance_id, all_flag=args.all)
    for row in targets:
        print(_stop_instance(repo_root, row.instance_id))
    return 0


def cmd_enable(args: argparse.Namespace) -> int:
    repo_root = _resolve_repo_root(args.repo_root)
    instance_id = _validate_instance_id(args.instance_id)
    path = _upsert_registry_entry(repo_root, instance_id=instance_id, enabled=True)
    print(f"enabled: {instance_id} -> {path}")
    return 0


def cmd_disable(args: argparse.Namespace) -> int:
    repo_root = _resolve_repo_root(args.repo_root)
    instance_id = _validate_instance_id(args.instance_id)
    path = _upsert_registry_entry(repo_root, instance_id=instance_id, enabled=False)
    print(f"disabled: {instance_id} -> {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Q CodeAnzenn multi-bot manager")
    parser.add_argument("--repo-root", help="override repository root (for testing/debug)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("register", help="register a bot instance in config/bots.yaml")
    p.add_argument("--instance-id", required=True)
    p.add_argument("--disabled", action="store_true")
    p.set_defaults(func=cmd_register)

    p = sub.add_parser("enable", help="mark instance enabled in registry")
    p.add_argument("--instance-id", required=True)
    p.set_defaults(func=cmd_enable)

    p = sub.add_parser("disable", help="mark instance disabled in registry")
    p.add_argument("--instance-id", required=True)
    p.set_defaults(func=cmd_disable)

    p = sub.add_parser("list", help="list known instances and runtime state")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("status", help="show status for one or many instances")
    p.add_argument("--instance-id")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("start", help="start one or many bot instances")
    p.add_argument("--instance-id")
    p.add_argument("--all", action="store_true")
    p.add_argument("--restart", action="store_true")
    p.add_argument("--foreground", action="store_true")
    p.add_argument("--python-bin")
    p.set_defaults(func=cmd_start)

    p = sub.add_parser("restart", help="restart one or many bot instances")
    p.add_argument("--instance-id")
    p.add_argument("--all", action="store_true")
    p.add_argument("--python-bin")
    p.set_defaults(func=lambda a: cmd_start(argparse.Namespace(**{**vars(a), "restart": True, "foreground": False})))

    p = sub.add_parser("stop", help="stop one or many bot instances")
    p.add_argument("--instance-id")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_stop)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except BotManagerError as exc:
        print(f"error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
