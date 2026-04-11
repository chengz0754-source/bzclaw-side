# amazon_selection_automation_plan_profit_first_v6_execution_20260407

Resynced on `2026-04-09` as the repo-current execution interpretation.

## SellerSprite Execution Reading

- Top-level repo judgment:
  - `SELLERSPRITE_NIGHTLY_READY`
- This does not equal full closure for every direction.
- Current `claw machine / US` remains:
  - `SELLERSPRITE_NOT_CLOSED`

## Current Execution Order

- `PRODUCT_FORM`
  - `STEP1_PRODUCT -> STEP4_BENCHMARK -> STEP2_KEYWORD -> STEP3_MARKET -> STEP7_CANDIDATE_POOL`
- `MARKET_CATEGORY`
  - `STEP3_MARKET -> STEP1_PRODUCT -> STEP4_BENCHMARK -> STEP2_KEYWORD -> STEP7_CANDIDATE_POOL`
- `PRECISE_DEMAND`
  - `STEP2_KEYWORD -> STEP3_MARKET -> STEP4_BENCHMARK -> STEP7_CANDIDATE_POOL`

## Current Operational Meaning

- STEP1 is no longer allowed to rely on the old pseudo-product entry.
- STEP2 is no longer just `blocked`; it has canonical `20/21/22`, but the gate is still `HOLD`.
- STEP3 for product-form words is no longer allowed to hit market research with a naked keyword as the main path.
- STEP4 is no longer defined by API lookup as the main path; the main path is page query -> export -> export-log -> workbook parse.
- Candidate-pool execution must preserve downgrade boundaries such as:
  - `PARTIAL_REAL_SAMPLE_ONLY`
  - `BLOCKED_BY_MARKET_SOURCE_EMPTY`

## Current Follow-up Priority

- Refresh canonical STEP1 Product Research auth so real `10/11/12` can be rebuilt on the true product page.
- Refresh STEP3 market auth so the corrected product-sample market route can rebuild fresh `30/31/32`.
- Keep STEP2 and STEP4 marked as auth-sensitive rather than pretending to be fully stable all-night collectors.
