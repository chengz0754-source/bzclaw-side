# SIF Shortlist Reinforcement Contract

## Scope

- This contract defines where SIF attaches in the purpose-routed program.
- SIF is a shortlist / candidate-row reinforcement layer.
- SIF is not a pre-SellerSprite universal gate.
- This contract does not claim that live SIF auth or live SIF collectors are already stable.

## Entry Position

- SIF may only enter after SellerSprite has already emitted candidate rows:
  - `03_候选市场与候选品初筛池.csv`
  - `60_候选样品池.csv`
- The normal handoff order is:
  - SellerSprite evidence and sample collection
  - Candidate pool projection
  - shortlist selection
  - SIF reinforcement
  - daytime cost / margin pack

## Input Objects

- Candidate rows:
  - `outputs/selection_runs/<batch_id>/02_generated_outputs/60_候选样品池.csv`
- Candidate pool summary:
  - `outputs/selection_runs/<batch_id>/02_generated_outputs/candidate_pool_summary.json`
- Purpose-routed SIF strategy input:
  - `inputs/selection_run_current/02A_SIF补强策略输入.csv`
- Optional shortlist filters:
  - ASIN
  - brand
  - seller
  - keyword

## Allowed Purposes

- `MARKET_DISCOVERY`
  - SIF is only for shortlist reinforcement after market and product narrowing.
- `PRODUCT_IDEA_VALIDATION`
  - SIF reinforces shortlisted ASIN rows after STEP1 / STEP4 / STEP2 evidence exists.
- `COMPETITOR_REVERSE_MINING`
  - SIF reinforces shortlisted competitor / brand / seller rows.
- `SUPPLY_CHAIN_BACKSOLVE`
  - SIF stays optional and only applies after candidate rows exist.

## Output Layer

- SIF-aligned structured outputs remain:
  - `50_SIF流量结构补强.csv`
  - `51_SIF关键词价值补强.csv`
  - `52_SIF广告结构补强.csv`
  - `53_SIF补强下推结果.csv`
- Downstream daytime pack remains:
  - `61_待供应链核利清单.csv`
  - `61_待供应链核利清单.md`

## Current Repo Truth On 2026-04-10

- SellerSprite remains first.
- SIF is not allowed to pre-empt SellerSprite formal-path repair.
- If SIF auth or SIF surface proof is still blocked, the repo must keep fail-closed SIF outputs.
- `02A_SIF补强策略输入.csv` only formalizes the handoff contract; it does not prove live SIF automation is ready.
