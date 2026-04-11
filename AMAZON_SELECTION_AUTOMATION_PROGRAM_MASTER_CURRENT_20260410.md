# Amazon Selection Automation Program Master Current (2026-04-10)

## Current Judgment

- Program architecture: `PROGRAM_MASTER_CURRENT__PURPOSE_ROUTED__PLAYWRIGHT_ONLY__SELLERSPRITE_FIRST__SIF_AFTER_SHORTLIST`
- Repo-level SellerSprite judgment: `SELLERSPRITE_NIGHTLY_READY`
- Business-level SellerSprite judgment: `SELLERSPRITE_NOT_CLOSED`
- Program judgment: `PROGRAM_NOT_READY_FOR_OTHER_BUSINESS_LINES`

## What Changed

- The project is no longer defined as a single universal path.
- The program is now purpose-routed.
- SellerSprite tools are mapped by business purpose instead of forcing every exact product idea through market-first gating.
- Existing v6 downstream stages stay in place:
  - Candidate Pool
  - SIF reinforcement
  - daytime cost / margin pack

## Formal Purposes

- `MARKET_DISCOVERY`
  - broad market discovery and market-first narrowing
- `PRODUCT_IDEA_VALIDATION`
  - exact product idea feasibility
- `COMPETITOR_REVERSE_MINING`
  - reverse mining from ASIN / brand / seller
- `SUPPLY_CHAIN_BACKSOLVE`
  - back-solving from supplier capability to product and market candidates

## Current Formal Tasks

- `T01 = MARKET_DISCOVERY`
  - input: `toy`
  - market whitelist is limited to the 10 visible rows from the current real workbook support set
  - current empirical status: workbook-based shortlist built; not a fresh Playwright export rerun
- `T02 = PRODUCT_IDEA_VALIDATION`
  - input: `claw machine`
  - `STEP3_REQUIRED = false`
  - `STEP3_OPTIONAL_ENRICHMENT = true`
  - current empirical status: STEP3 page-visible handoff is active, but live blocker is still unresolved
- `T03 = COMPETITOR_REVERSE_MINING`
  - input: real seed ASIN from T02 fresh artifact
  - current empirical status: contract and route are landed; live rerun not executed in this slice
- `T04 = SUPPLY_CHAIN_BACKSOLVE`
  - input: `toy novelty / arcade`
  - current empirical status: contract and route are landed; live rerun not executed in this slice

## SellerSprite Mapping

- `MARKET_DISCOVERY`
  - primary entry: STEP3 Market Research
  - support: STEP1 Product Research -> STEP4 Benchmark -> STEP2 Keyword
- `PRODUCT_IDEA_VALIDATION`
  - primary entry: STEP1 Product Research
  - support: STEP4 Benchmark -> STEP2 Keyword -> STEP3 broad market mapping
- `COMPETITOR_REVERSE_MINING`
  - primary entry: STEP4 Benchmark
  - support: STEP2 Keyword -> STEP1 Product -> STEP3 broad market remap
- `SUPPLY_CHAIN_BACKSOLVE`
  - primary entry: STEP1 Product or STEP3 Market depending supplier framing
  - support: STEP4 Benchmark -> STEP2 Keyword

## STEP3 Gate Policy

- STEP3 is still required for `MARKET_DISCOVERY`.
- STEP3 is not a universal hard gate anymore.
- For `PRODUCT_IDEA_VALIDATION`:
  - `STEP3_REQUIRED = false`
  - `STEP3_OPTIONAL_ENRICHMENT = true`
- Missing broad market mapping must project as a boundary state, not as whole-chain invalid.

## Candidate Pool Projection

- Candidate Pool must now preserve purpose-aware downgrade states such as:
  - `MARKET_MAPPING_PENDING`
  - `PASS_WITH_MARKET_MAPPING_PENDING`
  - `PRODUCT_FEASIBLE__MARKET_ABSTRACTION_PENDING`
  - `PARTIAL_REAL_SAMPLE_ONLY`
  - `BLOCKED_BY_MARKET_SOURCE_EMPTY`

## SIF Position

- SIF remains after candidate rows / shortlist.
- SIF does not move ahead of SellerSprite.
- `02A_SIF补强策略输入.csv` defines the future handoff contract only.
