# CODEX T02 STEP3 Handoff Object Summary (2026-04-10)

## Current Git Truth

- Program current remains purpose-routed.
- Repo-level SellerSprite truth remains `SELLERSPRITE_NIGHTLY_READY`.
- Business-level SellerSprite truth remains `SELLERSPRITE_NOT_CLOSED`.
- T02 remains `PRODUCT_IDEA_VALIDATION`.
- T02 keeps `STEP3_REQUIRED = false`.
- T02 keeps `STEP3_OPTIONAL_ENRICHMENT = true`.
- The current first live blocker for T02 remains STEP3, not STEP2, not SIF.

## Why `PRODUCT_RESULT_ROWS_MISSING` Was Not The True Root Cause

The prior STEP3 path still reopened Product Research, reran the query, and depended on rows being visible again before clicking `市场分析`. That meant the system had no durable continuity object between:

- successful STEP1 truth
- and live STEP3 market-entry action

So `PRODUCT_RESULT_ROWS_MISSING` was only the last visible symptom of a weaker continuity model. The true missing object was a formal, replayable STEP1 -> STEP3 handoff object.

## Handoff-Object Fix Implemented

### Materialized object

STEP1 build now emits:

- `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/13_step1_market_handoff.jsonl`

Each record includes:

- `task_id`
- `purpose_type`
- `run_name`
- `direction_id`
- `keyword`
- `site`
- `sample_id`
- `sample_asin`
- `sample_title`
- `selected_product_research_url`
- `selected_visible_market_analysis_href`
- `selected_candidate_market_name`
- `selected_market_path`
- `handoff_capture_status`
- `capture_timestamp`

The current T02 handoff object was materialized from the fresh STEP1 PASS product artifact and points to the exact visible Product Research results URL plus the exact visible `市场分析` href for sample `PSMP_969FF7CC8E / B07P44GKJR`.

### STEP3 consumption order

`scripts/export_market_report.py` now consumes Product-form STEP3 in this order:

1. handoff object
2. exact sample rebind on the reopened captured Product Research results page
3. page-visible `市场分析` click handoff
4. raw direct market URL only as supporting fallback

Generic query rerun is no longer the mainline path for this slice.

### Rebind behavior

STEP3 now prefers stable identifiers from STEP1 truth:

- `sample_id`
- `sample_asin`
- `sample_title`

It waits for Product Research result rows on the captured results URL, scores visible rows against the selected ASIN/title, and only then tries to click the row-scoped visible `市场分析` link.

### Failure taxonomy

This slice formalized or preserved these reason codes:

- `STEP1_MARKET_HANDOFF_OBJECT_MISSING`
- `STEP1_MARKET_HANDOFF_REBIND_FAILED`
- `PRODUCT_RESULT_ROWS_MISSING`
- `PRODUCT_MARKET_ANALYSIS_LINK_NOT_VISIBLE`
- `MARKET_SOURCE_EMPTY`
- `MARKET_PLAYWRIGHT_ERROR`
- `MARKET_WORKBOOK_PASS`

## T02 STEP3 Rerun Result

### Materialization run

- status: `PASS`
- output: `13_step1_market_handoff.jsonl`
- log: `logs/formal_t02_step3_handoff_20260410/step1_handoff_materialize/latest_product_build_run.json`

### Live rerun

Two live reruns were executed:

1. `auto`
2. `storage_state`

Both produced the same result:

- status: `FAILED`
- reason_code: `SELLERSPRITE_AUTH_REQUIRED`
- result type: stable reproducible blocker
- not a workbook pass
- not a real `SOURCE_EMPTY`

Primary logs:

- `logs/formal_t02_step3_handoff_20260410/step3_market_export/latest_run.json`
- `logs/formal_t02_step3_handoff_20260410/step3_market_export_storage/latest_run.json`

What changed materially:

- the blocker is no longer `PRODUCT_RESULT_ROWS_MISSING`
- the run now reaches the handoff-object entry and tries to open the captured Product Research results surface
- the Product Research surface immediately redirects to login before the exact sample rebind can begin

So the new visible blocker is sharper:

- current blocker surface: `SELLERSPRITE_PRODUCT_RESEARCH_AUTH`
- current blocker stage: `market_open_product_entry`
- current blocker meaning: the handoff object is present and selected, but the replayed Product Research auth state is still not usable for STEP3

## T02 STEP7 Rerun Result

Command used only fresh formal artifacts:

- fresh STEP1 gate: `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/12_产品样本下推结果.csv`
- fresh STEP2 gate: `outputs/selection_runs/20260410_auth_replay_formal/02_generated_outputs/22_关键词证据词池下推结果.csv`
- fresh STEP4 gate: `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/42_竞品基准下推结果.csv`
- no old STEP3 gate was borrowed

Result:

- status: `HOLD`
- reason_code: `PRODUCT_FEASIBLE__MARKET_ABSTRACTION_PENDING`
- final row count: `46`

Artifacts:

- `outputs/selection_runs/20260410_t02_step7_after_handoff_object/02_generated_outputs/03_候选市场与候选品初筛池.csv`
- `outputs/selection_runs/20260410_t02_step7_after_handoff_object/02_generated_outputs/60_候选样品池.csv`
- `outputs/selection_runs/20260410_t02_step7_after_handoff_object/02_generated_outputs/60_候选样品池.md`

Meaning:

- T02 still has real product/competitor feasibility evidence
- broad market mapping is still pending
- Candidate Pool does not claim SellerSprite closure

## SellerSprite Closure Judgment

SellerSprite remains `SELLERSPRITE_NOT_CLOSED`.

This slice repaired continuity truth for STEP3, but did not produce:

- fresh `30 / 31 / 32`
- or a real `SOURCE_EMPTY`

The current first blocker is now a clearer live auth blocker on the Product Research handoff surface.

## Manual Owner Intervention Requirement

Manual owner intervention is **not yet required** for this slice.

Current evidence shows the registered `SELLERSPRITE_PRODUCT_RESEARCH_AUTH` replay is still backed by a manifest whose `source_surface_family` is `SELLERSPRITE_KEYWORD_MINER_AUTH`. That points to a local replay binding problem first, not yet a proven need for a brand-new owner recording.

## Next Exact Slice

Do not reopen single-path logic. Do not move SIF earlier.

Next slice should do exactly this:

1. repair the local `SELLERSPRITE_PRODUCT_RESEARCH_AUTH` replay binding so STEP3 opens the captured Product Research results page in a truly authenticated usable state
2. rerun T02 STEP3 again using the existing handoff object first
3. only if STEP3 truth changes, rerun T02 STEP7 once more
