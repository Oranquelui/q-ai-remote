"""Telegram command handlers."""

from __future__ import annotations

import logging
import subprocess

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.menu import main_menu_markup, menu_action_from_text, resolve_lang
from src.bot.templates import (
    approved_text,
    execution_summary_text,
    free_text_routed_text,
    logs_text,
    menu_help_text,
    pending_task_text,
    plan_text,
    planning_in_progress_text,
    policy_text,
    runtime_status_text,
    start_text,
    task_list_text,
)
from src.core.approval_service import ApprovalError
from src.core.runtime import AppRuntime, RuntimePolicyError
from src.security.path_guard import PathGuardViolation
from src.security.rate_limit import RateLimitExceeded

LOGGER = logging.getLogger(__name__)


def _user_id(update: Update) -> int:
    assert update.effective_user is not None
    return int(update.effective_user.id)


def _chat_id(update: Update) -> int:
    assert update.effective_chat is not None
    return int(update.effective_chat.id)


def _args(context: ContextTypes.DEFAULT_TYPE) -> list[str]:
    raw = getattr(context, "args", None)
    if not raw:
        return []
    return [str(x) for x in raw]


class TelegramHandlers:
    def __init__(self, runtime: AppRuntime, language: str = "ja") -> None:
        self.runtime = runtime
        self.lang = resolve_lang(language)

    async def _reply(self, update: Update, text: str) -> None:
        await update.message.reply_text(text, reply_markup=main_menu_markup(self.lang))

    async def _create_plan_from_text(self, update: Update, request_text: str) -> None:
        await self._reply(update, planning_in_progress_text(self.lang))
        LOGGER.info("plan requested user_id=%s text_len=%s", _user_id(update), len(request_text))
        try:
            plan = self.runtime.create_plan(
                request_text=request_text,
                user_id=_user_id(update),
                chat_id=_chat_id(update),
            )
        except (RuntimePolicyError, RateLimitExceeded, PathGuardViolation, ApprovalError, RuntimeError) as exc:
            await self._reply(update, f"Planを拒否しました: {exc}")
            return

        LOGGER.info("plan created plan_id=%s user_id=%s", plan.plan_id, _user_id(update))
        await self._reply(update, plan_text(plan))

    def _engine_connectivity_summary(self) -> str:
        mode = self.runtime.policy.engine.mode
        if mode == "codex_api":
            return "OK (codex_api configured)"

        if mode == "codex_subscription":
            command = self.runtime.policy.engine.codex_cli.command
            argv = [command, "login", "status"]
        elif mode == "claude_subscription":
            command = self.runtime.policy.engine.claude_cli.command
            argv = [command, "auth", "status"]
        else:
            return f"UNKNOWN (unsupported mode: {mode})"

        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except FileNotFoundError:
            return f"NG ({command} not found)"
        except subprocess.TimeoutExpired:
            return "UNKNOWN (status check timeout)"
        except Exception as exc:  # pragma: no cover - defensive runtime handling
            return f"UNKNOWN ({type(exc).__name__})"

        if proc.returncode == 0:
            return "OK"
        detail = ((proc.stderr or "").strip() or (proc.stdout or "").strip() or f"rc={proc.returncode}")
        if len(detail) > 120:
            detail = detail[-120:]
        return f"NG ({detail})"

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._reply(update, start_text(self.lang))

    async def policy(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._reply(update, policy_text(self.lang))

    async def plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = _args(context)
        text = " ".join(args).strip()
        if not text:
            usage = "Usage: /plan <request>" if self.lang == "en" else "使い方: /plan <依頼内容>"
            await self._reply(update, usage)
            return

        await self._create_plan_from_text(update, request_text=text)

    async def approve(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = _args(context)
        if len(args) != 2:
            usage = (
                "Usage: /approve <plan_id> <short_token>"
                if self.lang == "en"
                else "使い方: /approve <plan_id> <short_token>"
            )
            await self._reply(update, usage)
            return

        plan_id, short_token = args[0].strip(), args[1].strip()

        try:
            await self._reply(update, approved_text(plan_id))
            result, _report, _jsonl = self.runtime.approve_and_execute(
                plan_id=plan_id,
                short_token=short_token,
                user_id=_user_id(update),
            )
        except (RuntimePolicyError, RateLimitExceeded, ApprovalError, RuntimeError) as exc:
            await self._reply(update, f"承認または実行を拒否しました: {exc}")
            return

        await self._reply(update, execution_summary_text(result))

    async def reject(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = _args(context)
        if len(args) != 1:
            usage = "Usage: /reject <plan_id>" if self.lang == "en" else "使い方: /reject <plan_id>"
            await self._reply(update, usage)
            return

        plan_id = args[0].strip()
        try:
            status = self.runtime.reject_plan(plan_id=plan_id, user_id=_user_id(update))
        except (RuntimePolicyError, ApprovalError, RuntimeError) as exc:
            await self._reply(update, f"rejectに失敗しました: {exc}")
            return

        await self._reply(update, f"Planを拒否しました\nplan_id: {plan_id}\nstatus: {status}")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = _args(context)
        if len(args) == 0:
            try:
                runtime_status = self.runtime.get_runtime_status(user_id=_user_id(update))
                engine_connectivity = self._engine_connectivity_summary()
            except (RuntimePolicyError, RateLimitExceeded, ApprovalError, RuntimeError) as exc:
                await self._reply(update, f"status取得に失敗しました: {exc}")
                return
            await self._reply(
                update,
                runtime_status_text(
                    instance_id=runtime_status["instance_id"],
                    engine_mode=runtime_status["engine_mode"],
                    engine_connectivity=engine_connectivity,
                    lang=self.lang,
                ),
            )
            return

        if len(args) != 1:
            usage = "Usage: /status [plan_id]" if self.lang == "en" else "使い方: /status [plan_id]"
            await self._reply(update, usage)
            return

        plan_id = args[0].strip()
        try:
            status = self.runtime.get_status(plan_id=plan_id, user_id=_user_id(update))
        except (RuntimePolicyError, RateLimitExceeded, ApprovalError, RuntimeError) as exc:
            await self._reply(update, f"status取得に失敗しました: {exc}")
            return

        await self._reply(update, f"Plan状態\nplan_id: {plan_id}\nstatus: {status}")

    async def logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = _args(context)
        if len(args) != 1:
            usage = "Usage: /logs <plan_id>" if self.lang == "en" else "使い方: /logs <plan_id>"
            await self._reply(update, usage)
            return

        plan_id = args[0].strip()
        try:
            view = self.runtime.get_logs(plan_id=plan_id, user_id=_user_id(update))
        except (RuntimePolicyError, RateLimitExceeded, ApprovalError, RuntimeError) as exc:
            await self._reply(update, f"logs取得に失敗しました: {exc}")
            return

        diff_summary = view.diff_path
        await self._reply(
            update,
            logs_text(
                plan_id=view.plan_id,
                final_status=view.final_status,
                diff_summary=diff_summary,
                jsonl_path=view.jsonl_path,
                html_path=view.html_report_path,
            )
        )

    async def menu_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = (update.message.text or "").strip()
        if not text:
            return

        action = menu_action_from_text(text)

        if context.user_data.get("awaiting_plan_text") and action is None:
            context.user_data["awaiting_plan_text"] = False
            await self._create_plan_from_text(update, request_text=text)
            return

        if action == "new_task":
            context.user_data["awaiting_plan_text"] = True
            prompt = (
                "Send your request in one message.\n"
                "It will be processed with the same flow as /task (Plan+Risk only)."
                if self.lang == "en"
                else "依頼内容を1メッセージで送ってください。\n受信後に /task と同じ処理で Plan+Risk を作成します。"
            )
            await self._reply(update, prompt)
            return

        if action == "task_list":
            try:
                plans = self.runtime.list_recent_plans(user_id=_user_id(update), limit=20)
            except (RuntimePolicyError, RateLimitExceeded, ApprovalError, RuntimeError) as exc:
                await self._reply(update, f"TASK一覧の取得に失敗しました: {exc}")
                return
            items = [
                {
                    "plan_id": p.plan_id,
                    "status": p.status,
                    "risk_level": p.risk_level,
                    "risk_score": str(p.risk_score),
                }
                for p in plans
            ]
            await self._reply(update, task_list_text(items=items, lang=self.lang))
            return

        if action == "continue_task":
            try:
                plans = self.runtime.list_pending_plans(user_id=_user_id(update), limit=10)
            except (RuntimePolicyError, RateLimitExceeded, ApprovalError, RuntimeError) as exc:
                await self._reply(update, f"承認待ちTASKの取得に失敗しました: {exc}")
                return
            items = [
                {
                    "plan_id": p.plan_id,
                    "short_token": p.short_token,
                    "risk_level": p.risk_level,
                    "risk_score": str(p.risk_score),
                    "expires_at": p.expires_at,
                }
                for p in plans
            ]
            await self._reply(update, pending_task_text(items=items, lang=self.lang))
            return

        if action == "task_guide":
            await self._reply(update, menu_help_text(self.lang))
            return

        if action == "policy":
            await self._reply(update, policy_text(self.lang))
            return

        if action == "status":
            await self.status(update, context)
            return

        if action == "logs":
            usage = "Usage: /logs <plan_id>" if self.lang == "en" else "使い方: /logs <plan_id>"
            await self._reply(update, usage)
            return

        if action == "help":
            await self._reply(update, menu_help_text(self.lang))
            return

        await self._reply(update, free_text_routed_text(self.lang))
        await self._create_plan_from_text(update, request_text=text)
