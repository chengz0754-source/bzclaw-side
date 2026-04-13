# CODEX_CLOSURE_SEMANTICS_SPLIT_SUMMARY_20260412

## Current Git Truth
- Project shape remains `PURPOSE_ROUTED / PLAYWRIGHT_ONLY / SELLERSPRITE_FIRST / SIF_AFTER_SHORTLIST`.
- This slice does not reopen exporters or reruns. It only fixes the canonical wording used to describe current repo-visible truth.
- The problem being fixed here is semantic, not data-collection availability:
  - line flows are already deposited
  - real rows already land in repo-visible artifacts
  - but business-layer `HOLD` states were still collapsing everything back into a single `not closed` judgment

## Canonical Semantics Split
- `FLOW_CLOSED`
  - means the SellerSprite collection/validation flow for that scope is deposited, callable, and has already landed its required repo-visible outputs
- `BUSINESS_PROMOTED`
  - means the current repo-visible business layer for that scope has advanced beyond the present `HOLD` / pending boundary
- `SELLERSPRITE_CLOSED`
  - is reserved for the case where overall SellerSprite is both:
    - `FLOW_CLOSED`
    - `BUSINESS_PROMOTED`
- Canonical negatives are:
  - `FLOW_NOT_CLOSED`
  - `BUSINESS_NOT_PROMOTED`
  - `BUSINESS_NOT_APPLICABLE`
- No alias should replace these canonical terms in board, README, registry, or final closure summaries.

## T11 Minimum Legal Reading
- `T11 / Squeeze Toys`
  - `flow_closure_status = FLOW_CLOSED`
  - `business_promotion_status = BUSINESS_NOT_PROMOTED`
- Why this is legal:
  - first real candidate flow has already landed for `T11`
  - real candidate rows exist in `60_候选样品池.csv`
  - latest reruns still leave those rows at `HOLD`, so business promotion has not landed
- Therefore the correct T11 split is:
  - `FLOW_CLOSED`
  - `BUSINESS_NOT_PROMOTED`
  - not `SELLERSPRITE_CLOSED`

## Line-Level Mapping
- `P0 / SHARED_FOUNDATION`
  - `flow_closure_status = FLOW_NOT_CLOSED`
  - `business_promotion_status = BUSINESS_NOT_APPLICABLE`
- `T01 / MARKET_DISCOVERY`
  - `flow_closure_status = FLOW_CLOSED`
  - `business_promotion_status = BUSINESS_NOT_PROMOTED`
- `T02 / PRODUCT_IDEA_VALIDATION`
  - `flow_closure_status = FLOW_CLOSED`
  - `business_promotion_status = BUSINESS_NOT_PROMOTED`
- `T03 / COMPETITOR_REVERSE_MINING`
  - `flow_closure_status = FLOW_CLOSED`
  - `business_promotion_status = BUSINESS_NOT_PROMOTED`
- `T04 / SUPPLY_CHAIN_BACKSOLVE`
  - `flow_closure_status = FLOW_CLOSED`
  - `business_promotion_status = BUSINESS_NOT_PROMOTED`

## Overall SellerSprite Reading
- Overall SellerSprite now has a legal two-layer reading:
  - `flow_closure_status = FLOW_CLOSED`
  - `business_promotion_status = BUSINESS_NOT_PROMOTED`
- Why overall `FLOW_CLOSED` is now legal:
  - all four purpose lines are deposited as callable skill + runner assets
  - `T01` has already landed a first real candidate flow
  - `T02/T03/T04` each reach Candidate Pool with reusable repo-visible lines
- Why overall `BUSINESS_PROMOTED` is still not legal:
  - `T11` candidate rows remain `HOLD`
  - `T02/T03/T04` are still business-pending lines
  - `P0` continuity hardening is still open
- Therefore the legal overall wording remains:
  - `SELLERSPRITE_NOT_CLOSED`

## Repo Files Updated
- `README.md`
- `reports/MASTER_PROGRESS_BOARD__20260412.csv`
- `skills/skill_sellersprite_four_line_runtime_registry.md`
- `reports/CODEX_FINAL_INTEGRATION_AND_REGISTRY_SUMMARY_20260412.md`
- `reports/CODEX_FINAL_SELLERSPRITE_CLOSURE_GATE_SUMMARY_20260412.md`
- `reports/CODEX_CLOSURE_SEMANTICS_SPLIT_SUMMARY_20260412.md`

## Next Exact Slice
- Do not reopen wording again unless repo-visible truth changes.
- Keep using the split semantics:
  - `FLOW_CLOSED`
  - `BUSINESS_PROMOTED`
- The next substantive work slice should stay operational:
  - either stabilize `T11/T12`
  - or advance a current `HOLD` line toward business promotion
