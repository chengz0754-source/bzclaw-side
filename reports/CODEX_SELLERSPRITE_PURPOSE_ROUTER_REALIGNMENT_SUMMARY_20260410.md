# CODEX SellerSprite Purpose Router Realignment Summary (2026-04-10)

## Scope

This slice stayed inside the `amazon-selection-automation` sidecar repo.

Exact scope:

- upgrade the project from single-path logic to purpose-routed logic
- add formal purpose-routed input tables
- realign SellerSprite path mapping around business purpose
- downgrade STEP3 from universal hard gate to conditional gate
- upgrade candidate-pool state projection for market-mapping-pending cases
- define SIF as a shortlist reinforcement layer only

Out of scope:

- SIF live mainline automation
- unapproved API paths
- SellerSprite closure claims
- unrelated business lines

## Current Git Truth After This Slice

- repo-level judgment stays `SELLERSPRITE_NIGHTLY_READY`
- business-level judgment stays `SELLERSPRITE_NOT_CLOSED`
- STEP1 and STEP4 keep their fresh PASS ability
- STEP2 still has artifact layer but business gate stays `HOLD`
- STEP3 is no longer treated as a universal hard gate for exact product ideas

## New Master Plan

- added: `AMAZON_SELECTION_AUTOMATION_PROGRAM_MASTER_CURRENT_20260410.md`
- the program is now explicitly:
  - `PURPOSE_ROUTED`
  - `PLAYWRIGHT_ONLY`
  - `SELLERSPRITE_FIRST`
  - `SIF_AFTER_SHORTLIST`

## New Input Contract

Formal operator-facing tables now are:

- `00_选品运行目标与边界.csv`
- `01_选品任务路由与目的.csv`
- `01A_市场发现参数.csv`
- `01B_产品与竞品种子输入.csv`
- `02_账号与合规预检查.csv`
- `02A_SIF补强策略输入.csv`

Current runtime note:

- legacy `01_市场入口与筛选参数.csv` is still kept for collector runtime knobs
- purpose and route switching now come from the new `01 / 01A / 01B / 02A` layer

## Purpose Router

Formal purposes:

- `MARKET_DISCOVERY`
- `PRODUCT_IDEA_VALIDATION`
- `COMPETITOR_REVERSE_MINING`
- `SUPPLY_CHAIN_BACKSOLVE`

`claw machine` now resolves to:

- `PRODUCT_IDEA_VALIDATION`

The router now emits:

- `purpose_type`
- `route_sequence`
- `step3_policy`
- `step3_required`
- `step3_optional_enrichment`
- SellerSprite primary/supporting entry mapping

## SellerSprite Path Mapping

- `MARKET_DISCOVERY`
  - primary: STEP3 Market
  - support: STEP1 -> STEP4 -> STEP2
- `PRODUCT_IDEA_VALIDATION`
  - primary: STEP1 Product
  - support: STEP4 -> STEP2 -> STEP3 optional enrichment
- `COMPETITOR_REVERSE_MINING`
  - primary: STEP4 Benchmark
  - support: STEP2 -> STEP1 -> STEP3 optional remap
- `SUPPLY_CHAIN_BACKSOLVE`
  - primary: STEP1 or STEP3 depending supplier framing
  - support: STEP4 -> STEP2

## Candidate Pool Upgrade

Candidate-pool projection is now purpose-aware.

For `PRODUCT_IDEA_VALIDATION`, when real samples exist but broad market mapping is still pending, the pool may now project:

- `MARKET_MAPPING_PENDING`
- `PASS_WITH_MARKET_MAPPING_PENDING`
- `PRODUCT_FEASIBLE__MARKET_ABSTRACTION_PENDING`

The pool still preserves older downgrade truth when applicable:

- `PARTIAL_REAL_SAMPLE_ONLY`
- `BLOCKED_BY_MARKET_SOURCE_EMPTY`

## SIF Position

- added: `reports/sif_shortlist_reinforcement_contract.md`
- SIF is now explicitly defined as a shortlist / candidate-row reinforcement layer
- `02A_SIF补强策略输入.csv` defines the handoff contract
- this slice does not claim live SIF readiness

## Validation

- router classification was re-run for `claw machine / US`
- candidate pool was rebuilt from fresh formal artifacts after the purpose-policy change

## Exact Next Slice

Keep SellerSprite-first scope and repair the next live blocker:

1. continue from fresh STEP1 / STEP4
2. repair STEP3 market-entry handoff on the purpose-routed path
3. re-run STEP3
4. re-run STEP7 with the updated STEP3 truth
