# CODEX Toy Category Parameterization Run Summary (2026-04-11)

## Current Git Truth

- Program current remains `PURPOSE_ROUTED / PLAYWRIGHT_ONLY / SELLERSPRITE_FIRST / SIF_AFTER_SHORTLIST`.
- Business current remains `SELLERSPRITE_NOT_CLOSED`.
- `claw machine / US` remains `PRODUCT_IDEA_VALIDATION`.
- STEP3 collector is already successful and is not the current blocker for this slice.
- This slice only parameterized the STEP3 gate chain and reran `build_market_workbook_index.py` plus `build_candidate_pool.py`.

## Category Template Integration

- New repo-visible parameter source:
  - `templates/category_gate_profiles/01__CATEGORY_GATE_PROFILES__TOY_V1__20260411.csv`
- Current input routing sheet now carries:
  - `类目大类`
  - `类目子类`
  - `业务目的`
  - `参数模板ID`
  - `参数版本`
  - `参数来源`
- Updated current input:
  - `inputs/selection_run_current/01_选品任务路由与目的.csv`
- Updated template input:
  - `templates/selection_csv_cn_reference/01_选品任务路由与目的.csv`

## Matched Profile

- Current case:
  - `direction_id = T02`
  - `keyword = claw machine`
  - `site = US`
  - `purpose_type = PRODUCT_IDEA_VALIDATION`
  - `category_l1 = TOY`
  - `category_l2 = TOY_NOVELTY_ARCADE`
- Matched profile:
  - `TOY_NOVELTY_ARCADE__IDEA_VALIDATION__V1`
- Rule source:
  - `templates/category_gate_profiles/01__CATEGORY_GATE_PROFILES__TOY_V1__20260411.csv`

## STEP3 Rerun

- Command:
  - `.\.venv\Scripts\python.exe scripts\build_market_workbook_index.py --context-row-index 2 --market-dir runs/manual/10_market/20260411_t02_direct_asset_override --output-dir outputs/selection_runs/20260411_t02_toy_parameterized_step3/02_generated_outputs --batch-id STEP3_TOY_PARAM_T02_20260411`
- Fixed input workbook:
  - `runs/manual/10_market/20260411_t02_direct_asset_override/market-report-us-claw-machine-d30-new6m-sample100-head10-20260411_003456.xlsx`
- New outputs:
  - `outputs/selection_runs/20260411_t02_toy_parameterized_step3/02_generated_outputs/30_市场调研原始索引.csv`
  - `outputs/selection_runs/20260411_t02_toy_parameterized_step3/02_generated_outputs/31_市场调研清洗结果.csv`
  - `outputs/selection_runs/20260411_t02_toy_parameterized_step3/02_generated_outputs/32_市场调研下推结果.csv`
  - `outputs/selection_runs/20260411_t02_toy_parameterized_step3/02_generated_outputs/market_chain_output_index.md`
- Gate summary changed from:
  - `PASS=0 / FAIL=16 / HOLD=1`
- Gate summary to:
  - `PASS=0 / FAIL=0 / HOLD=17`

### STEP3 Reason Distribution

- `S3_MAX_SELLER_CONCENTRATION:HOLD = 15`
- `S3_MAX_BRAND_CONCENTRATION:HOLD = 11`
- `S3_MAX_AVG_PRICE:HOLD = 10`
- `S3_MAX_COMMODITY_CONCENTRATION:HOLD = 8`
- `S3_MIN_NEW_PRODUCT_RATIO:HOLD = 5`
- `S3_MIN_MARKET_VOLUME:HOLD = 3`
- `S3_MIN_AVG_PRICE:HOLD = 1`

### STEP3 Interpretation

- Toy category parameterization is successfully connected.
- The toy profile clearly softened the previous universal hard-fail chain.
- This rerun does **not** support the old judgment of `real market fail` for the current toy case.
- It also does **not** produce STEP3 PASS rows yet.
- The current truth is:
  - hard fails were mostly a universal-rule mismatch
  - remaining blocker is a conservative hold-only toy validation gate, not replay/auth/collector failure

## STEP7 Rerun

- Command:
  - `.\.venv\Scripts\python.exe scripts\build_candidate_pool.py --context-row-index 2 --step1-gate-csv outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/12_产品样本下推结果.csv --step2-gate-csv outputs/selection_runs/20260410_auth_replay_formal/02_generated_outputs/22_关键词证据词池下推结果.csv --step3-gate-csv outputs/selection_runs/20260411_t02_toy_parameterized_step3/02_generated_outputs/32_市场调研下推结果.csv --step4-gate-csv outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/42_竞品基准下推结果.csv --output-dir outputs/selection_runs/20260411_t02_toy_parameterized_step7/02_generated_outputs --log-dir logs/formal_t02_toy_parameterized_20260411/step7_candidate_pool --batch-id STEP7_T02_TOY_PARAM_20260411`
- Current run summary:
  - `status = HOLD`
  - `reason_code = PRODUCT_FEASIBLE__MARKET_ABSTRACTION_PENDING`
  - `step3_status = HOLD`
  - `intermediate_row_count = 46`
  - `final_row_count = 46`
- Output artifacts:
  - `outputs/selection_runs/20260411_t02_toy_parameterized_step7/02_generated_outputs/03_候选市场与候选品初筛池.csv`
  - `outputs/selection_runs/20260411_t02_toy_parameterized_step7/02_generated_outputs/60_候选样品池.csv`
  - `outputs/selection_runs/20260411_t02_toy_parameterized_step7/02_generated_outputs/60_候选样品池.md`

## Required Answers

1. Toy category parameter template is successfully integrated into the current chain.
2. `TOY_NOVELTY_ARCADE__IDEA_VALIDATION__V1` does **not** produce STEP3 PASS in this rerun.
3. If PASS is still zero, the main cause is closer to:
   - `参数仍过严`
   - more precisely: the toy validation profile correctly removed hard fails, but it still leaves every row under at least one HOLD condition.
   - this is not the same as confirming `BUSINESS_NO_GO__REAL_MARKET_NOT_PASSABLE`.
4. SellerSprite remains:
   - `SELLERSPRITE_NOT_CLOSED`

## Next Exact Slice

- Keep the current collector output frozen.
- Do not return to auth / replay / route semantics.
- Open one narrow follow-up slice only if needed:
  - review whether `TOY_NOVELTY_ARCADE__IDEA_VALIDATION__V1` should allow a purpose-specific PASS path for `PRODUCT_IDEA_VALIDATION`
  - or explicitly accept that this purpose should remain HOLD-only and stop expecting STEP3 PASS for idea validation
