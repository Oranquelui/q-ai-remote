# Telegram Demo Script (MVP)

1. Send `/start`
- Confirm command list and no-execution-before-approve policy.

2. Send `/policy`
- Confirm blocked actions and approval format `/approve <plan_id> <short_token>`.

3. Send `/plan docs/README.mdにQ-Guard概要を追加`
- Confirm response includes `plan_id`, `short_token`, `risk`, `ops`, `expires_at`.
- Confirm filesystem unchanged at this point.

4. Send `/approve <plan_id> <short_token>`
- Confirm status transition and execution summary.

5. Send `/status <plan_id>`
- Confirm `EXECUTED`.

6. Send `/logs <plan_id>`
- Confirm JSONL and HTML paths are returned.
- Open artifacts locally and verify hash-chain fields in JSONL.

7. Negative test
- Send `/plan ../../.ssh/config を読む`
- Confirm immediate rejection by path policy.
