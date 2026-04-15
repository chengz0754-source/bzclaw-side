# SellerSprite Current-Stage Closure Contract

> Repo role freeze on `2026-04-15`: `E:\bzclaw-side` is the Machine B business
> state host. It is not an online execution bus, not a worker host, and not
> the A-side control plane. The frozen state-sync contract lives at
> `docs/state_sync_contract_current.md`.

## Repo Role Freeze

- A `bzclaw`: only control plane, approval plane, dispatch truth, and final
  verification owner
- B `amazon-selection-automation`: execution sidecar, local model runtime,
  Playwright, receipts, and runtime artifacts
- B `bzclaw-side`: business state host for truth-pack, board, current-state,
  and owner writeback
- Active truth-pack host: `reports/sellersprite_truth_pack_current.json`
- Active board host: `reports/selection/MASTER_PROGRESS_BOARD__20260412.csv`
- Active current-state hosts:
  - `README.md`
  - `reports/latest_sellersprite_stage_status.json`
- Active owner writeback hosts:
  - `templates/owner_manual_writeback/02__SELLERSPRITE_OWNER_STAGE_WRITEBACK_PACKET__20260413.csv`
  - `reports/latest_sellersprite_owner_handoff.json`
  - `reports/latest_sellersprite_owner_writeback_export.json`

## Candidate Sync Layer

Automated candidate ingest is frozen to reviewable staging roots only:

- `docs/truth_pack/candidates/`
- `reports/board/candidates/`
- `docs/current_state/candidates/`

Those roots accept candidate truth objects only. They do not replace the active
hosts above, and they must not become runtime drop zones.

Standardized Machine B receipts, manifests, and run summaries may appear only
as provenance refs inside candidate metadata. Raw runtime logs, Playwright
artifacts, queue traffic, and secrets still stay out of git truth.

This file is a deterministic current-state host rendered by `scripts/run_sellersprite_stage_closure.py`.

## Current Verdict

- SellerSprite current-stage closure = `FLOW_CLOSED`.
- `flow_closed = true`
- `artifact_depth_reconciled = true`
- `hardening_debt_blocking = false`
- `post_stage_open_debt_present = true`
- `current_stage_closed = true`
- `next_stage_required = true`
- overall legal wording = `SELLERSPRITE_FLOW_CLOSED__BUSINESS_NOT_PROMOTED`

## Current Git Truth

- `P0` shared continuity remains `NON_BLOCKING_HARDENING_DEBT`.
- `T11 / T12` artifact-depth is reconciled and remains the canonical file-backed T01 reference pair.
- `T01`, `T02`, `T03`, and `T04` are SellerSprite line-level `FLOW_CLOSED` lines.
- `T02 / T03 / T04` remain `POST_STAGE_OPEN_DEBT`, but that debt does not reopen current-stage closure.
- Owner-side manual writeback fields remain outside the current-stage closure gate.

## Machine Status Host

- latest machine-readable status: `reports/latest_sellersprite_stage_status.json`
- latest machine-readable truth pack: `reports/sellersprite_truth_pack_current.json`
- artifact evidence mode for the latest evaluation: `truth_pack`
- physical progress-board host in this workspace: `reports/selection/MASTER_PROGRESS_BOARD__20260412.csv`

## Current Board Snapshot

- `P1` = `CURRENT_STAGE_FLOW_CLOSED__STABILITY_CONFIRMED__NEXT_STAGE_OWNER_PROMOTION_PENDING`
- `P2` = `CURRENT_STAGE_FLOW_CLOSED__REUSABLE_LINE__POST_STAGE_OPEN_DEBT_TRACKED`
- `P3` = `CURRENT_STAGE_FLOW_CLOSED__REUSABLE_LINE__POST_STAGE_OPEN_DEBT_TRACKED`
- `P4` = `CURRENT_STAGE_FLOW_CLOSED__REUSABLE_LINE__POST_STAGE_OPEN_DEBT_TRACKED`

## Next-Stage Boundary

- `BUSINESS_PROMOTED` belongs to the next-stage owner/business flow.
- Owner-side manual writeback starts after current-stage flow closure.
- If promotion work is needed, move forward from current `HOLD` candidate rows without reopening current-stage SellerSprite continuity.
