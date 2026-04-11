# CODEX T02 STEP3 Gate-Chain Fix Summary (2026-04-11)

## Current Git Truth

- Program truth stays `PURPOSE_ROUTED / PLAYWRIGHT_ONLY / SELLERSPRITE_FIRST / SIF_AFTER_SHORTLIST`.
- Business truth stays `SELLERSPRITE_NOT_CLOSED`.
- `claw machine` stays `PRODUCT_IDEA_VALIDATION`.
- `T02 STEP3_REQUIRED = false`.
- `T02 STEP3_OPTIONAL_ENRICHMENT = true`.
- Current STEP3 truth is no longer auth / replay / handoff blockage.
- Current STEP3 collector has already landed:
  - real workbook
  - fresh `30_市场调研原始索引.csv`
  - fresh `31_市场调研清洗结果.csv`
  - fresh `32_市场调研下推结果.csv`

## Why This Slice Stopped Fixing The Collector

This slice froze the current STEP3 collector output and did not reopen browser export logic.

Frozen STEP3 collector inputs:

- `runs/manual/10_market/20260411_t02_direct_asset_override/market-report-us-claw-machine-d30-new6m-sample100-head10-20260411_003456.xlsx`
- `outputs/selection_runs/20260411_t02_direct_asset_override_step3/02_generated_outputs/30_市场调研原始索引.csv`
- `outputs/selection_runs/20260411_t02_direct_asset_override_step3/02_generated_outputs/31_市场调研清洗结果.csv`
- `outputs/selection_runs/20260411_t02_direct_asset_override_step3/02_generated_outputs/32_市场调研下推结果.csv`
- `logs/formal_t02_direct_asset_override_20260411/step3_market_export/latest_run.json`

The current problem has moved from:

- auth
- replay
- owner asset quality
- handoff continuity

to:

- STEP3 gate-chain judgment over a real workbook

## Where The STEP3 Gate Chain Actually Runs

Current STEP3 gate path is:

1. `scripts/build_market_workbook_index.py`
   - `load_step3_rules()`
   - `build_cleaned_rows()`
   - `evaluate_rule()`
   - `build_gate_rows()`
2. `scripts/build_candidate_pool.py`
   - `stage_status_from_gate_rows()`
   - `boundary_pool_status()`
   - `market_mapping_pending_status()`

Current truth from code audit:

- `build_market_workbook_index.py` is purpose-agnostic.
- It still applies the universal STEP3 rule table from `templates/selection_canonical_standards/90_下推参数表.csv`.
- `STEP3_OPTIONAL_ENRICHMENT = true` is not enforced inside STEP3 rule evaluation itself.
- That optional boundary is already enforced downstream inside `scripts/build_candidate_pool.py`.

So the current architecture is:

- STEP3 builder decides row-level market viability using the standard rule table.
- Candidate-pool builder decides whether non-`PASS` STEP3 should block the whole direction.

## 32 Gate Audit

### Status distribution

- `PASS = 0`
- `FAIL = 16`
- `HOLD = 1`

### Reason-code distribution

- `S3_MAX_SELLER_CONCENTRATION:HOLD` = `16`
- `S3_MAX_BRAND_CONCENTRATION:HOLD` = `14`
- `S3_MAX_COMMODITY_CONCENTRATION:FAIL` = `14`
- `S3_MAX_AVG_PRICE:FAIL` = `11`
- `S3_MIN_MARKET_VOLUME:FAIL` = `8`
- `S3_MIN_NEW_PRODUCT_RATIO:HOLD` = `6`
- `S3_MIN_AVG_PRICE:FAIL` = `1`

### Reason-code mapping and judgment

| reason_code | source field | current rule | count | current judgment |
| --- | --- | --- | --- | --- |
| `S3_MIN_AVG_PRICE:FAIL` | `平均价格` | `>= 15`, hard fail | `1` | reasonable under the current contract; borderline but not a parse bug |
| `S3_MAX_AVG_PRICE:FAIL` | `平均价格` | `<= 60`, hard fail | `11` | reasonable under the current contract; values like `83.65`, `94.48`, `244.97`, `580.62` are truly above threshold |
| `S3_MIN_MARKET_VOLUME:FAIL` | `月总销量` | `>= 3000`, hard fail | `8` | reasonable under the current contract; the workbook really contains rows below `3000` |
| `S3_MIN_NEW_PRODUCT_RATIO:HOLD` | `新品占比_pct` | `>= 10`, soft hold | `6` | reasonable under the current contract; blank / `N/A` / low values correctly become hold rather than fail |
| `S3_MAX_COMMODITY_CONCENTRATION:FAIL` | `商品集中度` | `<= 0.45`, hard fail | `14` | reasonable under the current contract; values like `0.451`, `0.492`, `0.737`, `1` are real workbook values |
| `S3_MAX_BRAND_CONCENTRATION:HOLD` | `品牌集中度` | `<= 0.60`, soft hold | `14` | reasonable under the current contract; high concentration is being treated as warning, not hard fail |
| `S3_MAX_SELLER_CONCENTRATION:HOLD` | `卖家集中度` | `<= 0.55`, soft hold | `16` | reasonable under the current contract; every row exceeds the soft threshold, so all rows keep this warning |

### Spot checks against the real workbook-derived 31 rows

- `Drinking Games`
  - `商品集中度 = 0.451`
  - rule `S3_MAX_COMMODITY_CONCENTRATION <= 0.45`
  - current `FAIL` is consistent with the actual parsed value
- `Air Hockey`
  - `平均价格 = 83.65`
  - rule `S3_MAX_AVG_PRICE <= 60`
  - current `FAIL` is consistent with the actual parsed value
- `Foosball Accessories`
  - `平均价格 = 14.65`
  - rule `S3_MIN_AVG_PRICE >= 15`
  - current `FAIL` is consistent with the actual parsed value
- `Shuffleboard Accessories`
  - no hard-fail rule is broken
  - current row is the only `HOLD`
  - this is consistent with the soft-hold rule design

## Gate-Chain Bug Judgment

### Technical finding

- No field-mapping bug was confirmed.
- No column-name mismatch was confirmed.
- No numeric normalization bug was confirmed.
- No blank-value misclassification bug was confirmed.
- No downstream consumption bug was confirmed for this slice.

### Current interpretation

The current zero-pass result is coming from real workbook values hitting the current canonical thresholds.

There is still a contract-layer nuance:

- STEP3 rules are still the universal market-screen rules inherited from the canonical standards.
- They are not purpose-specific rules for `PRODUCT_IDEA_VALIDATION`.

But in the current repo architecture, that is not by itself a confirmed technical bug, because:

- STEP3 optionality is already handled downstream in `build_candidate_pool.py`
- the current candidate-pool result stays pending instead of collapsing the whole chain

Therefore this slice concludes:

- `GATE_CHAIN_BUG_NOT_CONFIRMED`

## Minimal Rerun

### STEP3 gate rerun

Command:

```powershell
.\.venv\Scripts\python.exe scripts\build_market_workbook_index.py --context-row-index 2 --market-dir runs/manual/10_market/20260411_t02_direct_asset_override --output-dir outputs/selection_runs/20260411_t02_step3_gate_chain_rerun/02_generated_outputs --batch-id STEP3_GATE_CHAIN_AUDIT_20260411
```

Result:

- selected workbook stayed the same real workbook
- fresh rerun again produced:
  - `30_市场调研原始索引.csv`
  - `31_市场调研清洗结果.csv`
  - `32_市场调研下推结果.csv`
- gate summary stayed:
  - `PASS=0 / FAIL=16 / HOLD=1`

This rerun confirms the current gate result is stable on frozen collector input.

### STEP7 rerun

Command:

```powershell
.\.venv\Scripts\python.exe scripts\build_candidate_pool.py --context-row-index 2 --step1-gate-csv outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/12_产品样本下推结果.csv --step2-gate-csv outputs/selection_runs/20260410_auth_replay_formal/02_generated_outputs/22_关键词证据词池下推结果.csv --step3-gate-csv outputs/selection_runs/20260411_t02_step3_gate_chain_rerun/02_generated_outputs/32_市场调研下推结果.csv --step4-gate-csv outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/42_竞品基准下推结果.csv --output-dir outputs/selection_runs/20260411_t02_step7_gate_chain_rerun/02_generated_outputs --log-dir logs/formal_t02_step3_gate_chain_20260411/step7_candidate_pool --batch-id STEP7_T02_STEP3_GATE_CHAIN_20260411
```

Result:

- `status = HOLD`
- `reason_code = PRODUCT_FEASIBLE__MARKET_ABSTRACTION_PENDING`
- `final_row_count = 46`

This confirms downstream consumption is behaving consistently:

- STEP3 has fresh real workbook truth
- STEP3 still has no `PASS` rows
- STEP7 remains pending, not falsely promoted to closure

## Final Judgment

- Judgment A: `GATE_CHAIN_BUG_NOT_CONFIRMED`
- Judgment B: `STEP3_GATE_PASS_STILL_ZERO`
- Judgment C: `BUSINESS_NO_GO__REAL_MARKET_NOT_PASSABLE`
- Judgment D: `SELLERSPRITE_NOT_CLOSED`

## Why The Main Cause Is Business No-Go Rather Than Technical Failure

The strongest current evidence is:

- the collector path succeeded
- the workbook is real
- the parsed fields are coherent
- the reason codes line up with workbook values
- rerunning the gate chain reproduces the same result without reopening the browser collector

So the current blocking truth is no longer “the system failed to get market truth.”

The current truth is:

- the system got market truth
- that market truth did not yield any STEP3 `PASS` rows under the current canonical market-screen contract

## Next Exact Slice

Do not reopen:

- auth
- replay
- owner recording
- route semantics
- T03 / T04
- SIF

Next slice should stay narrow and repo-visible:

1. treat STEP3 collector success as settled truth
2. decide whether the universal STEP3 market-screen contract should remain purpose-agnostic for `PRODUCT_IDEA_VALIDATION`
3. if the answer is “yes”, stop technical looping and keep the current business-no-go judgment
4. if the answer is “no”, then the next slice is a pure contract-change slice for purpose-specific STEP3 thresholds, not a collector-repair slice
