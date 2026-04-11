# CODEX SELLERSPRITE Next Slice Summary (2026-04-10)

## Scope

This slice stayed inside the `amazon-selection-automation` sidecar repo and only touched the approved SellerSprite Playwright page path.

Exact scope:

- Repair Product Research replay so replay no longer stops at "applied but still unusable".
- Re-run fresh formal STEP1.
- Re-run fresh formal STEP4 from fresh STEP1 seed.
- Re-run STEP3 from fresh STEP1 market-entry binding.
- Rebuild STEP7 from fresh formal artifacts only.

Out of scope:

- SIF
- non-selection business lines
- unapproved API collectors
- pretending replay connectivity equals SellerSprite closure

## Current Git Truth After This Slice

- Repo-level current judgment remains `SELLERSPRITE_NIGHTLY_READY`.
- Business-level current judgment remains `SELLERSPRITE_NOT_CLOSED`.
- STEP1 artifact layer is now fresh and real through Product Research workbook export.
- STEP4 formal path is now fresh and real through page export-log download.
- STEP3 is still not closed; the current fresh blocker is a reproducible market-entry redirect loop, not auth illusion.
- STEP7 can rebuild from fresh real samples, but still holds because STEP2 business gate is still `HOLD` and STEP3 did not form a fresh market workbook.

## Product Replay Repair

### What was wrong before

The previous replay integration could rebuild a persistent profile on disk, but Product Research still reopened into a guest-only export surface after the collector restarted.

### What changed

- SellerSprite replay now distinguishes two replay modes:
  - `storage_state_copy`
  - `persistent_profile_seed`
- Product/benchmark/export-log surfaces now map to `persistent_profile_seed`, sourced from the owner-provided `SELLERSPRITE_KEYWORD_MINER_AUTH` storage state.
- Product/benchmark collectors no longer depend on reopening the replay profile directory alone.
- Instead, they now launch a fresh runtime persistent context and inject the owner storage state into that live context before page work starts.
- Market export was intentionally kept on its existing primary-profile/storage-state path so this slice did not widen replay scope beyond the Product/Benchmark problem.

### Result

Product Research replay is now genuinely usable for the formal collector path:

- real query surface opened
- row selection worked
- export-log handoff worked
- workbook download succeeded

## Fresh Rerun Results

### STEP1

- Status: `PASS`
- Reason code: `PASS`
- Evidence type: real workbook + real page-visible market-entry merge
- Key artifacts:
  - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/product_research_raw.json`
  - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/10_产品样本原始结果.csv`
  - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/11_产品样本种子池.csv`
  - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/12_产品样本下推结果.csv`
- Workbook:
  - `runs/manual/15_product_exports/20260410_next_slice_formal/Product-US-Last-30-days-209236.xlsx`
- Latest logs:
  - `logs/formal_next_slice_20260410/step1_product/latest_product_research_run.json`
  - `logs/formal_next_slice_20260410/step1_product_build/latest_product_build_run.json`

Fresh STEP1 facts:

- query rows: `120`
- parsed workbook rows: `60`
- seed rows: `46`
- gate rows: `46`
- `visible_market_entry_count = 60`

### STEP4

- Status: `PASS`
- Reason code: `PASS`
- Evidence type: real workbook via formal page export-log path
- Key artifacts:
  - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/benchmark_competitor_raw.json`
  - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/40_竞品基准结果.csv`
  - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/41_候选产品种子池.csv`
  - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/42_竞品基准下推结果.csv`
- Workbook:
  - `runs/manual/20_benchmark_exports/20260410_next_slice_formal/Competitor-US-Last-30-days-209270.xlsx`
- Latest logs:
  - `logs/formal_next_slice_20260410/step4_benchmark/latest_benchmark_export_run.json`
  - `logs/formal_next_slice_20260410/step4_benchmark_build/latest_benchmark_build_run.json`

Fresh STEP4 facts:

- raw items: `60`
- seed rows: `46`
- gate status: `PASS`
- seed source step: `STEP1_PRODUCT_GATE`
- manual override was not used

### STEP3

- Status: `FAILED`
- Reason code: `MARKET_PLAYWRIGHT_ERROR`
- Evidence type: real surface blocker
- Entry mode: `product_market_analysis`
- Entry source step: `STEP1_PRODUCT_SEED`
- Market entry URL came from fresh STEP1 seed, not from naked keyword search
- Latest logs:
  - `logs/formal_next_slice_20260410/step3_market_export/latest_run.json`
  - `logs/formal_next_slice_20260410/step3_market_export_auto/latest_run.json`

Fresh STEP3 facts:

- the current fresh `市场分析URL` now exists in `11_产品样本种子池.csv`
- both storage-state and auto retry reproduced the same blocker
- the blocker is:
  - `Page.goto: net::ERR_TOO_MANY_REDIRECTS`
  - target: `https://www.sellersprite.com/v2/market-research?...nodeIdPath=3375251:10971181011:706808011:7427858011...`
- current blocker is no longer "missing STEP1 market entry binding"
- current blocker is no longer the earlier generic auth illusion

No fresh STEP3 workbook formed in this slice, so there is still no fresh `30 / 31 / 32`.

### STEP7

- Status: `HOLD`
- Reason code: `STEP2_HOLD__REAL_SAMPLES_CONTINUED`
- Evidence type: fresh direct-artifact rebuild only
- Key artifacts:
  - `outputs/selection_runs/20260410_next_slice_formal_step7/02_generated_outputs/03_候选市场与候选品初筛池.csv`
  - `outputs/selection_runs/20260410_next_slice_formal_step7/02_generated_outputs/60_候选样品池.csv`
  - `outputs/selection_runs/20260410_next_slice_formal_step7/02_generated_outputs/60_候选样品池.md`
- Latest log:
  - `logs/formal_next_slice_20260410/step7_candidate_pool/latest_run.json`

Fresh STEP7 facts:

- intermediate rows: `46`
- final rows: `46`
- source is fresh STEP1 + fresh STEP4 only
- no old STEP3 artifact was borrowed
- no old STEP1/STEP4 artifact was borrowed

## Repo Files Changed In This Slice

- `scripts/keyword_chain_common.py`
- `scripts/benchmark_chain_common.py`
- `scripts/sellersprite_auth_replay.py`
- `scripts/export_benchmark_competitors.py`
- `scripts/export_product_research.py`
- `scripts/export_market_report.py`
- `scripts/temp_product_export_trigger_record.py`
- `scripts/temp_product_export_log_record.py`
- `reports/CODEX_SELLERSPRITE_NEXT_SLICE_SUMMARY_20260410.md`

## Local-only Assets Read Or Updated

Read/consumed:

- `playwright/auth/owner_recordings/SELLERSPRITE_KEYWORD_MINER_AUTH/*`
- `playwright/auth/owner_recordings/SELLERSPRITE_MARKET_RESEARCH_AUTH/*`
- `playwright/auth/login_replay_registry.json`

Updated local-only:

- `playwright/auth/owner_recordings/*/recording_manifest.json`
- `playwright/auth/login_replays/*.py`
- `playwright/auth/replay_backups/*`
- `logs/runtime_replay_profiles/*`
- `logs/formal_next_slice_20260410/*`
- `runs/manual/15_product_exports/20260410_next_slice_formal/*`
- `runs/manual/20_benchmark_exports/20260410_next_slice_formal/*`
- `runs/manual/10_market/20260410_next_slice_formal/*`

These assets remain local-only / ignored and must not be committed.

## Can SellerSprite Be Declared Closed?

No.

Current business truth stays:

- `SELLERSPRITE_NOT_CLOSED`

Reason:

- STEP1 is now fresh `PASS`
- STEP4 is now fresh `PASS`
- STEP3 still has no fresh `30 / 31 / 32`
- STEP2 business gate still remains `HOLD`

## Can Work Be Pushed To Other Business Lines?

No.

This slice materially improved SellerSprite formal-path recovery, but the repo still does not have a fresh closed SellerSprite chain for `claw machine / US`.

## Exact Next Slice

Repair STEP3 market-entry consumption for the fresh Product Research market-analysis handoff.

Minimal next slice:

1. Keep the current fresh STEP1 market-entry capture.
2. Investigate why the captured `/v2/market-research?...nodeIdPath=...` URL enters `ERR_TOO_MANY_REDIRECTS` when opened directly in a new collector context.
3. Prefer a page-visible handoff strategy if needed:
   - click the `市场分析` action from the live Product Research expanded row
   - capture the resulting page/new-tab state
   - continue export from that live handoff instead of raw `goto` only
4. Re-run fresh STEP3.
5. Rebuild STEP7 again from fresh formal artifacts after STEP3 truth is updated.
