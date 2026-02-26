"""Telegram response templates (no file body output)."""

from __future__ import annotations

from src.core.executor import ExecutionResult
from src.models.plan import Plan


def start_text(lang: str = "ja") -> str:
    if (lang or "ja").lower() == "en":
        return (
            "Q CodeAnzenn MVP is online.\n"
            "Mode: Safety Governance\n"
            "Commands: /start /policy /task /plan /approve /reject /status /logs\n"
            "Rule: No execution before explicit /approve.\n"
            "Input guide: send /plan <request>, tap Create Task, or just send free text."
        )
    return (
        "Q CodeAnzenn MVP が起動中です。\n"
        "モード: 安全ガバナンス\n"
        "コマンド: /start /policy /task /plan /approve /reject /status /logs\n"
        "ルール: /approve されるまで実行しません。\n"
        "入力ガイド: /task <依頼内容>、新規TASK開始、または自由文入力が使えます。"
    )


def policy_text(lang: str = "ja") -> str:
    if (lang or "ja").lower() == "en":
        return (
            "Policy v1\n"
            "- Allowed ops: list_dir, read_file, create_file, patch_file\n"
            "- Prohibited: arbitrary command execution, network operations, absolute paths/UNC/symlink/junction\n"
            "- Planning engine: switch by policy.yaml engine.mode\n"
            "- Write operations always require approval\n"
            "- Approval format: /approve <plan_id> <short_token>\n"
            "- Response policy: file body is hidden (summary and diff summary only)"
        )
    return (
        "ポリシー v1\n"
        "- 許可操作: list_dir, read_file, create_file, patch_file\n"
        "- 禁止: 任意コマンド実行、ネットワーク操作、絶対パス/UNC/symlink/junction\n"
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
        f"status: {final_status}\n"
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
        f"status: {result.status}\n"
        f"ops: {len(result.op_summaries)}\n"
        f"write_ops: {result.write_op_count}\n"
        f"duration_ms: {result.duration_ms}\n"
        f"diff_summary: {diff_summary}"
    )


def menu_help_text(lang: str = "ja") -> str:
    if (lang or "ja").lower() == "en":
        return (
            "Menu actions\n"
            "- TASK List (20): show your recent plan IDs\n"
            "- Pending TASKs: show approvable plans with /approve format\n"
            "- Start New TASK: next single message is processed as /task\n"
            "- TASK Guide: usage and approval flow\n"
            "- Safety Policy: show current safety policy\n"
            "- Engine/Runtime: /status (runtime) or /status <plan_id>\n"
            "- Audit Logs: /logs <plan_id>\n"
            "- Free text is also accepted and routed to /task automatically\n"
            "- Direct commands are also available: /start /policy /task /plan /approve /reject /status /logs"
        )
    return (
        "メニュー操作\n"
        "- TASK一覧(直近20): あなたの最近のplan_idを表示\n"
        "- 承認待ちTASK: /approve 可能な計画を表示\n"
        "- 新規TASK開始: 次の1メッセージを /task として処理\n"
        "- TASKの進め方: 操作手順と承認フローを表示\n"
        "- 安全ポリシー: 現在の安全ポリシーを表示\n"
        "- 接続/稼働状態: /status（稼働状態）または /status <plan_id>\n"
        "- 監査ログ: /logs <plan_id>\n"
        "- 自由文も受け付け、/task として自動処理します\n"
        "- 直接コマンドも利用可能: /start /policy /task /plan /approve /reject /status /logs"
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


def free_text_routed_text(lang: str = "ja") -> str:
    if (lang or "ja").lower() == "en":
        return (
            "Free text received.\n"
            "Routing it to /task flow (Plan+Risk only, no execution)."
        )
    return (
        "自由文を受け付けました。\n"
        "/task フロー（Plan+Riskのみ、実行なし）として処理します。"
    )


def task_list_text(items: list[dict[str, str]], lang: str = "ja") -> str:
    if not items:
        if (lang or "ja").lower() == "en":
            return "No TASK history yet.\nSend free text or run /task <request>."
        return "TASK履歴はまだありません。\n自由文または /task <依頼内容> で開始してください。"

    lines: list[str] = []
    if (lang or "ja").lower() == "en":
        lines.append("TASK List (latest)")
        for item in items:
            lines.append(
                f"- {item['plan_id']} | {item['status']} | {item['risk_level']}({item['risk_score']}) | /status {item['plan_id']}"
            )
    else:
        lines.append("TASK一覧（直近）")
        for item in items:
            lines.append(
                f"- {item['plan_id']} | {item['status']} | {item['risk_level']}({item['risk_score']}) | /status {item['plan_id']}"
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
    else:
        lines.append("承認待ちTASK")
        for item in items:
            lines.append(
                f"- {item['plan_id']} | {item['risk_level']}({item['risk_score']}) | expires: {item['expires_at']}"
            )
            lines.append(f"  /approve {item['plan_id']} {item['short_token']}")
            lines.append(f"  /reject {item['plan_id']}")
    return "\n".join(lines)
