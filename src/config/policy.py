"""Policy loader for Q CodeAnzenn MVP."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml


@dataclass(frozen=True)
class RateLimitConfig:
    command_per_minute: int
    plan_per_minute: int
    approve_per_minute: int


@dataclass(frozen=True)
class PlanPolicyConfig:
    ttl_minutes: int
    short_token_length: int


@dataclass(frozen=True)
class RiskScoringConfig:
    list_dir: int
    read_file: int
    create_file: int
    patch_file: int
    per_20_changed_lines: int
    per_extra_file: int


@dataclass(frozen=True)
class StorageConfig:
    sqlite: str
    plans_dir: str
    audit_jsonl_dir: str
    audit_diff_dir: str
    audit_html_dir: str


@dataclass(frozen=True)
class UiConfig:
    language: str


@dataclass(frozen=True)
class InstanceConfig:
    id: str


@dataclass(frozen=True)
class EngineCliConfig:
    command: str
    model: str


@dataclass(frozen=True)
class EngineConfig:
    mode: str
    timeout_seconds: int
    codex_api_model: str
    codex_cli: EngineCliConfig
    claude_cli: EngineCliConfig


@dataclass(frozen=True)
class PolicyConfig:
    version: str
    commands: list[str]
    allowed_ops: list[str]
    prohibited_ops: list[str]
    allowed_path_prefixes: list[str]
    blocked_path_patterns: list[str]
    allowlist_user_ids: list[int]
    fail_closed_when_empty: bool
    rate_limit: RateLimitConfig
    plan: PlanPolicyConfig
    risk_block_levels: list[str]
    risk_scoring: RiskScoringConfig
    storage: StorageConfig
    engine: EngineConfig
    ui: UiConfig
    instance: InstanceConfig


class PolicyLoadError(RuntimeError):
    """Raised when policy cannot be loaded."""


def _require(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise PolicyLoadError(f"missing required policy key: {key}")
    return data[key]


def load_policy(path: Path) -> PolicyConfig:
    if not path.exists():
        raise PolicyLoadError(f"policy file not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise PolicyLoadError("policy root must be an object")

    commands = list(_require(raw["telegram"], "commands"))
    allowed_ops = list(_require(raw["executor"], "allowed_ops"))
    prohibited_ops = list(_require(raw["executor"], "prohibit"))

    plan_raw = raw["plan"]
    short_token = plan_raw.get("short_token", {})

    risk_raw = raw["risk"]
    scoring = risk_raw["scoring"]

    rate_raw = raw["rate_limit"]
    storage_raw = raw["storage"]
    users_raw = raw["users"]
    engine_raw = raw.get("engine", {})
    ui_raw = raw.get("ui", {})
    instance_raw = raw.get("instance", {})
    if not isinstance(engine_raw, dict):
        raise PolicyLoadError("engine must be an object")
    if not isinstance(ui_raw, dict):
        raise PolicyLoadError("ui must be an object")
    if not isinstance(instance_raw, dict):
        raise PolicyLoadError("instance must be an object")

    mode = str(engine_raw.get("mode", "codex_api")).strip()
    if mode not in {"codex_api", "codex_subscription", "claude_subscription"}:
        raise PolicyLoadError(f"invalid engine.mode: {mode}")

    timeout_seconds = int(engine_raw.get("timeout_seconds", 120))
    if timeout_seconds <= 0:
        raise PolicyLoadError("engine.timeout_seconds must be > 0")

    codex_api_model = str(engine_raw.get("codex_api_model", "gpt-5-codex")).strip()
    if not codex_api_model:
        raise PolicyLoadError("engine.codex_api_model must not be empty")

    codex_cli_raw = engine_raw.get("codex_cli", {})
    claude_cli_raw = engine_raw.get("claude_cli", {})
    if not isinstance(codex_cli_raw, dict):
        raise PolicyLoadError("engine.codex_cli must be an object")
    if not isinstance(claude_cli_raw, dict):
        raise PolicyLoadError("engine.claude_cli must be an object")

    codex_command = str(codex_cli_raw.get("command", "codex")).strip()
    claude_command = str(claude_cli_raw.get("command", "claude")).strip()
    if not codex_command:
        raise PolicyLoadError("engine.codex_cli.command must not be empty")
    if not claude_command:
        raise PolicyLoadError("engine.claude_cli.command must not be empty")

    # Keep planner transport fixed to known commands (no arbitrary executor-style command path).
    if mode == "codex_subscription" and "codex" not in Path(codex_command).name.lower():
        raise PolicyLoadError("engine.codex_cli.command must point to codex CLI")
    if mode == "claude_subscription" and "claude" not in Path(claude_command).name.lower():
        raise PolicyLoadError("engine.claude_cli.command must point to claude CLI")

    ui_language = str(ui_raw.get("language", "ja")).strip().lower()
    if ui_language not in {"ja", "en"}:
        raise PolicyLoadError(f"invalid ui.language: {ui_language}")

    instance_id = str(instance_raw.get("id", "default")).strip()
    if not instance_id:
        raise PolicyLoadError("instance.id must not be empty")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", instance_id):
        raise PolicyLoadError(f"invalid instance.id: {instance_id}")

    return PolicyConfig(
        version=str(_require(raw, "version")),
        commands=commands,
        allowed_ops=allowed_ops,
        prohibited_ops=prohibited_ops,
        allowed_path_prefixes=list(_require(raw, "allowed_path_prefixes")),
        blocked_path_patterns=list(_require(raw, "blocked_path_patterns")),
        allowlist_user_ids=[int(x) for x in users_raw.get("allowlist_user_ids", [])],
        fail_closed_when_empty=bool(users_raw.get("fail_closed_when_empty", True)),
        rate_limit=RateLimitConfig(
            command_per_minute=int(rate_raw["command_per_minute"]),
            plan_per_minute=int(rate_raw["plan_per_minute"]),
            approve_per_minute=int(rate_raw["approve_per_minute"]),
        ),
        plan=PlanPolicyConfig(
            ttl_minutes=int(plan_raw["ttl_minutes"]),
            short_token_length=int(short_token.get("length", 8)),
        ),
        risk_block_levels=list(risk_raw.get("block_levels", ["HIGH", "CRITICAL"])),
        risk_scoring=RiskScoringConfig(
            list_dir=int(scoring["list_dir"]),
            read_file=int(scoring["read_file"]),
            create_file=int(scoring["create_file"]),
            patch_file=int(scoring["patch_file"]),
            per_20_changed_lines=int(scoring["per_20_changed_lines"]),
            per_extra_file=int(scoring["per_extra_file"]),
        ),
        storage=StorageConfig(
            sqlite=str(storage_raw["sqlite"]),
            plans_dir=str(storage_raw["plans_dir"]),
            audit_jsonl_dir=str(storage_raw["audit_jsonl_dir"]),
            audit_diff_dir=str(storage_raw["audit_diff_dir"]),
            audit_html_dir=str(storage_raw["audit_html_dir"]),
        ),
        engine=EngineConfig(
            mode=mode,
            timeout_seconds=timeout_seconds,
            codex_api_model=codex_api_model,
            codex_cli=EngineCliConfig(
                command=codex_command,
                model=str(codex_cli_raw.get("model", "gpt-5.3-codex")).strip() or "gpt-5.3-codex",
            ),
            claude_cli=EngineCliConfig(
                command=claude_command,
                model=str(claude_cli_raw.get("model", "sonnet")).strip() or "sonnet",
            ),
        ),
        ui=UiConfig(language=ui_language),
        instance=InstanceConfig(id=instance_id),
    )


def ensure_storage_dirs(root: Path, storage: StorageConfig) -> None:
    for rel in [storage.plans_dir, storage.audit_jsonl_dir, storage.audit_diff_dir, storage.audit_html_dir]:
        (root / rel).mkdir(parents=True, exist_ok=True)
    (root / Path(storage.sqlite).parent).mkdir(parents=True, exist_ok=True)
