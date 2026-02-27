"""Telegram response templates (no file body output)."""

from __future__ import annotations

from src.core.executor import ExecutionResult
from src.models.plan import Plan


def _status_label(status: str, lang: str = "ja") -> str:
    s = (status or "").upper()
    if (lang or "ja").lower() == "en":
        return {
            "PENDING_APPROVAL": "Waiting approval",
            "APPROVED": "Approved",
            "EXECUTING": "Executing",
            "EXECUTED": "Completed",
            "FAILED": "Failed",
            "REJECTED": "Rejected",
            "EXPIRED": "Expired",
        }.get(s, s)
    return {
        "PENDING_APPROVAL": "承認待ち",
        "APPROVED": "承認済み",
        "EXECUTING": "実行中",
        "EXECUTED": "完了",
        "FAILED": "失敗",
        "REJECTED": "破棄",
        "EXPIRED": "期限切れ",
    }.get(s, s)


def start_text(lang: str = "ja") -> str:
    if (lang or "ja").lower() == "en":
        return (
            "Q AI Remote is ready.\n"
            "Send plain text for questions.\n"
            "Use /task for file/code changes.\n"
            "After plan creation, use the on-screen buttons to run or cancel."
        )
    return (
        "Q AI Remote を開始しました。\n"
        "自由文はそのまま送信できます。\n"
        "ファイル/コード変更は /task を使います。\n"
        "Plan作成後は画面ボタンで実行または破棄します。"
    )


def policy_text(lang: str = "ja") -> str:
    if (lang or "ja").lower() == "en":
        return (
            "Policy v1\n"
            "- Allowed ops: list_dir, read_file, create_file, patch_file\n"
            "- Prohibited (execution ops): arbitrary command execution, network operations, absolute paths/UNC/symlink/junction\n"
            "- Chat/free-question answers may use live web lookup depending on engine/runtime availability\n"
            "- Planning engine: switch by policy.yaml engine.mode\n"
            "- Write operations always require approval\n"
            "- Approval format: /approve <plan_id> <short_token>\n"
            "- Response policy: file body is hidden (summary and diff summary only)"
        )
    return (
        "ポリシー v1\n"
        "- 許可操作: list_dir, read_file, create_file, patch_file\n"
        "- 禁止（実行オペレーション）: 任意コマンド実行、ネットワーク操作、絶対パス/UNC/symlink/junction\n"
        "- 自由質問の回答は、エンジン/実行環境で可能な場合にライブWeb参照を行うことがあります\n"
        "- 生成エンジン: policy.yaml の engine.mode で切替\n"
        "- 書き込み系は必ず承認が必要\n"
        "- 承認形式: /approve <plan_id> <short_token>\n"
        "- 返信方針: ファイル本文は非表示（要約と差分サマリのみ）"
    )


def planning_in_progress_text(lang: str = "ja") -> str:
    if (lang or "ja").lower() == "en":
        return (
            "Creating Plan+Risk now.\n"
            "This usually takes 20-90 seconds depending on engine latency.\n"
            "Please wait for the result message."
        )
    return (
        "Plan+Risk を生成中です。\n"
        "エンジン応答時間により 20-90秒ほどかかる場合があります。\n"
        "完了メッセージが届くまでお待ちください。"
    )


def chat_in_progress_text(lang: str = "ja") -> str:
    if (lang or "ja").lower() == "en":
        return "Generating chat answer..."
    return "回答を生成中です..."


def plan_text(plan: Plan) -> str:
    read_count = sum(1 for op in plan.ops if op.type in ("list_dir", "read_file"))
    write_count = len(plan.ops) - read_count
    targets = sorted({op.path for op in plan.ops})
    target_summary = ", ".join(targets[:5])
    if len(targets) > 5:
        target_summary += ", ..."

    return (
        "計画を作成しました\n"
        f"plan_id: {plan.plan_id}\n"
        f"short_token: {plan.short_token}\n"
        "status: PENDING_APPROVAL\n"
        f"risk: {plan.risk.level.value} ({plan.risk.score})\n"
        f"ops: {len(plan.ops)} (read={read_count}, write={write_count})\n"
        f"targets: {target_summary}\n"
        f"expires_at: {plan.expires_at.isoformat()}\n"
        f"次の操作: /approve {plan.plan_id} {plan.short_token} または /reject {plan.plan_id}"
    )


def approved_text(plan_id: str) -> str:
    return (
        "承認を受け付けました\n"
        f"plan_id: {plan_id}\n"
        "status: APPROVED -> EXECUTING\n"
        "注記: 実行前にポリシーを再検証します。"
    )


def logs_text(
    plan_id: str,
    final_status: str,
    diff_summary: str,
    jsonl_path: str,
    html_path: str,
) -> str:
    return (
        "実行ログ\n"
        f"plan_id: {plan_id}\n"
        f"status: {_status_label(final_status, 'ja')} ({final_status})\n"
        f"diff_summary: {diff_summary}\n"
        f"jsonl: {jsonl_path}\n"
        f"html: {html_path}"
    )


def execution_summary_text(result: ExecutionResult) -> str:
    diff_summary = "書き込み操作なし"
    if result.diff_artifact:
        diff_summary = f"patch={result.diff_artifact.path} files={len(result.diff_artifact.summary)}"
    return (
        "実行が完了しました\n"
        f"plan_id: {result.plan_id}\n"
        f"status: {_status_label(result.status, 'ja')} ({result.status})\n"
        f"ops: {len(result.op_summaries)}\n"
        f"write_ops: {result.write_op_count}\n"
        f"duration_ms: {result.duration_ms}\n"
        f"diff_summary: {diff_summary}"
    )


def menu_help_text(lang: str = "ja") -> str:
    if (lang or "ja").lower() == "en":
        return (
            "How to use\n"
            "Ask Freely: send any question.\n"
            "New TASK: send one request to create Plan+Risk.\n"
            "Pending TASKs: execute/reject from buttons.\n"
            "TASK History: check recent plan IDs.\n"
            "Run Logs: open latest executed task log.\n"
            "Optional commands: /task /status /logs"
        )
    return (
        "使い方\n"
        "自由質問: そのまま質問を送信\n"
        "新規TASK: 1メッセージ送信で Plan+Risk 作成\n"
        "承認待ち: ボタンで実行/破棄\n"
        "TASK履歴: 最近の plan_id を確認\n"
        "実行ログ: 最新の実行済みログを表示\n"
        "必要ならコマンド: /task /status /logs"
    )


def runtime_status_text(
    instance_id: str,
    engine_mode: str,
    engine_connectivity: str,
    lang: str = "ja",
) -> str:
    if (lang or "ja").lower() == "en":
        return (
            "Runtime status\n"
            f"instance_id: {instance_id}\n"
            f"engine_mode: {engine_mode}\n"
            f"engine_connectivity: {engine_connectivity}\n"
            "Tip: /status <plan_id> to check a specific plan."
        )
    return (
        "稼働状態\n"
        f"instance_id: {instance_id}\n"
        f"engine_mode: {engine_mode}\n"
        f"engine_connectivity: {engine_connectivity}\n"
        "補足: 個別の計画状態は /status <plan_id> で確認できます。"
    )


def task_list_text(items: list[dict[str, str]], lang: str = "ja") -> str:
    if not items:
        if (lang or "ja").lower() == "en":
            return "No TASK history yet.\nSend free text or run /task <request>."
        return "TASK履歴はまだありません。\n自由文または /task <依頼内容> で開始してください。"

    lines: list[str] = []
    if (lang or "ja").lower() == "en":
        lines.append("TASK List (latest)")
        latest = items[0]
        lines.append(f"Latest: {_status_label(latest['status'], 'en')} ({latest['status']})")
        for item in items:
            lines.append(
                f"- {item['plan_id']} | {_status_label(item['status'], 'en')} ({item['status']}) | {item['risk_level']}({item['risk_score']}) | /status {item['plan_id']}"
            )
    else:
        lines.append("TASK一覧（直近）")
        latest = items[0]
        lines.append(f"最新結果: {_status_label(latest['status'], 'ja')} ({latest['status']})")
        for item in items:
            lines.append(
                f"- {item['plan_id']} | {_status_label(item['status'], 'ja')} ({item['status']}) | {item['risk_level']}({item['risk_score']}) | /status {item['plan_id']}"
            )
    return "\n".join(lines)


def pending_task_text(items: list[dict[str, str]], lang: str = "ja") -> str:
    if not items:
        if (lang or "ja").lower() == "en":
            return "No pending TASKs.\nCreate one with free text or /task <request>."
        return "承認待ちTASKはありません。\n自由文または /task <依頼内容> で新規作成してください。"

    lines: list[str] = []
    if (lang or "ja").lower() == "en":
        lines.append("Pending TASKs")
        for item in items:
            lines.append(
                f"- {item['plan_id']} | {item['risk_level']}({item['risk_score']}) | expires: {item['expires_at']}"
            )
            lines.append(f"  /approve {item['plan_id']} {item['short_token']}")
            lines.append(f"  /reject {item['plan_id']}")
        lines.append("Tip: You can execute/reject from the action buttons.")
    else:
        lines.append("承認待ちTASK")
        for item in items:
            lines.append(
                f"- {item['plan_id']} | {item['risk_level']}({item['risk_score']}) | expires: {item['expires_at']}"
            )
            lines.append(f"  /approve {item['plan_id']} {item['short_token']}")
            lines.append(f"  /reject {item['plan_id']}")
        lines.append("補足: 下のアクションボタンから実行/破棄できます。")
    return "\n".join(lines)
