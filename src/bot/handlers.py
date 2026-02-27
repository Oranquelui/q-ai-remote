"""Telegram command handlers."""

from __future__ import annotations

import html
import logging
import re
import subprocess
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from src.bot.menu import main_menu_markup, menu_action_from_text, resolve_lang
from src.bot.templates import (
    approved_text,
    chat_in_progress_text,
    execution_summary_text,
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


def _render_telegram_html(text: str) -> str:
    # Escape user/model text first, then allow a minimal Markdown-style bold: **text**.
    escaped = html.escape(text or "")

    def _bold_sub(match: re.Match[str]) -> str:
        inner = match.group(1)
        if not inner.strip():
            return match.group(0)
        return f"<b>{inner}</b>"

    return re.sub(r"\*\*(.+?)\*\*", _bold_sub, escaped)


def _is_reject_all_intent(text: str) -> bool:
    src = text or ""
    lower = src.lower()
    has_task = ("task" in lower) or ("タスク" in src)
    has_all = any(token in src for token in ("全て", "すべて", "全部", "全")) or ("all" in lower)
    has_reject = any(token in src for token in ("削除", "消去", "消して", "クリア", "取り消", "キャンセル")) or any(
        token in lower for token in ("delete", "clear", "cancel", "reject")
    )
    return has_task and has_all and has_reject


def _cb_approve(plan_id: str, short_token: str) -> str:
    return f"ap|{plan_id}|{short_token}"


def _cb_reject(plan_id: str) -> str:
    return f"rj|{plan_id}"


def _cb_status(plan_id: str) -> str:
    return f"st|{plan_id}"


def _cb_logs(plan_id: str) -> str:
    return f"lg|{plan_id}"


def _parse_callback_data(raw: str) -> tuple[str, str, str]:
    parts = (raw or "").split("|")
    if len(parts) == 2:
        action, plan_id = parts
        return action.strip(), plan_id.strip(), ""
    if len(parts) >= 3:
        action, plan_id, token = parts[0], parts[1], parts[2]
        return action.strip(), plan_id.strip(), token.strip()
    return "", "", ""


class TelegramHandlers:
    def __init__(self, runtime: AppRuntime, language: str = "ja") -> None:
        self.runtime = runtime
        self.lang = resolve_lang(language)

    def _format_execution_error(self, exc: Exception) -> str:
        detail = str(exc)
        if "create_file target already exists:" in detail:
            path = detail.split("create_file target already exists:", 1)[1].strip()
            if self.lang == "en":
                return (
                    f"Execution error: file already exists: {path}\n"
                    "Use /task and request patch_file for that path."
                )
            return (
                f"承認/実行エラー: 既存ファイルです: {path}\n"
                "/task でそのパスは patch_file を使うよう依頼してください。"
            )

        if self.lang == "en":
            return f"Execution error: {detail}"
        return f"承認/実行エラー: {detail}"

    def _plan_actions_markup(self, plan_id: str, short_token: str) -> InlineKeyboardMarkup:
        if self.lang == "en":
            rows = [
                [
                    InlineKeyboardButton("✅ Execute", callback_data=_cb_approve(plan_id, short_token)),
                    InlineKeyboardButton("❌ Reject", callback_data=_cb_reject(plan_id)),
                ],
                [
                    InlineKeyboardButton("📌 Status", callback_data=_cb_status(plan_id)),
                    InlineKeyboardButton("🧾 Logs", callback_data=_cb_logs(plan_id)),
                ],
            ]
        else:
            rows = [
                [
                    InlineKeyboardButton("✅ 実行", callback_data=_cb_approve(plan_id, short_token)),
                    InlineKeyboardButton("❌ 破棄", callback_data=_cb_reject(plan_id)),
                ],
                [
                    InlineKeyboardButton("📌 状態", callback_data=_cb_status(plan_id)),
                    InlineKeyboardButton("🧾 ログ", callback_data=_cb_logs(plan_id)),
                ],
            ]
        return InlineKeyboardMarkup(rows)

    async def _reply(self, update: Update, text: str, inline_markup: InlineKeyboardMarkup | None = None) -> None:
        message = update.message
        if message is None and update.callback_query is not None:
            message = update.callback_query.message
        if message is None:
            return
        rendered = _render_telegram_html(text)
        reply_markup = inline_markup if inline_markup is not None else main_menu_markup(self.lang)
        try:
            await message.reply_text(
                rendered,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=reply_markup,
            )
        except BadRequest:
            await message.reply_text(text, reply_markup=reply_markup)

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
        await self._reply(
            update,
            plan_text(plan),
            inline_markup=self._plan_actions_markup(plan_id=plan.plan_id, short_token=plan.short_token),
        )

    async def _answer_chat_text(self, update: Update, user_text: str) -> None:
        await self._reply(update, chat_in_progress_text(self.lang))
        started_at = time.time()
        try:
            answer = self.runtime.answer_chat(
                user_id=_user_id(update),
                user_text=user_text,
            )
        except (RuntimePolicyError, RateLimitExceeded, ApprovalError, RuntimeError) as exc:
            await self._reply(update, f"回答生成に失敗しました: {exc}")
            return
        elapsed_ms = int((time.time() - started_at) * 1000)
        LOGGER.info("chat answered user_id=%s elapsed_ms=%s", _user_id(update), elapsed_ms)
        await self._reply(update, answer)

    async def _reject_all_pending(self, update: Update) -> None:
        try:
            plans = self.runtime.list_pending_plans(user_id=_user_id(update), limit=200)
        except (RuntimePolicyError, RateLimitExceeded, ApprovalError, RuntimeError) as exc:
            await self._reply(update, f"TASK一括削除に失敗しました: {exc}")
            return

        if not plans:
            await self._reply(update, "承認待ちTASKはありません。")
            return

        rejected: list[str] = []
        failed: list[str] = []
        for item in plans:
            try:
                self.runtime.reject_plan(plan_id=item.plan_id, user_id=_user_id(update))
                rejected.append(item.plan_id)
            except (RuntimePolicyError, ApprovalError, RuntimeError):
                failed.append(item.plan_id)

        lines = [
            "承認待ちTASKを一括削除しました。",
            f"削除: **{len(rejected)}件**",
            f"失敗: {len(failed)}件",
        ]
        if rejected:
            show = ", ".join(rejected[:8])
            if len(rejected) > 8:
                show += ", ..."
            lines.append(f"plan_id: {show}")
        if failed:
            show = ", ".join(failed[:5])
            if len(failed) > 5:
                show += ", ..."
            lines.append(f"失敗plan_id: {show}")
        await self._reply(update, "\n".join(lines))

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
            context.user_data["awaiting_plan_text"] = True
            context.user_data["awaiting_chat_text"] = False
            prompt = (
                "Send your request in one message.\n"
                "It will be processed with the same flow as /task (Plan+Risk only)."
                if self.lang == "en"
                else "依頼内容を1メッセージで送ってください。\n受信後に /task と同じ処理で Plan+Risk を作成します。"
            )
            await self._reply(update, prompt)
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
            await self._reply(update, self._format_execution_error(exc))
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

    async def inline_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None:
            return

        action, plan_id, short_token = _parse_callback_data(query.data or "")
        if not action or not plan_id:
            await query.answer("Invalid action", show_alert=False)
            return
        await query.answer()

        if action == "ap":
            if not short_token:
                await self._reply(update, "承認に必要なトークンが不足しています。")
                return
            try:
                await self._reply(update, approved_text(plan_id))
                result, _report, _jsonl = self.runtime.approve_and_execute(
                    plan_id=plan_id,
                    short_token=short_token,
                    user_id=_user_id(update),
                )
            except (RuntimePolicyError, RateLimitExceeded, ApprovalError, RuntimeError) as exc:
                await self._reply(update, self._format_execution_error(exc))
                return
            await self._reply(update, execution_summary_text(result))
            return

        if action == "rj":
            try:
                status = self.runtime.reject_plan(plan_id=plan_id, user_id=_user_id(update))
            except (RuntimePolicyError, ApprovalError, RuntimeError) as exc:
                await self._reply(update, f"rejectに失敗しました: {exc}")
                return
            await self._reply(update, f"Planを拒否しました\nplan_id: {plan_id}\nstatus: {status}")
            return

        if action == "st":
            try:
                status = self.runtime.get_status(plan_id=plan_id, user_id=_user_id(update))
            except (RuntimePolicyError, RateLimitExceeded, ApprovalError, RuntimeError) as exc:
                await self._reply(update, f"status取得に失敗しました: {exc}")
                return
            await self._reply(update, f"Plan状態\nplan_id: {plan_id}\nstatus: {status}")
            return

        if action == "lg":
            try:
                view = self.runtime.get_logs(plan_id=plan_id, user_id=_user_id(update))
            except (RuntimePolicyError, RateLimitExceeded, ApprovalError, RuntimeError) as exc:
                await self._reply(update, f"logs取得に失敗しました: {exc}")
                return
            await self._reply(
                update,
                logs_text(
                    plan_id=view.plan_id,
                    final_status=view.final_status,
                    diff_summary=view.diff_path,
                    jsonl_path=view.jsonl_path,
                    html_path=view.html_report_path,
                ),
            )
            return

    async def menu_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = (update.message.text or "").strip()
        if not text:
            return

        if _is_reject_all_intent(text):
            context.user_data["awaiting_chat_text"] = False
            context.user_data["awaiting_plan_text"] = False
            await self._reject_all_pending(update)
            return

        action = menu_action_from_text(text)

        if context.user_data.get("awaiting_plan_text") and action is None:
            context.user_data["awaiting_plan_text"] = False
            await self._create_plan_from_text(update, request_text=text)
            return
        if context.user_data.get("awaiting_chat_text") and action is None:
            context.user_data["awaiting_chat_text"] = False
            await self._answer_chat_text(update, user_text=text)
            return

        if action == "new_task":
            context.user_data["awaiting_plan_text"] = True
            context.user_data["awaiting_chat_text"] = False
            prompt = (
                "Send your request in one message.\n"
                "It will be processed with the same flow as /task (Plan+Risk only)."
                if self.lang == "en"
                else "依頼内容を1メッセージで送ってください。\n受信後に /task と同じ処理で Plan+Risk を作成します。"
            )
            await self._reply(update, prompt)
            return

        if action == "ask_chat":
            context.user_data["awaiting_chat_text"] = True
            context.user_data["awaiting_plan_text"] = False
            prompt = (
                "Send your question in one message.\n"
                "I will answer in chat mode (no execution)."
                if self.lang == "en"
                else "質問を1メッセージで送ってください。\nチャットモードで回答します（実行なし）。"
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
            if plans:
                latest = plans[0]
                prompt = (
                    f"Latest pending TASK: {latest.plan_id}\nUse buttons below."
                    if self.lang == "en"
                    else f"最新の承認待ちTASK: {latest.plan_id}\n下のボタンで実行/破棄できます。"
                )
                await self._reply(
                    update,
                    prompt,
                    inline_markup=self._plan_actions_markup(plan_id=latest.plan_id, short_token=latest.short_token),
                )
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
            try:
                plans = self.runtime.list_recent_plans(user_id=_user_id(update), limit=20)
            except (RuntimePolicyError, RateLimitExceeded, ApprovalError, RuntimeError) as exc:
                await self._reply(update, f"ログ候補の取得に失敗しました: {exc}")
                return

            target_id = ""
            for p in plans:
                if p.status in {"EXECUTED", "FAILED"}:
                    target_id = p.plan_id
                    break

            if not target_id:
                msg = (
                    "No executed TASK found yet. Run one TASK first."
                    if self.lang == "en"
                    else "実行済みTASKがまだありません。先に1件実行してください。"
                )
                await self._reply(update, msg)
                return

            try:
                view = self.runtime.get_logs(plan_id=target_id, user_id=_user_id(update))
            except (RuntimePolicyError, RateLimitExceeded, ApprovalError, RuntimeError) as exc:
                await self._reply(update, f"logs取得に失敗しました: {exc}")
                return

            await self._reply(
                update,
                logs_text(
                    plan_id=view.plan_id,
                    final_status=view.final_status,
                    diff_summary=view.diff_path,
                    jsonl_path=view.jsonl_path,
                    html_path=view.html_report_path,
                ),
            )
            return

        if action == "help":
            await self._reply(update, menu_help_text(self.lang))
            return

        await self._answer_chat_text(update, user_text=text)
