# Q AI Remote v0.9.8 Release Notes

Release date: 2026-03-28

## Summary

`v0.9.8` is a foundation release for the async job runner roadmap.

This release does not replace the current synchronous approval flow yet. Instead, it lands the internal contracts needed to move from a single approval-execute path toward queued, resumable, and schedulable runs.

## Highlights

### 1. Async run-state contract

Added a dedicated run-state model for background execution:

- `QUEUED`
- `RUNNING`
- `WAITING_INPUT`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

This includes:

- explicit transition validation
- terminal-state detection
- test coverage for allowed and rejected transitions

### 2. Persisted run records

Added runtime/database support for persisted run records so future async runs can be tracked safely across process boundaries.

This includes:

- schema support for run records
- database-layer persistence
- runtime integration points
- focused tests for runtime and DB behavior

## Why This Matters

These changes establish the first two building blocks for:

- queue workers
- cancel / retry / resume controls
- scheduled jobs
- morning review summaries

They are intentionally low-risk infrastructure steps that preserve the current safety model.

## What Did Not Change

The current execution model is still:

- `Plan + Risk`
- explicit approval
- synchronous safe execution

This release does not introduce unrestricted background execution, arbitrary shell access, or network-enabled executor behavior.

## Next Planned Work

- queue worker foundation
- run controls (`cancel`, `retry`, `resume`)
- schedule jobs
- morning review flow

## Verification

Validated with focused checks:

```bash
python3 -m py_compile src/core/run_state.py tests/core/test_run_state.py tests/core/test_runtime_run_records.py tests/db/test_run_records.py
python3 -m pytest -q tests/core/test_run_state.py tests/core/test_runtime_run_records.py tests/db/test_run_records.py
```
