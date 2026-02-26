# Q CodeAnzenn MVP Requirements (Frozen)

## 1. Purpose
Q CodeAnzenn provides a Telegram-operated safety-governed assistant that can propose and execute constrained workspace edits only after explicit user approval.

## 2. Non-goals
- No cloud multi-tenant runtime in MVP
- No web dashboard UI
- No arbitrary command execution
- No executor-side network actions
- No local LLM execution

## 3. User Flow
1. User sends `/plan <text>` on Telegram.
2. System generates `Plan + Risk` and stores plan in `PENDING_APPROVAL`.
3. System returns summary (`plan_id`, `short_token`, ops, risk, expiry).
4. No side effects occur before `/approve <plan_id> <short_token>`.
5. On valid approval, fixed safe ops execute.
6. System stores `diff + JSONL(hash-chain) + HTML` and exposes paths via `/logs <plan_id>`.

## 4. Prohibitions (Hard)
- Access outside allowed workspace prefixes is rejected 100%.
- Symlink, junction, UNC, and absolute path usage is rejected.
- Operations limited to `list_dir`, `read_file`, `create_file`, `patch_file` only.
- No shell command execution path exists.
- No executor network operation path exists.
- Telegram responses must not include raw file body by default.

## 5. Security and Secrets
- Engine uses Codex API only.
- Secrets are read from OS credential store only:
  - macOS: Keychain
  - Windows: Credential Manager
- Secret values are never logged or returned to Telegram.

## 6. Acceptance Criteria
- `/plan` never mutates files.
- `/approve` requires exactly two arguments: `<plan_id> <short_token>`.
- Any path policy violation rejects before execution.
- Every write plan execution emits local diff + JSONL + HTML artifacts.
- Audit JSONL includes hash-chain fields for tamper evidence.
- Works on macOS 13+ and Windows 11+ (x64).
