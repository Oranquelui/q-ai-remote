"""HTML report generator for execution audit."""

from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.core.executor import ExecutionResult
from src.models.plan import Plan


@dataclass(frozen=True)
class ReportArtifact:
    path: Path


class ReportBuilder:
    def __init__(self, out_dir: Path) -> None:
        self._out_dir = out_dir
        self._out_dir.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        plan: Plan,
        result: ExecutionResult,
        jsonl_path: Path,
        diff_path: Optional[Path],
    ) -> ReportArtifact:
        out_path = self._out_dir / f"{plan.plan_id}.html"

        ops_rows = "\n".join(
            [
                "<tr>"
                f"<td>{html.escape(op.op_id)}</td>"
                f"<td>{html.escape(op.op_type)}</td>"
                f"<td>{html.escape(op.path)}</td>"
                f"<td>{html.escape(op.status)}</td>"
                f"<td>{html.escape(op.summary)}</td>"
                "</tr>"
                for op in result.op_summaries
            ]
        )

        diff_ref = html.escape(str(diff_path)) if diff_path else "(no write ops)"
        html_doc = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Q CodeAnzenn Report {html.escape(plan.plan_id)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; margin: 24px; color: #111; }}
    h1, h2 {{ margin-bottom: 8px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 8px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f6f6f6; }}
    code {{ background: #f3f3f3; padding: 2px 4px; }}
  </style>
</head>
<body>
  <h1>Q CodeAnzenn Execution Report</h1>
  <h2>Summary</h2>
  <p><strong>Plan ID:</strong> {html.escape(plan.plan_id)}</p>
  <p><strong>Status:</strong> {html.escape(result.status)}</p>
  <p><strong>Risk:</strong> {html.escape(plan.risk.level.value)} ({plan.risk.score})</p>
  <p><strong>Duration:</strong> {result.duration_ms} ms</p>
  <p><strong>Write Ops:</strong> {result.write_op_count}</p>

  <h2>Policy Snapshot</h2>
  <p><strong>Policy ID:</strong> {html.escape(plan.policy_snapshot.policy_id)}</p>
  <p><strong>Allowed Prefixes:</strong> {html.escape(', '.join(plan.policy_snapshot.allowed_path_prefixes))}</p>

  <h2>Operations</h2>
  <table>
    <thead>
      <tr><th>op_id</th><th>type</th><th>path</th><th>status</th><th>summary</th></tr>
    </thead>
    <tbody>
      {ops_rows}
    </tbody>
  </table>

  <h2>Artifacts</h2>
  <p><strong>JSONL:</strong> <code>{html.escape(str(jsonl_path))}</code></p>
  <p><strong>Diff:</strong> <code>{diff_ref}</code></p>
</body>
</html>
"""
        out_path.write_text(html_doc, encoding="utf-8")
        return ReportArtifact(path=out_path)
