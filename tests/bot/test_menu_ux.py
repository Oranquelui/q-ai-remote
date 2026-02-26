from src.bot.menu import menu_action_from_text, menu_labels
from src.bot.templates import pending_task_text, task_list_text


def test_menu_labels_include_task_terms_ja() -> None:
    labels = menu_labels("ja")
    assert labels["task_list"] == "TASK一覧(直近20)"
    assert labels["continue_task"] == "承認待ちTASK"
    assert labels["new_task"] == "新規TASK開始"


def test_menu_action_mapping_for_new_task_buttons() -> None:
    assert menu_action_from_text("TASK一覧(直近20)") == "task_list"
    assert menu_action_from_text("承認待ちTASK") == "continue_task"
    assert menu_action_from_text("新規TASK開始") == "new_task"
    assert menu_action_from_text("TASKの進め方") == "task_guide"


def test_menu_action_mapping_for_legacy_buttons() -> None:
    assert menu_action_from_text("新規タスク作成") == "new_task"
    assert menu_action_from_text("使い方") == "task_guide"


def test_task_list_text_empty_message() -> None:
    text = task_list_text(items=[], lang="ja")
    assert "TASK履歴はまだありません" in text


def test_pending_task_text_contains_approve_hint() -> None:
    text = pending_task_text(
        items=[
            {
                "plan_id": "pln_abc123",
                "short_token": "Abc12345",
                "risk_level": "LOW",
                "risk_score": "10",
                "expires_at": "2026-02-26T10:00:00+00:00",
            }
        ],
        lang="ja",
    )
    assert "/approve pln_abc123 Abc12345" in text
