#!/usr/bin/env python3
"""Desktop first-run setup for Q CodeAnzenn.

Purpose:
- Select engine mode in config/policy.yaml
- Set allowlist Telegram user id
- Store required secrets in OS credential store
- Verify subscription CLI login status
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import yaml

BASE_SERVICE_NAME = "qcodeanzenn"
POLICY_PATH = Path("config/policy.yaml")
INSTANCE_POLICY_DIR = Path("config/instances")
ACTIVE_INSTANCE_FILE = Path("config/.active_instance")
DEFAULT_INSTANCE_ID = "default"
ALLOWED_MODES = ["codex_subscription", "claude_subscription", "codex_api"]
LANG_CHOICES = ("ja", "en")
MODE_LABELS = {
    "ja": {
        "codex_subscription": "Codexサブスク (codex login)",
        "claude_subscription": "Claudeサブスク (claude auth)",
        "codex_api": "Codex APIキー モード",
    },
    "en": {
        "codex_subscription": "Codex subscription (codex login)",
        "claude_subscription": "Claude subscription (claude auth)",
        "codex_api": "Codex API key mode",
    },
}

TEXTS = {
    "ja": {
        "wizard_title": "Q CodeAnzenn セットアップ",
        "repo": "- リポジトリ: {repo}",
        "policy": "- ポリシー: {policy}",
        "instance_id": "- インスタンス: {instance_id}",
        "secret_service": "- secrets service: {service_name}",
        "setup_mode_header": "\nセットアップ種別を選択してください:",
        "setup_mode_first": "  1) 初回セットアップ（default を使用）",
        "setup_mode_add": "  2) 既存環境にBot追加（別 instance_id 推奨）",
        "setup_mode_prompt": "種別 [1/2] (default: {default}): ",
        "setup_mode_invalid": "1 または 2 を入力してください。",
        "current_mode": "- 現在の mode: {mode}",
        "current_allowlist": "- 現在の allowlist: {allowlist}",
        "instance_prompt": "instance_id [{current}] (英数/_/-): ",
        "instance_invalid": "instance_id は英数/_/- のみ、1-40文字で入力してください。",
        "instance_new_policy_seeded": "- 新規インスタンス用 policy を作成しました: {path}",
        "select_mode_header": "\nEngine mode を選択してください:",
        "mode_prompt": "Mode [{current}]: ",
        "mode_invalid": "不正な入力です。1-3 か mode 名を入力してください。",
        "user_id_prompt": "allowlist に入れる Telegram user id [{default}]: ",
        "auto_user_id_prompt": "allowlist 用 user id を自動取得しますか？",
        "auto_user_id_wait": "  Telegramで @{username} に /start を送ってください（最大{seconds}秒待機）",
        "auto_user_id_detected": "  自動取得 user id: {user_id}",
        "auto_user_id_failed": "  user id の自動取得に失敗しました。手動入力に切り替えます。",
        "auto_user_id_skipped": "  user id の自動取得をスキップしました。",
        "invalid_integer": "数値を入力してください。",
        "user_id_positive": "user id は正の整数で入力してください。",
        "yes_no_invalid": "y か n を入力してください。",
        "missing_policy": "policy ファイルが見つかりません: {path}",
        "invalid_policy_obj": "policy ファイルは YAML オブジェクトである必要があります",
        "keyring_required": "keyring が必要です。先に依存パッケージをインストールしてください。",
        "telegram_token_note": "- Telegram Botトークン（BotFather発行）は必須です",
        "telegram_existing_bot": "- 現在の telegram_bot_token: @{username} (id={bot_id})",
        "telegram_verified_bot": "- 入力トークン確認OK: @{username} (id={bot_id})",
        "telegram_verify_failed": "- telegram_bot_token の確認に失敗: {reason}",
        "replace_secret": "{account} は既に保存済みです。上書きしますか？",
        "keeping_secret": "- {account} は既存値をそのまま使います",
        "enter_secret": "{label} を入力してください: ",
        "stored_secret": "- {account} をOS資格情報ストアに保存しました",
        "secret_required": "{account} は必須です。値を入力してください。",
        "secret_skipped": "- {account} の入力をスキップしました",
        "secrets_header": "\nSecrets 設定:",
        "api_key_optional": "- サブスク mode では codex_api_key は任意です",
        "prereq_header": "\nEngine 事前チェック:",
        "codex_ok": "- codex login status: OK",
        "codex_ng": "- codex login status: 未完了",
        "codex_detail": "  認証詳細: {detail}",
        "codex_hint": "  実行: codex login",
        "claude_ok": "- claude auth status: OK",
        "claude_ng": "- claude auth status: 未完了",
        "claude_detail": "  認証詳細: method={method}, email={email}, plan={plan}",
        "claude_hint": "  実行: claude auth login",
        "run_login_now": "  今すぐログインを実行しますか？",
        "login_done_recheck": "  ログイン完了。再確認します。",
        "login_failed": "  ログイン実行に失敗しました (code={code})",
        "manual_check_hint": "  手動確認: {command}",
        "api_note": "- codex_api mode を選択中（codex_api_key が必要）",
        "policy_updated": "\nPolicy を更新しました:",
        "updated_mode": "- mode: {mode}",
        "updated_allowlist": "- allowlist_user_ids: {allowlist}",
        "updated_backup": "- バックアップ: {backup}",
        "updated_instance": "- instance.id: {instance_id}",
        "updated_storage_root": "- storage root: {root}",
        "active_instance_written": "- active instance を更新: {path}",
        "next_header": "\n次の操作:",
        "next_start_1": "1) Bot起動:",
        "next_start_2": "   ./.venv/bin/python -m src.main --instance-id {instance_id}   (macOS/Linux)",
        "next_start_3": "   .\\.venv\\Scripts\\python.exe -m src.main --instance-id {instance_id}   (Windows)",
        "next_flow": "2) Telegram: /start -> /policy -> /plan ... -> /approve ... ... -> /logs ...",
        "next_bot_target": "3) Telegramで開くBot: @{username}",
        "non_interactive_requires": "--non-interactive では --mode と --user-id が必須です",
    },
    "en": {
        "wizard_title": "Q CodeAnzenn setup wizard",
        "repo": "- repo: {repo}",
        "policy": "- policy: {policy}",
        "instance_id": "- instance: {instance_id}",
        "secret_service": "- secrets service: {service_name}",
        "setup_mode_header": "\nChoose setup type:",
        "setup_mode_first": "  1) First setup (use default instance)",
        "setup_mode_add": "  2) Add another bot (separate instance_id recommended)",
        "setup_mode_prompt": "Type [1/2] (default: {default}): ",
        "setup_mode_invalid": "Enter 1 or 2.",
        "current_mode": "- current mode: {mode}",
        "current_allowlist": "- current allowlist: {allowlist}",
        "instance_prompt": "instance_id [{current}] (alnum/_/-): ",
        "instance_invalid": "instance_id must match [A-Za-z0-9_-]{1,40}",
        "instance_new_policy_seeded": "- Seeded new instance policy: {path}",
        "select_mode_header": "\nSelect engine mode:",
        "mode_prompt": "Mode [{current}]: ",
        "mode_invalid": "Invalid mode. Choose 1-3 or a mode name.",
        "user_id_prompt": "Telegram user id for allowlist [{default}]: ",
        "auto_user_id_prompt": "Auto-detect Telegram user id for allowlist now?",
        "auto_user_id_wait": "  Send /start to @{username} in Telegram (waiting up to {seconds}s)",
        "auto_user_id_detected": "  Auto-detected user id: {user_id}",
        "auto_user_id_failed": "  Failed to auto-detect user id. Switching to manual input.",
        "auto_user_id_skipped": "  Skipped auto-detect for user id.",
        "invalid_integer": "Invalid integer. Try again.",
        "user_id_positive": "User id must be positive.",
        "yes_no_invalid": "Please answer y or n.",
        "missing_policy": "policy file not found: {path}",
        "invalid_policy_obj": "policy file must contain a YAML object",
        "keyring_required": "keyring is required. Install dependencies first.",
        "telegram_token_note": "- Telegram bot token from BotFather is required",
        "telegram_existing_bot": "- Current telegram_bot_token: @{username} (id={bot_id})",
        "telegram_verified_bot": "- Token verified: @{username} (id={bot_id})",
        "telegram_verify_failed": "- Failed to verify telegram_bot_token: {reason}",
        "replace_secret": "{account} already exists. Replace?",
        "keeping_secret": "- Keeping existing {account}",
        "enter_secret": "Enter {label}: ",
        "stored_secret": "- Stored {account} in OS credential store",
        "secret_required": "{account} is required. Please enter a value.",
        "secret_skipped": "- Skipped {account}",
        "secrets_header": "\nSecrets setup:",
        "api_key_optional": "- codex_api_key is optional in subscription mode",
        "prereq_header": "\nEngine prerequisite check:",
        "codex_ok": "- codex login status: OK",
        "codex_ng": "- codex login status: NOT READY",
        "codex_detail": "  auth detail: {detail}",
        "codex_hint": "  Run: codex login",
        "claude_ok": "- claude auth status: OK",
        "claude_ng": "- claude auth status: NOT READY",
        "claude_detail": "  auth detail: method={method}, email={email}, plan={plan}",
        "claude_hint": "  Run: claude auth login",
        "run_login_now": "  Run login now?",
        "login_done_recheck": "  Login command finished. Re-checking.",
        "login_failed": "  Login command failed (code={code})",
        "manual_check_hint": "  Manual check: {command}",
        "api_note": "- codex_api mode selected (requires codex_api_key in credential store)",
        "policy_updated": "\nPolicy updated:",
        "updated_mode": "- mode: {mode}",
        "updated_allowlist": "- allowlist_user_ids: {allowlist}",
        "updated_backup": "- backup: {backup}",
        "updated_instance": "- instance.id: {instance_id}",
        "updated_storage_root": "- storage root: {root}",
        "active_instance_written": "- updated active instance file: {path}",
        "next_header": "\nNext:",
        "next_start_1": "1) Start bot:",
        "next_start_2": "   ./.venv/bin/python -m src.main --instance-id {instance_id}   (macOS/Linux)",
        "next_start_3": "   .\\.venv\\Scripts\\python.exe -m src.main --instance-id {instance_id}   (Windows)",
        "next_flow": "2) Telegram: /start -> /policy -> /plan ... -> /approve ... ... -> /logs ...",
        "next_bot_target": "3) Open this bot in Telegram: @{username}",
        "non_interactive_requires": "--non-interactive requires --mode and --user-id",
    },
}


def _resolve_lang(raw: str) -> str:
    value = (raw or "").strip().lower()
    if value in LANG_CHOICES:
        return value
    return "en"


def tr(lang: str, key: str, **kwargs: Any) -> str:
    return TEXTS[lang][key].format(**kwargs)


def _resolve_instance_id(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return DEFAULT_INSTANCE_ID
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", value):
        raise RuntimeError(f"invalid instance_id: {value}")
    return value


def choose_instance_id(current: str, lang: str, provided: Optional[str] = None) -> str:
    if provided is not None:
        value = _resolve_instance_id(provided)
        if not value:
            raise RuntimeError(tr(lang, "instance_invalid"))
        return value

    while True:
        raw = input(tr(lang, "instance_prompt", current=current)).strip()
        if not raw:
            return current
        try:
            return _resolve_instance_id(raw)
        except RuntimeError:
            print(tr(lang, "instance_invalid"))


def choose_setup_type(lang: str, default_add: bool) -> str:
    print(tr(lang, "setup_mode_header"))
    print(tr(lang, "setup_mode_first"))
    print(tr(lang, "setup_mode_add"))
    default_raw = "2" if default_add else "1"

    while True:
        raw = input(tr(lang, "setup_mode_prompt", default=default_raw)).strip()
        if not raw:
            return "add" if default_add else "first"
        if raw == "1":
            return "first"
        if raw == "2":
            return "add"
        print(tr(lang, "setup_mode_invalid"))


def _instance_policy_path(repo_root: Path, instance_id: str) -> Path:
    if instance_id == DEFAULT_INSTANCE_ID:
        return repo_root / POLICY_PATH
    return repo_root / INSTANCE_POLICY_DIR / instance_id / "policy.yaml"


def _service_name_for_instance(instance_id: str) -> str:
    if instance_id == DEFAULT_INSTANCE_ID:
        return BASE_SERVICE_NAME
    return f"{BASE_SERVICE_NAME}.{instance_id}"


def _seed_instance_policy(repo_root: Path, instance_id: str, lang: str) -> Path:
    target = _instance_policy_path(repo_root=repo_root, instance_id=instance_id)
    if target.exists():
        return target

    source = repo_root / POLICY_PATH
    if not source.exists():
        raise RuntimeError(tr(lang, "missing_policy", path=source))

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    print(tr(lang, "instance_new_policy_seeded", path=target))
    return target


def _apply_instance_defaults(policy: dict[str, Any], instance_id: str) -> str:
    instance = policy.setdefault("instance", {})
    if not isinstance(instance, dict):
        raise RuntimeError("instance must be an object")
    instance["id"] = instance_id

    storage = policy.setdefault("storage", {})
    if not isinstance(storage, dict):
        raise RuntimeError("storage must be an object")

    if instance_id == DEFAULT_INSTANCE_ID:
        return "data"

    root = f"data/instances/{instance_id}"
    storage["sqlite"] = f"{root}/qguard.sqlite3"
    storage["plans_dir"] = f"{root}/plans"
    storage["audit_jsonl_dir"] = f"{root}/audit/jsonl"
    storage["audit_diff_dir"] = f"{root}/audit/diffs"
    storage["audit_html_dir"] = f"{root}/audit/reports"
    return root


def _write_active_instance(repo_root: Path, instance_id: str, lang: str) -> None:
    path = repo_root / ACTIVE_INSTANCE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(instance_id + "\n", encoding="utf-8")
    print(tr(lang, "active_instance_written", path=path))


def _read_active_instance(repo_root: Path) -> Optional[str]:
    path = repo_root / ACTIVE_INSTANCE_FILE
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    try:
        return _resolve_instance_id(raw)
    except RuntimeError:
        return None


def load_policy(path: Path, lang: str) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(tr(lang, "missing_policy", path=path))
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(tr(lang, "invalid_policy_obj"))
    return data


def save_policy(path: Path, data: dict[str, Any]) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_suffix(path.suffix + f".bak.{ts}")
    shutil.copy2(path, backup)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return backup


def ask_yes_no(question: str, lang: str, default_yes: bool = True) -> bool:
    suffix = " [Y/n]: " if default_yes else " [y/N]: "
    while True:
        raw = input(question + suffix).strip().lower()
        if not raw:
            return default_yes
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print(tr(lang, "yes_no_invalid"))


def choose_mode(current: str, lang: str) -> str:
    print(tr(lang, "select_mode_header"))
    for idx, mode in enumerate(ALLOWED_MODES, start=1):
        marker = " (current)" if mode == current else ""
        print(f"  {idx}) {mode} - {MODE_LABELS[lang][mode]}{marker}")

    direct_map = {str(i + 1): mode for i, mode in enumerate(ALLOWED_MODES)}
    while True:
        raw = input(tr(lang, "mode_prompt", current=current)).strip()
        if not raw:
            return current
        if raw in direct_map:
            return direct_map[raw]
        if raw in ALLOWED_MODES:
            return raw
        print(tr(lang, "mode_invalid"))


def choose_user_id(current_ids: list[int], lang: str, provided: Optional[int] = None) -> int:
    if provided is not None:
        if provided <= 0:
            raise RuntimeError("user id must be positive")
        return provided

    default = str(current_ids[0]) if current_ids else ""
    while True:
        raw = input(tr(lang, "user_id_prompt", default=default)).strip()
        if not raw and default:
            return int(default)
        try:
            value = int(raw)
        except ValueError:
            print(tr(lang, "invalid_integer"))
            continue
        if value <= 0:
            print(tr(lang, "user_id_positive"))
            continue
        return value


def _import_keyring(lang: str):
    try:
        import keyring  # type: ignore
    except Exception as exc:  # pragma: no cover - runtime check
        raise RuntimeError(tr(lang, "keyring_required")) from exc
    return keyring


def _telegram_api_get(
    token: str,
    method: str,
    params: Optional[dict[str, Any]] = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    if params:
        url += "?" + urlencode(params)
    with urlopen(url, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    if not isinstance(payload, dict):
        raise RuntimeError("invalid telegram api response")
    return payload


def _extract_user_id_from_update(update: dict[str, Any]) -> Optional[int]:
    def _from_node(node: Any) -> Optional[int]:
        if not isinstance(node, dict):
            return None
        from_obj = node.get("from")
        if not isinstance(from_obj, dict):
            return None
        raw = from_obj.get("id")
        if isinstance(raw, int) and raw > 0:
            return raw
        return None

    for key in ("message", "edited_message", "callback_query", "inline_query", "my_chat_member", "chat_member"):
        uid = _from_node(update.get(key))
        if uid:
            return uid
    return None


def _auto_detect_user_id_from_token(
    token: str,
    lang: str,
    username: str,
    wait_seconds: int = 60,
) -> Optional[int]:
    safe_username = username or "your_bot"
    print(tr(lang, "auto_user_id_wait", username=safe_username, seconds=wait_seconds))
    try:
        initial = _telegram_api_get(token=token, method="getUpdates", params={"timeout": 1}, timeout=5.0)
        current = initial.get("result")
        updates = current if isinstance(current, list) else []
        last_update_id = 0
        for row in updates:
            if not isinstance(row, dict):
                continue
            raw_id = row.get("update_id")
            if isinstance(raw_id, int) and raw_id > last_update_id:
                last_update_id = raw_id

        for _ in range(max(1, wait_seconds)):
            payload = _telegram_api_get(
                token=token,
                method="getUpdates",
                params={"offset": last_update_id + 1, "timeout": 1},
                timeout=5.0,
            )
            result = payload.get("result")
            updates = result if isinstance(result, list) else []
            for row in updates:
                if not isinstance(row, dict):
                    continue
                raw_id = row.get("update_id")
                if isinstance(raw_id, int) and raw_id > last_update_id:
                    last_update_id = raw_id
                uid = _extract_user_id_from_update(row)
                if uid and uid > 0:
                    return uid
    except Exception:
        return None
    return None


def _inspect_telegram_token(token: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    try:
        payload = _telegram_api_get(token=token, method="getMe", timeout=10.0)
    except HTTPError as exc:
        reason = exc.reason if getattr(exc, "reason", None) else f"HTTP {exc.code}"
        return None, str(reason)
    except URLError as exc:
        reason = exc.reason if getattr(exc, "reason", None) else str(exc)
        return None, str(reason)
    except Exception as exc:  # pragma: no cover - defensive runtime handling
        return None, str(exc)

    if not isinstance(payload, dict) or not payload.get("ok"):
        desc = "-"
        if isinstance(payload, dict):
            desc = str(payload.get("description") or "-")
        return None, desc

    result = payload.get("result")
    if not isinstance(result, dict):
        return None, "invalid response"
    username = str(result.get("username") or "")
    bot_id = result.get("id")
    if not username or bot_id is None:
        return None, "missing bot identity"
    return {"username": username, "id": int(bot_id)}, None


def _set_secret_if_needed(
    service_name: str,
    account: str,
    prompt_label: str,
    required: bool,
    lang: str,
) -> Optional[dict[str, Any]]:
    keyring = _import_keyring(lang)
    existing = keyring.get_password(service_name, account)
    existing_info: Optional[dict[str, Any]] = None
    if account == "telegram_bot_token" and existing:
        existing_info, error = _inspect_telegram_token(existing)
        if existing_info:
            print(
                tr(
                    lang,
                    "telegram_existing_bot",
                    username=existing_info["username"],
                    bot_id=existing_info["id"],
                )
            )
        elif error:
            print(tr(lang, "telegram_verify_failed", reason=error))

    if existing and not ask_yes_no(tr(lang, "replace_secret", account=account), lang=lang, default_yes=False):
        print(tr(lang, "keeping_secret", account=account))
        return existing_info

    while True:
        value = getpass.getpass(tr(lang, "enter_secret", label=prompt_label)).strip()
        if value:
            info: Optional[dict[str, Any]] = None
            if account == "telegram_bot_token":
                info, error = _inspect_telegram_token(value)
                if not info:
                    print(tr(lang, "telegram_verify_failed", reason=error or "-"))
                    if required:
                        continue
                    return None
                print(tr(lang, "telegram_verified_bot", username=info["username"], bot_id=info["id"]))
            keyring.set_password(service_name, account, value)
            print(tr(lang, "stored_secret", account=account))
            return info
        if required:
            print(tr(lang, "secret_required", account=account))
            continue
        print(tr(lang, "secret_skipped", account=account))
        return None


def configure_telegram_secret(service_name: str, lang: str) -> Optional[dict[str, Any]]:
    print(tr(lang, "secrets_header"))
    print(tr(lang, "telegram_token_note"))
    token_label = "Telegram bot token" if lang == "en" else "Telegram Botトークン"
    telegram_info = _set_secret_if_needed(
        service_name=service_name,
        account="telegram_bot_token",
        prompt_label=token_label,
        required=True,
        lang=lang,
    )
    return telegram_info


def maybe_auto_detect_user_id(
    service_name: str,
    lang: str,
    telegram_info: Optional[dict[str, Any]],
    enabled: bool = True,
) -> Optional[int]:
    if not enabled:
        return None
    if not ask_yes_no(tr(lang, "auto_user_id_prompt"), lang=lang, default_yes=True):
        print(tr(lang, "auto_user_id_skipped"))
        return None

    keyring = _import_keyring(lang)
    token = keyring.get_password(service_name, "telegram_bot_token")
    if not token:
        print(tr(lang, "auto_user_id_failed"))
        return None

    username = ""
    if isinstance(telegram_info, dict):
        username = str(telegram_info.get("username") or "")
    user_id = _auto_detect_user_id_from_token(token=token, lang=lang, username=username, wait_seconds=60)
    if user_id is None:
        print(tr(lang, "auto_user_id_failed"))
        return None

    print(tr(lang, "auto_user_id_detected", user_id=user_id))
    return user_id


def configure_codex_api_secret_if_needed(mode: str, service_name: str, lang: str) -> None:
    if mode == "codex_api":
        key_label = "Codex API key" if lang == "en" else "Codex APIキー"
        _set_secret_if_needed(
            service_name=service_name,
            account="codex_api_key",
            prompt_label=key_label,
            required=True,
            lang=lang,
        )
    else:
        print(tr(lang, "api_key_optional"))


def _run_status(cmd: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except FileNotFoundError:
        return 127, "command not found"
    except subprocess.TimeoutExpired:
        return 124, "status check timed out"

    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    text = (out + "\n" + err).strip()
    return proc.returncode, text


def _run_login_command(cmd: list[str]) -> int:
    try:
        proc = subprocess.run(cmd, check=False)
    except FileNotFoundError:
        return 127
    return int(proc.returncode)


def verify_engine_prereq(mode: str, lang: str, allow_prompt_login: bool = True) -> None:
    print(tr(lang, "prereq_header"))
    if mode == "codex_subscription":
        rc, text = _run_status(["codex", "login", "status"])
        if rc == 0 and "logged in" in text.lower():
            print(tr(lang, "codex_ok"))
            detail = next((ln.strip() for ln in text.splitlines() if ln.strip()), "unknown")
            print(tr(lang, "codex_detail", detail=detail))
            print(tr(lang, "manual_check_hint", command="codex login status"))
        else:
            print(tr(lang, "codex_ng"))
            print(tr(lang, "codex_hint"))
            if allow_prompt_login and ask_yes_no(tr(lang, "run_login_now"), lang=lang, default_yes=False):
                code = _run_login_command(["codex", "login"])
                if code == 0:
                    print(tr(lang, "login_done_recheck"))
                    verify_engine_prereq(mode, lang=lang, allow_prompt_login=False)
                else:
                    print(tr(lang, "login_failed", code=code))
        return

    if mode == "claude_subscription":
        rc, text = _run_status(["claude", "auth", "status"])
        if rc == 0:
            try:
                payload = json.loads(text)
                logged_in = bool(payload.get("loggedIn"))
                if logged_in:
                    print(tr(lang, "claude_ok"))
                    print(
                        tr(
                            lang,
                            "claude_detail",
                            method=str(payload.get("authMethod") or "-"),
                            email=str(payload.get("email") or "-"),
                            plan=str(payload.get("subscriptionType") or "-"),
                        )
                    )
                    print(tr(lang, "manual_check_hint", command="claude auth status"))
                    return
            except json.JSONDecodeError:
                pass
        print(tr(lang, "claude_ng"))
        print(tr(lang, "claude_hint"))
        if allow_prompt_login and ask_yes_no(tr(lang, "run_login_now"), lang=lang, default_yes=False):
            code = _run_login_command(["claude", "auth", "login"])
            if code == 0:
                print(tr(lang, "login_done_recheck"))
                verify_engine_prereq(mode, lang=lang, allow_prompt_login=False)
            else:
                print(tr(lang, "login_failed", code=code))
        return

    print(tr(lang, "api_note"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Q CodeAnzenn desktop setup wizard")
    parser.add_argument(
        "--mode",
        choices=ALLOWED_MODES,
        help="Planner engine mode",
    )
    parser.add_argument("--user-id", type=int, help="Telegram user id to set in allowlist")
    parser.add_argument(
        "--instance-id",
        help="Instance id for multi-bot isolation (alnum/_/-). default: default",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Use CLI args only (requires --mode and --user-id)",
    )
    parser.add_argument(
        "--skip-secrets",
        action="store_true",
        help="Skip OS credential storage prompts",
    )
    parser.add_argument(
        "--lang",
        choices=LANG_CHOICES,
        help="UI language: ja or en",
    )
    args = parser.parse_args()

    lang = _resolve_lang(args.lang or os.getenv("QCA_SETUP_LANG", ""))

    repo_root = Path(__file__).resolve().parents[1]
    env_instance = os.getenv("QCA_INSTANCE_ID", "")
    active_instance = _read_active_instance(repo_root=repo_root)
    requested_instance = args.instance_id or env_instance or active_instance or DEFAULT_INSTANCE_ID
    try:
        default_instance_id = _resolve_instance_id(requested_instance)
    except RuntimeError:
        print(tr(lang, "instance_invalid"))
        return 2

    if args.non_interactive:
        if not args.mode or not args.user_id:
            print(tr(lang, "non_interactive_requires"))
            return 2
        instance_id = default_instance_id
    else:
        setup_type = choose_setup_type(lang=lang, default_add=bool(active_instance))
        if args.instance_id:
            instance_seed = args.instance_id
        elif setup_type == "first":
            instance_seed = DEFAULT_INSTANCE_ID
        else:
            if active_instance and active_instance != DEFAULT_INSTANCE_ID:
                instance_seed = active_instance
            else:
                instance_seed = "bot2"
        instance_id = choose_instance_id(instance_seed, lang=lang, provided=args.instance_id)

    policy_path = _instance_policy_path(repo_root=repo_root, instance_id=instance_id)
    if instance_id != DEFAULT_INSTANCE_ID:
        policy_path = _seed_instance_policy(repo_root=repo_root, instance_id=instance_id, lang=lang)

    policy = load_policy(policy_path, lang=lang)
    engine = policy.setdefault("engine", {})
    users = policy.setdefault("users", {})
    ui = policy.setdefault("ui", {})
    service_name = _service_name_for_instance(instance_id)

    current_mode = str(engine.get("mode", "codex_api"))
    current_allowlist = [int(x) for x in users.get("allowlist_user_ids", [])]

    print(tr(lang, "wizard_title"))
    print(tr(lang, "repo", repo=repo_root))
    print(tr(lang, "policy", policy=policy_path))
    print(tr(lang, "instance_id", instance_id=instance_id))
    print(tr(lang, "secret_service", service_name=service_name))
    print(tr(lang, "current_mode", mode=current_mode))
    print(tr(lang, "current_allowlist", allowlist=current_allowlist))

    telegram_info: Optional[dict[str, Any]] = None
    if not args.skip_secrets:
        telegram_info = configure_telegram_secret(service_name=service_name, lang=lang)

    if args.non_interactive:
        mode = args.mode
        user_id = args.user_id
    else:
        mode = args.mode or choose_mode(current_mode, lang=lang)
        detected_user_id: Optional[int] = None
        if args.user_id is None:
            detected_user_id = maybe_auto_detect_user_id(
                service_name=service_name,
                lang=lang,
                telegram_info=telegram_info,
                enabled=True,
            )
        user_id = choose_user_id(current_allowlist, lang=lang, provided=args.user_id or detected_user_id)

    engine["mode"] = mode
    users["allowlist_user_ids"] = [int(user_id)]
    ui["language"] = lang
    storage_root = _apply_instance_defaults(policy=policy, instance_id=instance_id)

    backup = save_policy(policy_path, policy)
    print(tr(lang, "policy_updated"))
    print(tr(lang, "updated_mode", mode=mode))
    print(tr(lang, "updated_allowlist", allowlist=[int(user_id)]))
    print(tr(lang, "updated_instance", instance_id=instance_id))
    print(tr(lang, "updated_storage_root", root=storage_root))
    print(tr(lang, "updated_backup", backup=backup))
    _write_active_instance(repo_root=repo_root, instance_id=instance_id, lang=lang)

    if not args.skip_secrets:
        configure_codex_api_secret_if_needed(mode=mode, service_name=service_name, lang=lang)

    verify_engine_prereq(mode, lang=lang, allow_prompt_login=not args.non_interactive)

    print(tr(lang, "next_header"))
    print(tr(lang, "next_start_1"))
    print(tr(lang, "next_start_2", instance_id=instance_id))
    print(tr(lang, "next_start_3", instance_id=instance_id))
    print(tr(lang, "next_flow"))
    if telegram_info and telegram_info.get("username"):
        print(tr(lang, "next_bot_target", username=telegram_info["username"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
