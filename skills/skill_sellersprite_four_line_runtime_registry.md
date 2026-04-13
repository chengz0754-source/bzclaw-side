# skill_sellersprite_four_line_runtime_registry

This registry is a deterministic current-state host rendered by `scripts/write_sellersprite_current_state.py`.

## Current Git Truth

- SellerSprite current-stage closure contract is flow-only:
  - `current_stage_closure_status = FLOW_CLOSED`
  - `current_stage_closed = true`
  - `artifact_depth_reconciled = true`
- `business_promotion_status` belongs to the next-stage owner/business flow and does not reopen current-stage closure.
- `P0` remains non-blocking hardening debt:
  - `hardening_debt_blocking = false`
- `T02 / T03 / T04` remain `POST_STAGE_OPEN_DEBT`, not current-stage blockers.
- latest machine-readable status host: `reports/latest_sellersprite_stage_status.json`

## Runtime Registry

### T01 / MARKET_DISCOVERY

- flow_closure_status: `FLOW_CLOSED`
- business_promotion_status: `BUSINESS_NOT_PROMOTED`
- current line truth: `CURRENT_STAGE_FLOW_CLOSED__STABILITY_CONFIRMED__NEXT_STAGE_OWNER_PROMOTION_PENDING`
- current-stage blocker status: `NONE__CURRENT_STAGE_FLOW_CLOSED`

### T02 / PRODUCT_IDEA_VALIDATION

- flow_closure_status: `FLOW_CLOSED`
- business_promotion_status: `BUSINESS_NOT_PROMOTED`
- current line truth: `CURRENT_STAGE_FLOW_CLOSED__REUSABLE_LINE__POST_STAGE_OPEN_DEBT_TRACKED`
- current-stage blocker status: `NONE__CURRENT_STAGE_FLOW_CLOSED`

### T03 / COMPETITOR_REVERSE_MINING

- flow_closure_status: `FLOW_CLOSED`
- business_promotion_status: `BUSINESS_NOT_PROMOTED`
- current line truth: `CURRENT_STAGE_FLOW_CLOSED__REUSABLE_LINE__POST_STAGE_OPEN_DEBT_TRACKED`
- current-stage blocker status: `NONE__CURRENT_STAGE_FLOW_CLOSED`

### T04 / SUPPLY_CHAIN_BACKSOLVE

- flow_closure_status: `FLOW_CLOSED`
- business_promotion_status: `BUSINESS_NOT_PROMOTED`
- current line truth: `CURRENT_STAGE_FLOW_CLOSED__REUSABLE_LINE__POST_STAGE_OPEN_DEBT_TRACKED`
- current-stage blocker status: `NONE__CURRENT_STAGE_FLOW_CLOSED`
