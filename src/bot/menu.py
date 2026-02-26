"""Telegram in-chat persistent menu definitions (i18n)."""

from __future__ import annotations

from typing import Optional

from telegram import ReplyKeyboardMarkup

LANGS = ("ja", "en")
MENU_ACTIONS = ("task_list", "continue_task", "new_task", "task_guide", "policy", "status", "logs")

MENU_TEXTS = {
    "ja": {
        "task_list": "TASK一覧(直近20)",
        "continue_task": "承認待ちTASK",
        "new_task": "新規TASK開始",
        "task_guide": "TASKの進め方",
        "policy": "安全ポリシー",
        "status": "接続/稼働状態",
        "logs": "監査ログ",
    },
    "en": {
        "task_list": "TASK List (20)",
        "continue_task": "Pending TASKs",
        "new_task": "Start New TASK",
        "task_guide": "TASK Guide",
        "policy": "Safety Policy",
        "status": "Engine/Runtime",
        "logs": "Audit Logs",
    },
}

LEGACY_TEXT_ALIASES = {
    "新規タスク作成": "new_task",
    "ポリシー確認": "policy",
    "状態確認": "status",
    "ログ確認": "logs",
    "使い方": "task_guide",
    "Create Task": "new_task",
    "Policy": "policy",
    "Status": "status",
    "Logs": "logs",
    "Help": "task_guide",
}

MENU_LAYOUT = (
    ("task_list", "continue_task"),
    ("new_task", "task_guide"),
    ("policy", "status"),
    ("logs",),
)


def resolve_lang(raw: str) -> str:
    lang = (raw or "").strip().lower()
    if lang in LANGS:
        return lang
    return "ja"


def label_for(action: str, lang: str) -> str:
    resolved = resolve_lang(lang)
    return MENU_TEXTS[resolved][action]


def menu_labels(lang: str) -> dict[str, str]:
    resolved = resolve_lang(lang)
    return dict(MENU_TEXTS[resolved])


def menu_action_from_text(text: str) -> Optional[str]:
    raw = (text or "").strip()
    if not raw:
        return None
    alias = LEGACY_TEXT_ALIASES.get(raw)
    if alias:
        return alias
    for lang in LANGS:
        table = MENU_TEXTS[lang]
        for action, label in table.items():
            if raw == label:
                return action
    return None


def main_menu_markup(lang: str) -> ReplyKeyboardMarkup:
    labels = menu_labels(lang)
    keyboard = [[labels[action] for action in row] for row in MENU_LAYOUT]
    placeholder = (
        "TASKを選択 / または依頼文をそのまま入力"
        if resolve_lang(lang) == "ja"
        else "Select TASK or type a request directly"
    )
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        one_time_keyboard=False,
        input_field_placeholder=placeholder,
    )
