# CODEX T11/T12 Artifact-Depth Reconciliation Summary (2026-04-13)

## Current Git Truth

- This slice does not reopen runtime by default.
- It only reconciles current `T11 / T12` artifact-depth truth against the actual repo-visible outputs.
- Current canonical T01 line wording remains:
  - `FLOW_CLOSED__BUSINESS_NOT_PROMOTED__STABILITY_CONFIRMED`
- Current canonical overall wording remains:
  - `SELLERSPRITE_FLOW_CLOSED__BUSINESS_NOT_PROMOTED`

## Files Rechecked

- `README.md`
- `reports/MASTER_PROGRESS_BOARD__20260412.csv`
- `reports/CODEX_REPO_TRUTH_REVALIDATION_AFTER_0118_SUMMARY_20260413.md`
- `reports/CODEX_T12_STEP4_TRUTH_RECONCILIATION_AND_STABILIZATION_SUMMARY_20260412.md`
- `reports/CODEX_STEP2_KEYWORD_MINER_SUBMIT_CONTINUITY_SUMMARY_20260412.md`
- `reports/CODEX_T11_T12_STABILITY_AND_PROMOTION_GATE_V3_SUMMARY_20260412.md`
- `scripts/run_t01_market_discovery.py`
- `scripts/build_candidate_pool.py`

## Actual Outputs Rechecked

### T11

- `12_产品样本下推结果.csv`
  - exists
  - parses
  - `row_count = 10`
  - `整体状态 = PASS x 10`
- `22_关键词证据词池下推结果.csv`
  - exists
  - parses
  - `row_count = 20`
  - `整体状态 = HOLD x 20`
- `42_竞品基准下推结果.csv`
  - exists
  - parses
  - `row_count = 10`
  - `整体状态 = PASS x 10`
- `60_候选样品池.csv`
  - exists
  - parses
  - `row_count = 10`
  - `当前下推状态 = HOLD x 10`

### T12

- `12_产品样本下推结果.csv`
  - exists
  - parses
  - `row_count = 10`
  - `整体状态 = PASS x 10`
- `22_关键词证据词池下推结果.csv`
  - exists
  - parses
  - `row_count = 20`
  - `整体状态 = FAIL x 3; HOLD x 17`
- `42_竞品基准下推结果.csv`
  - exists
  - parses
  - `row_count = 5`
  - `整体状态 = HOLD x 5`
- `60_候选样品池.csv`
  - exists
  - parses
  - `row_count = 5`
  - `当前下推状态 = HOLD x 5`

## Latest JSON Check

- Rechecked:
  - `latest_product_build_run.json`
  - `latest_keyword_build_run.json`
  - `latest_benchmark_build_run.json`
  - `latest_run.json`
- Current exact truth:
  - the checked files exist
  - they remain readable as supporting text
  - they are not reliable strict machine-parseable JSON for canonical truth writeback

This means the current highest-priority truth hosts remain:

- landed CSV outputs
- current `README.md`
- current `reports/MASTER_PROGRESS_BOARD__20260412.csv`

## Real Business Differences vs Artifact-Depth Conflicts

### Real Business Differences

- `T11` is stronger than `T12` at the gate-distribution layer:
  - `T11 42 = PASS x 10`
  - `T12 42 = HOLD x 5`
  - `T11 22 = HOLD x 20`
  - `T12 22 = FAIL x 3; HOLD x 17`
  - `T11 60 = HOLD x 10`
  - `T12 60 = HOLD x 5`

These are real line-level business/gate differences and must not be misread as truth-priority conflicts.

### Artifact-Depth / Truth-Priority Conflicts

- Earlier prose on `T12 STEP7 = PARTIAL_REAL_SAMPLE_ONLY` is no longer current truth.
- Earlier prose that let shallower retry wording demote already-landed T12 STEP4/STEP2 packages is no longer current truth.
- The checked actual outputs do not conflict with each other.
- The remaining conflict is host priority only:
  - stale prose can contradict newer file-backed outputs
  - malformed `latest_*.json` can look deep, but they cannot outrank landed CSV packages

## Canonical Rule

- `deeper file-backed truth > later shallower retry prose`
- `CSV / parseable output packages > unstable latest JSON prose`
- `row-count / gate-distribution differences != artifact-depth mismatch`

## Canonical Current Judgment

- `T11`
  - `12 = PASS x 10`
  - `22 = HOLD x 20`
  - `42 = PASS x 10`
  - `60 = HOLD x 10`
- `T12`
  - `12 = PASS x 10`
  - `22 = FAIL x 3; HOLD x 17`
  - `42 = HOLD x 5`
  - `60 = HOLD x 5`
- Closure-layer truth:
  - both lines remain `FLOW_CLOSED`
  - both lines remain `BUSINESS_NOT_PROMOTED`
- Current blocker:
  - `T01_PURE_BUSINESS_HOLD__PROMOTION_NOT_LANDED`

## Minimal Rerun / Rewriteback Decision

- No rerun was needed in this slice.
- The actual file-backed outputs already resolve the current truth-priority conflict.
- This slice only performs repo-visible writeback.

## Repo-Visible Writeback

- `README.md`
- `reports/MASTER_PROGRESS_BOARD__20260412.csv`
- `reports/CODEX_T11_T12_ARTIFACT_DEPTH_RECONCILIATION_SUMMARY_20260413.md`

## Next Exact Slice

- Do not reopen toy batch, T02, T03, or T04.
- Do not reopen generic truth reconciliation unless a new file-backed contradiction appears.
- Keep `T11/T12` as the canonical SellerSprite stage reference pair.
- If business promotion is needed, move forward from one current `HOLD` candidate path through owner-side writeback rather than reopening current-stage flow repair.
