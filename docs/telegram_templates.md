# Telegram Response Templates (MVP)

## /start
```text
Q CodeAnzenn MVP is online.
Mode: Safety Governance
Commands: /start /policy /plan /approve /reject /status /logs
Rule: No execution before explicit approval.
```

## /policy
```text
Policy v1
- Allowed ops: list_dir, read_file, create_file, patch_file
- Blocked: command execution, network actions, absolute/UNC/symlink/junction paths
- Approval required for every write plan
- /approve format: /approve <plan_id> <short_token>
- Output policy: file body is hidden; summary and diff summary only
```

## /plan <text>
```text
Plan Created
plan_id: {plan_id}
short_token: {short_token}
status: PENDING_APPROVAL
risk: {risk_level} ({risk_score})
ops: {ops_count} (read={read_count}, write={write_count})
targets: {target_summary}
expires_at: {expires_at}
Next: /approve {plan_id} {short_token} OR /reject {plan_id}
```

## /approve <plan_id> <short_token>
```text
Approval Accepted
plan_id: {plan_id}
status: APPROVED -> EXECUTING
note: Policy checks are re-evaluated before execution.
```

## /logs <plan_id>
```text
Execution Logs
plan_id: {plan_id}
status: {final_status}
diff_summary: {diff_summary}
jsonl: {jsonl_path}
html: {html_path}
```
