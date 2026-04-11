# Nightly Run Acceptance Report

## Scope

- Date: `2026-04-07`
- Repo root: `E:\选品文件夹\amazon-selection-automation`
- Acceptance batch: `20260407_p10_acceptance`
- Runner: `python scripts/run_nightly_selection_acceptance.py --batch-id 20260407_p10_acceptance`

## Verdict

- Acceptance result: `NOT PASSED`
- Runtime status: `HOLD`
- Final reason codes:
  - `BLOCKED_BY_UPSTREAM_CHAIN__STEP2_ALL_RAW_RUNS_BLOCKED`
  - `SIF_AUTH_REQUIRED`
  - `BLOCKED_BY_SIF_OR_POOL_ALIGNMENT__CANDIDATE_POOL_NOT_READY__SIF_DETAIL_SURFACE_NOT_COLLECTED__SIF_SEARCH_SURFACE_NOT_COLLECTED`
  - `BLOCKED_BY_SIF_OR_POOL_ALIGNMENT__CANDIDATE_POOL_NOT_READY__SIF_AUTH_REQUIRED`

This run is a real end-to-end dry-run, not a mocked acceptance. The chain assembled a full archive-shaped package and emitted standards-aligned outputs, but it did not pass business acceptance because STEP2 and SIF live collection are still blocked upstream.

## What Was Executed

The acceptance runner copied the current working inputs into `01_consumed_inputs/` and then executed these repo-local stages in order:

1. `scripts/run_selection_direction_batch.py`
2. `scripts/build_candidate_pool.py`
3. `scripts/collect_sif_detail_surface.py`
4. `scripts/collect_sif_search_surface.py`
5. `scripts/build_sif_enrichment_daytime_pack.py`

Observed step results for batch `20260407_p10_acceptance`:

- `direction_batch`: `HOLD`, reason `BLOCKED_BY_UPSTREAM_CHAIN__STEP2_ALL_RAW_RUNS_BLOCKED`
- `candidate_pool`: `HOLD`, reason `BLOCKED_BY_UPSTREAM_CHAIN__STEP2_ALL_RAW_RUNS_BLOCKED`
- `sif_detail_probe`: `HOLD`, reason `SIF_AUTH_REQUIRED`
- `sif_search_probe`: `HOLD`, reason `SIF_AUTH_REQUIRED`
- `sif_enrichment`: `HOLD`, reason `BLOCKED_BY_SIF_OR_POOL_ALIGNMENT__...`

## Archive And Output Verification

The batch produced a full archive-shaped package at:

- `outputs/selection_runs/20260407_p10_acceptance/`

Verified archive layers:

- `00_run_summary.md`
- `01_consumed_inputs/`
- `02_generated_outputs/`
- `03_logs/`

Verified required outputs under `02_generated_outputs/`:

- `batch_queue_status.csv`
- `batch_run_summary.json`
- `03_候选市场与候选品初筛池.csv`
- `60_候选样品池.csv`
- `50_SIF流量结构补强.csv`
- `51_SIF关键词价值补强.csv`
- `52_SIF广告结构补强.csv`
- `53_SIF补强下推结果.csv`
- `61_待供应链核利清单.csv`

## Canonical Checks

- Candidate pool and SIF outputs aligned by primary key:
  - `50_aligned = True`
  - `51_aligned = True`
  - `52_aligned = True`
  - `53_aligned = True`
- `61_待供应链核利清单.csv` remained header-only in this run:
  - `daytime_row_count = 0`
- Manual-only fields remained unpolluted:
  - `合规`
  - `改良点`
  - `最终解释`
  - `利润核价`
  - `最终 Go/No-Go`

## Current Automation Boundary

Nightly automation can already do these parts deterministically:

- read current `00/01/02/03`
- assemble a full archive-shaped dry-run package
- trigger direction batch orchestration
- build runtime `03` and `60`
- emit standards-aligned `50/51/52/53/61`
- preserve blocked truth instead of fabricating PASS rows

Nightly automation cannot yet claim acceptance PASS because these links are still not live-complete:

- SellerSprite STEP2 keyword evidence chain
- SIF authenticated detail/search collection
- Step 5 to Step 6 progression with real PASS rows

## Acceptance Decision

The repository is `ready for E2E dry-run`, but it is **not** yet `accepted for nightly autonomous success`.

Required follow-up before acceptance can pass:

1. Restore SellerSprite STEP2 live collection so `22_关键词证据词池下推结果.csv` becomes real instead of blocked.
2. Restore reusable SIF authentication so detail/search surfaces return live metrics instead of `SIF_AUTH_REQUIRED`.
3. Re-run `scripts/run_nightly_selection_acceptance.py` with a new batch id and confirm `53` contains real Step 5 decisions and `61` contains real daytime handoff rows.

## Related Docs

- `reports/nightly_run_operator_runbook.md`
- `reports/nightly_run_failure_recovery_guide.md`
- `reports/中文CSV运行归档规则.md`
