# Nightly Run Operator Runbook

## Purpose

This runbook is the operator entry point for the repo-local nightly acceptance dry-run. It validates the end-to-end chain without overwriting the current working inputs and assembles a full archive-shaped package under `outputs/selection_runs/<batch_id>/`.

## Preconditions

Run from the repo root only:

- `E:\选品文件夹\amazon-selection-automation`

Before starting a nightly acceptance run, confirm:

1. Canonical standards still come from `templates/selection_canonical_standards/`.
2. Current working inputs are in `inputs/selection_run_current/`.
3. Manual-only fields are still left for daytime:
   - `合规`
   - `改良点`
   - `最终解释`
   - `利润核价`
   - `最终 Go/No-Go`
4. SellerSprite and SIF auth truth is known. If auth is not ready, the run is still allowed, but it must fail closed.

## Standard Command

```powershell
.\.venv\Scripts\python.exe scripts\run_nightly_selection_acceptance.py --batch-id 20260407_p10_acceptance
```

Optional subset run:

```powershell
.\.venv\Scripts\python.exe scripts\run_nightly_selection_acceptance.py --batch-id 20260407_p10_acceptance_row1 --row-indices 1
```

Rules for `batch_id`:

- use a new `batch_id` every time
- never reuse an existing archive directory
- do not point outputs outside the repo root

## What The Runner Does

`scripts/run_nightly_selection_acceptance.py` performs a non-destructive acceptance flow:

1. Copies current `inputs/selection_run_current/` into `outputs/selection_runs/<batch_id>/01_consumed_inputs/`.
2. Runs direction orchestration into `02_generated_outputs/`.
3. Builds runtime candidate-pool outputs `03` and `60`.
4. Probes SIF detail and search surfaces against candidate row 1.
5. Builds `50/51/52/53/61`.
6. Copies current acceptance logs into `03_logs/`.
7. Writes `00_run_summary.md` plus `03_logs/nightly_acceptance_summary.json`.

This runner does **not** clear `inputs/selection_run_current/`.

## Expected Archive Shape

Every acceptance batch must land here:

- `outputs/selection_runs/<batch_id>/00_run_summary.md`
- `outputs/selection_runs/<batch_id>/01_consumed_inputs/`
- `outputs/selection_runs/<batch_id>/02_generated_outputs/`
- `outputs/selection_runs/<batch_id>/03_logs/`

Minimum expected generated outputs:

- `batch_queue_status.csv`
- `batch_run_summary.json`
- `03_候选市场与候选品初筛池.csv`
- `60_候选样品池.csv`
- `50_SIF流量结构补强.csv`
- `51_SIF关键词价值补强.csv`
- `52_SIF广告结构补强.csv`
- `53_SIF补强下推结果.csv`
- `61_待供应链核利清单.csv`

## How To Read The Result

- `PASS`: the chain and acceptance gate both passed.
- `HOLD`: the run is structurally complete, but upstream truth or missing live data blocks business acceptance.
- `FAIL`: a required output, required path, or archive layer is missing or broken.

Key log file:

- `outputs/selection_runs/<batch_id>/03_logs/nightly_acceptance_summary.json`

Key operator-readable summary:

- `outputs/selection_runs/<batch_id>/00_run_summary.md`

## Daytime Manual Boundary

Nightly automation may prepare the package, but daytime manual work still owns:

1. Compliance confirmation in `02_账号与合规预检查.csv`.
2. Supplier profit check and cost input.
3. Final human interpretation.
4. Final `Go/No-Go`.

If `61_待供应链核利清单.csv` is header-only, do not invent daytime rows. Treat that as a real blocked outcome.

## When To Use The Real Archive Script

Use `scripts/archive_selection_run_io.py` only when you intentionally want to move the current working inputs into a final consumed archive after a completed operator-approved run.

Use `scripts/run_nightly_selection_acceptance.py` when you need:

- a nightly dry-run
- a non-destructive acceptance package
- a truth-preserving readiness check before claiming the system can nightly-run end to end

## Current Repo Truth On 2026-04-07

The validated acceptance command currently finishes as:

- status: `HOLD`
- main blockers:
  - `BLOCKED_BY_UPSTREAM_CHAIN__STEP2_ALL_RAW_RUNS_BLOCKED`
  - `SIF_AUTH_REQUIRED`
  - `BLOCKED_BY_SIF_OR_POOL_ALIGNMENT`

So the nightly runner is operational, but the business chain is not yet accepted as fully autonomous.
