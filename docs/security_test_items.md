# Security Test Items (MVP)

## 1) Allowed Paths breakout resistance
- Case AP-01: `../` traversal in operation path must be rejected.
- Case AP-02: absolute path (`/etc/passwd`, `C:\\Windows\\...`) must be rejected.
- Case AP-03: UNC path (`\\server\\share\\file`) must be rejected.
- Case AP-04: symlink target escaping allowed prefix must be rejected.
- Case AP-05: Windows junction reparse point escaping allowed prefix must be rejected.

## 2) No execution before approval
- Case PA-01: `/plan` with write ops must not modify filesystem.
- Case PA-02: `/approve` missing token must reject.
- Case PA-03: `/approve` wrong token must reject.
- Case PA-04: expired plan token must reject.

## 3) Secret leakage prevention
- Case SL-01: logs must never contain API key value.
- Case SL-02: Telegram responses must not include secret values.
- Case SL-03: exception traces must redact secret-bearing config fields.

## 4) Rate limit enforcement
- Case RL-01: command burst over threshold returns rate-limit error.
- Case RL-02: approve burst over threshold blocks until window reset.
- Case RL-03: limits are user-specific (one user does not throttle another).

## 5) Fixed-op and no-command/no-network guarantees
- Case OP-01: non-listed operation type is rejected.
- Case OP-02: shell-like payload (`!ls`, `rm -rf`) is treated as invalid plan input.
- Case OP-03: executor code path has no HTTP client usage.
