# Q CodeAnzenn MVP

Telegram-operated safety governance assistant.

## Quick Desktop Setup
Use one of these local setup entrypoints after download:

- macOS (double click):
  - `scripts/setup_macos.command`
  - startup prompt lets user choose `日本語` or `English`
  - after setup, bot starts automatically in the same window
  - if same-folder bot is already running, setup auto-restarts it
- Windows (PowerShell):
  - `powershell -ExecutionPolicy Bypass -File scripts\\setup_windows.ps1`

What the setup wizard does:
- Asks Telegram bot token first (to prevent wrong-bot testing confusion)
- Optionally auto-detects Telegram `user_id` from `/start` via Bot API `getUpdates`
- Selects `engine.mode` in `config/policy.yaml`
- Sets `users.allowlist_user_ids`
- Sets `instance_id` (default: `default`) for multi-bot isolation
- Stores `telegram_bot_token` in OS credential store (`qcodeanzenn.<instance_id>`)
- If `codex_api` mode, also stores `codex_api_key`
- Checks subscription login state (`codex login status` / `claude auth status`)
- Saves UI language (`ui.language`) and reflects it in Telegram in-chat menu labels

Optional:
- `QCA_SETUP_AUTOSTART=N` to skip auto-start after setup

## Run
1. Install dependencies:
   - `pip install -r requirements.txt`
2. Choose planner engine in `config/policy.yaml` (`engine.mode`):
   - `codex_api`
   - `codex_subscription` (Codex CLI login session)
   - `claude_subscription` (Claude CLI auth session)
3. Set OS credential store entries under service:
   - `qcodeanzenn` for `instance_id=default`
   - `qcodeanzenn.<instance_id>` for non-default instances
   - Always required: `telegram_bot_token`
   - Required only for `engine.mode=codex_api`: `codex_api_key`
4. For subscription modes, ensure CLI auth is completed in the same OS account:
   - `codex login` (for `codex_subscription`)
   - `claude auth` (for `claude_subscription`)
5. Update allowlist in `config/policy.yaml` (`users.allowlist_user_ids`).
6. Start:
   - Default instance: `python -m src.main`
   - Named instance: `python -m src.main --instance-id mybot2`

## Multi-Bot Quick Flow (macOS/Windows)
1. Run setup once per bot token and choose a different `instance_id` each time.
2. Each instance stores secrets separately:
   - `qcodeanzenn` (default)
   - `qcodeanzenn.<instance_id>` (non-default)
3. Start one process per instance:
   - `python -m src.main --instance-id default`
   - `python -m src.main --instance-id mybot2`

## Security Guarantees (MVP)
- No execution before `/approve <plan_id> <short_token>`
- Fixed safe ops only: `list_dir/read_file/create_file/patch_file`
- Outside-allowed path access rejected
- JSONL hash-chain + HTML report persisted for executed plans

## Engine Notes
- Subscription mode still keeps execution safety gates unchanged.
- Planner generation is engine-switched only; executor behavior remains fixed and policy-guarded.
