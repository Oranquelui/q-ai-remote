# 10-Business-Day Implementation Plan

## Day 1
- Scope freeze and requirement sign-off
- Deliverables: `docs/mvp_requirements.md`
- Done when: mandatory sections approved

## Day 2
- Repository structure and policy baseline
- Deliverables: `docs/repo_tree.md`, `config/policy.yaml`
- Done when: command/op/prohibition policy schema validated

## Day 3
- Plan contract and schema export
- Deliverables: `src/models/plan.py`, `scripts/export_plan_schema.py`, `schemas/plan.schema.json`
- Done when: model validators reject absolute/UNC paths and schema export is deterministic

## Day 4
- Secrets and DB foundation
- Deliverables: `src/secrets/*`, `db/schema.sql`
- Done when: OS credential adapters read key and DB initializes cleanly

## Day 5
- Path guard implementation
- Deliverables: `src/security/path_guard.py`
- Done when: symlink/junction/UNC/outside-prefix tests pass

## Day 6
- Planner + risk + `/plan`
- Deliverables: `src/core/planner.py`, `src/security/risk_engine.py`, `src/bot/handlers_plan.py`
- Done when: `/plan` returns fixed short format and causes zero side effects

## Day 7
- Approval flow
- Deliverables: `src/core/approval_service.py`, `src/bot/handlers_approval_status.py`
- Done when: `/approve <plan_id> <short_token>` only path to execution

## Day 8
- Executor and diff
- Deliverables: `src/core/executor.py`, `src/core/diff_service.py`
- Done when: only 4 ops execute and diff is generated for writes

## Day 9
- Audit trail and logs endpoint
- Deliverables: `src/audit/audit_logger.py`, `src/audit/report_builder.py`, `src/bot/handlers_logs.py`
- Done when: JSONL hash-chain and HTML report generated per execution

## Day 10
- Security regression and demo
- Deliverables: `tests/security/test_regressions.py`, `docs/demo_script.md`
- Done when: all security regression items pass and Telegram demo is reproducible

## Post-Plan Patch (2026-02-26)
- setup UX adjustment for first-run onboarding:
  - prompt `telegram_bot_token` before mode/allowlist input
  - add optional `user_id` auto-detection via Bot API `getUpdates`
  - keep `codex_api_key` prompt conditional after mode selection
- Retest focus:
  - clean reset -> setup flow
  - wrong-token prevention
  - `/start` response on selected bot
