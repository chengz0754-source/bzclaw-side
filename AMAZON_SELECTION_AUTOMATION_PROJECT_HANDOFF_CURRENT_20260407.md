# AMAZON SELECTION AUTOMATION PROJECT HANDOFF CURRENT 20260407

Resynced on `2026-04-09` because the previously referenced handoff file was not present in the repo.

## Current Judgment

- Repo-level current judgment:
  - `SELLERSPRITE_NIGHTLY_READY`
- Current `claw machine / US` closure truth:
  - `SELLERSPRITE_NOT_CLOSED`

## SellerSprite Current Architecture

- Product entry:
  - real page route is `scripts/export_product_research.py` -> `scripts/build_product_seed_pool.py`
  - page target is `https://www.sellersprite.com/v3/product-research`
- Keyword evidence:
  - formal main path is `export_keyword_research(storage_state workbook export) + export_keyword_trend(v3 visible table) + build_keyword_evidence_pool`
- Market research:
  - `PRODUCT_FORM` words no longer enter STEP3 by naked keyword search
  - `scripts/export_market_report.py` now resolves STEP1 sample `市场分析URL` first
- Benchmark:
  - `scripts/export_benchmark_competitors.py` now resolves formal seeds in this order:
    `STEP1_PRODUCT_GATE -> STEP3_MARKET_GATE -> manual override`
- Nightly orchestration:
  - `scripts/sellersprite_route_router.py`
  - `scripts/sellersprite_nightly_orchestrator.py`

## Current Status By Stage

- STEP1 Product entry: `BLOCKED`
  - real Product Research query/results are live
  - workbook export is currently blocked by `SELLERSPRITE_PRODUCT_RESEARCH_AUTH`
- STEP2 Keyword evidence: `CLOSED_AT_ARTIFACT_LAYER`
  - canonical `20/21/22` already exist for `claw machine / US`
  - gate is still `PASS=0 / FAIL=7 / HOLD=12`
  - fresh recollection is currently auth-sensitive
- STEP3 Market research: `PARTIAL`
  - route logic is corrected to `STEP1 product sample -> Market Analysis -> market research`
  - `SOURCE_EMPTY` and auth blockers no longer kill the nightly chain
  - latest live `claw machine` run entered through STEP1 sample `PSMP_969FF7CC8E / B07P44GKJR` and then hit `SELLERSPRITE_MARKET_RESEARCH_AUTH`
- STEP4 Benchmark: `PARTIAL`
  - page-download route has succeeded live with STEP1 seed routing
  - current nightly stability is still auth-sensitive on `v2/export-log`

## How To Read Git Truth

- Git truth is the current repo-visible code and docs:
  - `README.md`
  - `reports/sellersprite_keyword_chain_contract.md`
  - `reports/sellersprite_benchmark_chain_contract.md`
  - this handoff file
- Runtime logs under `logs/`, `outputs/`, and `runs/` are evidence only.
- Logs may prove that a route once succeeded, but they do not override Git current.
- When code and docs disagree, update the docs to match the code and the latest honest runtime classification.
