"""Q CodeAnzenn Telegram bot entrypoint."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import re

from telegram import BotCommand, MenuButtonCommands
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters

from src.bot.handlers import TelegramHandlers
from src.bot.menu import resolve_lang
from src.core.runtime import AppRuntime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)


def _resolve_instance_id(raw: str) -> str:
    value = (raw or "default").strip()
    if not value:
        return "default"
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", value):
        raise ValueError("instance_id must match [A-Za-z0-9_-]{1,40}")
    return value


def _default_policy_path(workspace_root: Path, instance_id: str) -> Path:
    if instance_id == "default":
        return workspace_root / "config/policy.yaml"
    return workspace_root / "config" / "instances" / instance_id / "policy.yaml"


def _default_secret_service_name(instance_id: str) -> str:
    if instance_id == "default":
        return "qcodeanzenn"
    return f"qcodeanzenn.{instance_id}"


def _commands_for_lang(lang: str) -> list[BotCommand]:
    if lang == "en":
        return [
            BotCommand("start", "Show bot status"),
            BotCommand("policy", "Show safety policy"),
            BotCommand("task", "Create TASK from request"),
            BotCommand("plan", "Alias of /task"),
            BotCommand("approve", "Approve TASK and execute"),
            BotCommand("reject", "Reject TASK"),
            BotCommand("status", "Engine/runtime or TASK status"),
            BotCommand("logs", "Show TASK audit logs"),
        ]
    return [
        BotCommand("start", "起動状態を表示"),
        BotCommand("policy", "安全ポリシーを表示"),
        BotCommand("task", "依頼からTASKを作成"),
        BotCommand("plan", "/task の別名"),
        BotCommand("approve", "TASKを承認して実行"),
        BotCommand("reject", "TASKを拒否"),
        BotCommand("status", "接続/稼働またはTASK状態"),
        BotCommand("logs", "TASK監査ログを表示"),
    ]


def _build_post_init(lang: str):
    async def _post_init(application: Application) -> None:
        """Register command menu shown in Telegram chat UI."""
        commands = _commands_for_lang(lang)
        lang_code = "en" if lang == "en" else "ja"
        await application.bot.set_my_commands(commands=commands)
        await application.bot.set_my_commands(commands=commands, language_code=lang_code)
        await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())

    return _post_init


def main() -> None:
    parser = argparse.ArgumentParser(description="Q CodeAnzenn Telegram runner")
    parser.add_argument(
        "--instance-id",
        help="Instance id for multi-bot isolation (default: default)",
    )
    args = parser.parse_args()

    workspace_root = Path(os.getenv("QG_WORKSPACE_ROOT", Path(__file__).resolve().parents[1]))
    instance_id = _resolve_instance_id(args.instance_id or os.getenv("QCA_INSTANCE_ID", "default"))

    policy_path_raw = os.getenv("QG_POLICY_PATH", "").strip()
    if policy_path_raw:
        policy_path = Path(policy_path_raw)
    else:
        policy_path = _default_policy_path(workspace_root=workspace_root, instance_id=instance_id)

    secret_service_name = os.getenv("QCA_SECRET_SERVICE_NAME", "").strip() or _default_secret_service_name(
        instance_id=instance_id
    )
    logging.info(
        "starting instance_id=%s policy=%s secret_service=%s",
        instance_id,
        policy_path,
        secret_service_name,
    )

    runtime = AppRuntime(
        workspace_root=workspace_root,
        policy_path=policy_path,
        secret_service_name=secret_service_name,
    )
    ui_lang = resolve_lang(runtime.policy.ui.language)
    handlers = TelegramHandlers(runtime, language=ui_lang)

    app = ApplicationBuilder().token(runtime.telegram_bot_token).post_init(_build_post_init(ui_lang)).build()

    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("policy", handlers.policy))
    app.add_handler(CommandHandler("task", handlers.plan))
    app.add_handler(CommandHandler("plan", handlers.plan))
    app.add_handler(CommandHandler("approve", handlers.approve))
    app.add_handler(CommandHandler("reject", handlers.reject))
    app.add_handler(CommandHandler("status", handlers.status))
    app.add_handler(CommandHandler("logs", handlers.logs))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handlers.menu_text))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
