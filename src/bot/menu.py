"""Telegram in-chat persistent menu definitions (i18n)."""

from __future__ import annotations

from typing import Optional

from telegram import ReplyKeyboardMarkup

LANGS = ("ja", "en")
MENU_ACTIONS = ("task_list", "continue_task", "ask_chat", "new_task", "task_guide", "logs")

MENU_TEXTS = {
    "ja": {
        "task_list": "TASK履歴",
        "continue_task": "承認待ち",
        "ask_chat": "自由質問",
        "new_task": "新規TASK",
        "task_guide": "使い方",
        "logs": "実行ログ",
    },
    "en": {
        "task_list": "TASK History",
        "continue_task": "Pending TASKs",
        "ask_chat": "Ask Freely",
        "new_task": "New TASK",
        "task_guide": "How To Use",
        "logs": "Run Logs",
    },
}

LEGACY_TEXT_ALIASES = {
    "TASK一覧(直近20)": "task_list",
    "承認待ちTASK": "continue_task",
    "新規TASK開始": "new_task",
    "TASKの進め方": "task_guide",
    "監査ログ": "logs",
    "新規タスク作成": "new_task",
    "ポリシー確認": "policy",
    "状態確認": "status",
    "ログ確認": "logs",
    "使い方": "task_guide",
    "自由質問": "ask_chat",
    "Create Task": "new_task",
    "Policy": "policy",
    "Status": "status",
    "Logs": "logs",
    "Help": "task_guide",
    "Ask Freely": "ask_chat",
}

MENU_LAYOUT = (
    ("new_task", "continue_task"),
    ("ask_chat", "task_list"),
    ("logs", "task_guide"),
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
        "自由質問またはTASKを選択 / そのまま入力も可"
        if resolve_lang(lang) == "ja"
        else "Ask freely or select TASK / typing is also OK"
    )
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        one_time_keyboard=False,
        input_field_placeholder=placeholder,
    )
