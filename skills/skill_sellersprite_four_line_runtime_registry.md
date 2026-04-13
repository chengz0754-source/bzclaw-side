# skill_sellersprite_four_line_runtime_registry

## Purpose
- This registry is the top-level runtime map for the four SellerSprite purpose lines.
- It exists to keep `T01 / T02 / T03 / T04` callable through one consistent entry without inventing new business semantics.
- It is a dispatch and governance registry, not a new business line.

## Current Git Truth
- Project shape remains `PURPOSE_ROUTED / PLAYWRIGHT_ONLY / SELLERSPRITE_FIRST / SIF_AFTER_SHORTLIST`.
- Canonical closure semantics are now split into:
  - `FLOW_CLOSED` / `FLOW_NOT_CLOSED`
  - `BUSINESS_PROMOTED` / `BUSINESS_NOT_PROMOTED`
- SellerSprite overall split status is now:
  - `flow_closure_status = FLOW_CLOSED`
  - `business_promotion_status = BUSINESS_NOT_PROMOTED`
  - canonical legal overall wording is `SELLERSPRITE_FLOW_CLOSED__BUSINESS_NOT_PROMOTED`
  - legacy single-layer fallback wording remains `SELLERSPRITE_NOT_CLOSED`
- `P0` shared foundation is still a hardening debt:
  - `flow_closure_status = FLOW_NOT_CLOSED`
  - `business_promotion_status = BUSINESS_NOT_APPLICABLE`
- `T01`, `T02`, `T03`, and `T04` are all line-level `FLOW_CLOSED` lines, but none of them is yet `BUSINESS_PROMOTED`.
- `T02 / T03 / T04` are now canonicalized as:
  - `POST_STAGE_OPEN_DEBT`
  - not current SellerSprite stage blockers

## Canonical Semantics
- `FLOW_CLOSED` means the SellerSprite collection/validation layer for that scope is deposited, callable, and has already landed real repo-visible outputs through Candidate Pool or an equivalent line-standard artifact boundary.
- `BUSINESS_PROMOTED` means the current repo-visible business layer for that scope has advanced beyond the present `HOLD` / pending gate for that scope.
- `SELLERSPRITE_CLOSED` is reserved for the case where the overall program is both:
  - `FLOW_CLOSED`
  - `BUSINESS_PROMOTED`
- Do not replace these canonical terms with aliases when the split status itself is what needs to be stated.

## Runtime Registry

### T01 / MARKET_DISCOVERY
- purpose_type: `MARKET_DISCOVERY`
- line_id: `T01`
- runner: `scripts/run_t01_market_discovery.py`
- skill: `skills/skill_sellersprite_t01_market_discovery.md`
- primary input template: `inputs/selection_run_current/05A__INPUT_TEMPLATE__T01_MARKET_DISCOVERY__20260412.csv`
- expected input shape: shortlisted market term or single market-discovery pilot row
- flow_closure_status: `FLOW_CLOSED`
- business_promotion_status: `BUSINESS_NOT_PROMOTED`
- current line truth: `FLOW_CLOSED__BUSINESS_NOT_PROMOTED__STABILITY_CONFIRMED`
- use when:
  - the input is a shortlisted market term
  - we want `market -> shortlist -> product -> benchmark -> keyword/traffic -> candidate pool`

### T02 / PRODUCT_IDEA_VALIDATION
- purpose_type: `PRODUCT_IDEA_VALIDATION`
- line_id: `T02`
- runner: `scripts/run_t02_product_idea_validation.py`
- skill: `skills/skill_sellersprite_t02_product_idea_validation.md`
- primary input template: `inputs/selection_run_current/05B__INPUT_TEMPLATE__T02_PRODUCT_IDEA_VALIDATION__20260412.csv`
- expected input shape: one exact product-idea term
- flow_closure_status: `FLOW_CLOSED`
- business_promotion_status: `BUSINESS_NOT_PROMOTED`
- current line truth: `FLOW_CLOSED__BUSINESS_NOT_PROMOTED__REUSABLE_LINE`
- post_stage_debt_class: `POST_STAGE_OPEN_DEBT`
- current-stage blocker status: `NONE`
- use when:
  - the input is one concrete product idea
  - `STEP3` must stay optional enrichment instead of a universal hard gate

### T03 / COMPETITOR_REVERSE_MINING
- purpose_type: `COMPETITOR_REVERSE_MINING`
- line_id: `T03`
- runner: `scripts/run_t03_competitor_reverse_mining.py`
- skill: `skills/skill_sellersprite_t03_competitor_reverse_mining.md`
- primary input template: `inputs/selection_run_current/05C__INPUT_TEMPLATE__T03_COMPETITOR_REVERSE_MINING__20260412.csv`
- expected input shape: one real ASIN / brand / seller seed from T01 or T02 outputs
- flow_closure_status: `FLOW_CLOSED`
- business_promotion_status: `BUSINESS_NOT_PROMOTED`
- current line truth: `FLOW_CLOSED__BUSINESS_NOT_PROMOTED__REUSABLE_LINE`
- post_stage_debt_class: `POST_STAGE_OPEN_DEBT`
- current-stage blocker status: `NONE`
- use when:
  - the input is a real reverse-mining seed
  - the line must keep reverse lineage and keyword/traffic validation intact

### T04 / SUPPLY_CHAIN_BACKSOLVE
- purpose_type: `SUPPLY_CHAIN_BACKSOLVE`
- line_id: `T04`
- runner: `scripts/run_t04_supply_chain_backsolve.py`
- skill: `skills/skill_sellersprite_t04_supply_chain_backsolve.md`
- primary input template: `inputs/selection_run_current/05D__INPUT_TEMPLATE__T04_SUPPLY_CHAIN_BACKSOLVE__20260412.csv`
- expected input shape: one real `supplier_family`
- flow_closure_status: `FLOW_CLOSED`
- business_promotion_status: `BUSINESS_NOT_PROMOTED`
- current line truth: `FLOW_CLOSED__BUSINESS_NOT_PROMOTED__REUSABLE_LINE`
- post_stage_debt_class: `POST_STAGE_OPEN_DEBT`
- current-stage blocker status: `NONE`
- use when:
  - the starting point is a real supply-family boundary
  - the line must backsolve product/market/benchmark/keyword evidence into Candidate Pool

## Calling Order
- First decide whether the issue is still a shared `P0` blocker or a line-specific run request.
- If the problem is shared surface continuity, use:
  - `scripts/run_sellersprite_shared_foundation.py`
- If the problem is one purpose line, use:
  - `scripts/run_sellersprite_purpose_line.py --purpose-type <...>`
- Do not use this registry to bypass a line runner or invent a fifth purpose.

## Layer Boundary
- SellerSprite collection/validation layer ends at:
  - `STEP1`
  - `STEP4`
  - `STEP2`
  - optional `STEP3`
  - `STEP7 Candidate Pool`
- Owner-side manual writeback sits after the current SellerSprite stage and is not part of current-stage blocker logic:
  - `合规`
  - `改良点`
  - `最终解释`
  - `利润核价`
- Results after SellerSprite belong to later layers and are not part of this runtime registry:
  - SIF enrichment
  - daytime profit checking
  - owner-side manual writeback
  - manual profitability judgment

## Reuse Reading
- If a line is marked `FLOW_CLOSED`, that line is callable and its SellerSprite collection/validation flow has already landed.
- If that same line is still marked `BUSINESS_NOT_PROMOTED`, its current rows or gate layer are still on the business-side `HOLD` / pending side of the boundary.
- If `T02`, `T03`, or `T04` is marked `POST_STAGE_OPEN_DEBT`, that line remains open only after current-stage flow closure; it must not be written back as the active blocker for the current SellerSprite stage.
- Blank owner-side manual writeback fields must not be used to redefine a current-stage SellerSprite blocker.
- If a scope is marked `FLOW_NOT_CLOSED`, the runner/skill may still exist and be useful, but the line has not yet met its first repo-visible flow-closure standard.
