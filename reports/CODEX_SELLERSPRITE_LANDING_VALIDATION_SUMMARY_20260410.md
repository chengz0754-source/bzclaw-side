# CODEX SellerSprite Landing Validation Summary (2026-04-10)

## Current Git Truth

- Program truth remains `PURPOSE_ROUTED / PLAYWRIGHT_ONLY / SELLERSPRITE_FIRST / SIF_AFTER_SHORTLIST`.
- Repo-level SellerSprite truth remains `SELLERSPRITE_NIGHTLY_READY`.
- Business-level SellerSprite truth remains `SELLERSPRITE_NOT_CLOSED`.
- `claw machine` remains `PRODUCT_IDEA_VALIDATION`.
- `T02 STEP3_REQUIRED = false`.
- `T02 STEP3_OPTIONAL_ENRICHMENT = true`.
- This slice only reran:
  - `T02 STEP3`
  - `T02 STEP7`

## Why This Round Did Not Reopen Route Or Metadata Debate

- The repo already absorbed:
  - purpose-routed execution
  - formal STEP1 -> STEP3 handoff object
  - replay-family / replay-consumption repair
- The remaining question for this slice was narrower:
  - whether the latest owner-provided Product Research replay asset could move STEP3 forward when consumed by the current repo path
- So this slice stayed on:
  - latest owner-asset intake
  - local replay metadata refresh
  - minimum rerun only

## Five-Box Intake Result

All 5 boxes were read before repo execution:

- `BOX_1__PROMPT_AND_PROJECT_TRUTH__20260410.zip`
- `BOX_2__OWNER_REPLAY_ASSETS__20260410.zip`
- `BOX_3__PLAYWRIGHT_PROFILES_FILTERED__20260410.zip`
- `BOX_4A__PLAYWRIGHT_SCREENSHOTS_AUTH_AND_BENCHMARK__20260410.zip`
- `BOX_5__PLAYWRIGHT_SCREENSHOTS_KEYWORD_FLOW__20260410.zip`

High-signal intake truth:

- Box 3 confirms the filtered profile bundle exists, but profiles remain supporting input only.
- Box 4A screenshots continue to show repeated Product Research / market-entry auth incidents on the same surface family, which supports but does not override runtime truth.
- Box 5 screenshots continue to support STEP2 keyword-flow history, not this slice's primary blocker.

## Why This Owner Asset Supersedes The Older Drifted Local Replay State

This slice did absorb the latest owner asset from Box 2 as the execution input for Product Research replay.

What superseded the prior local state was not a new repo truth claim, but a local-only asset correction:

- the local Product Research replay directory had drifted away from its own manifest
- the Box 2 quartet was internally self-consistent:
  - `owner_fake_login_recording.py`
  - `recording_manifest.json`
  - `storage_state.json`
  - `composite_probe_state.json`
- the local replay directory was not self-consistent before refresh:
  - local `recording_manifest.json` already claimed:
    - `recording_script_sha1 = 5c8519dab8896089a964d0485220e5e9b2f60516`
    - `storage_state_sha1 = bdbe2e6bdd559c847719399b1987004a4b96c683`
  - but the actual local files did not match those hashes

After refresh, local Product Research replay assets now exactly match Box 2:

- `owner_fake_login_recording.py` SHA1 = `5c8519dab8896089a964d0485220e5e9b2f60516`
- `storage_state.json` SHA1 = `bdbe2e6bdd559c847719399b1987004a4b96c683`

## Conflict Note: Prompt Expectation vs Visible Box 2 Runtime Asset

This slice must explicitly preserve one conflict instead of hiding it.

Prompt-level and project-progress descriptions say the latest corrected owner asset should already include:

- open Product Research
- search `claw machine`
- trigger login
- click row-scoped `市场分析`
- `expect_popup()`
- save storage state after handoff

But the currently visible execution input in Box 2 does **not** expose that click-chain in the script body.

Visible Box 2 `owner_fake_login_recording.py` only shows:

- open login callback to `v3/product-research?market=US`
- close page
- `context.storage_state(...)`

So this slice treated the docs as:

- business expectation / judgment

and treated the current Box 2 files as:

- the actual local execution input

That means Box 2 superseded the older drifted local replay files, but it did **not** prove a visible row-scoped `市场分析` recording chain by script inspection alone.

## Replay Metadata Refresh Result

### Local-only files refreshed

- `playwright/auth/owner_recordings/SELLERSPRITE_PRODUCT_RESEARCH_AUTH/owner_fake_login_recording.py`
- `playwright/auth/owner_recordings/SELLERSPRITE_PRODUCT_RESEARCH_AUTH/recording_manifest.json`
- `playwright/auth/owner_recordings/SELLERSPRITE_PRODUCT_RESEARCH_AUTH/storage_state.json`
- `playwright/auth/owner_recordings/SELLERSPRITE_PRODUCT_RESEARCH_AUTH/composite_probe_state.json`

Backups were written to:

- `playwright/auth/replay_backups/20260411_landing_validation_product_research/`

### Registry refresh command

```powershell
.\.venv\Scripts\python.exe scripts\register_owner_sellersprite_replays.py
```

### Refresh truth

- `SELLERSPRITE_PRODUCT_RESEARCH_AUTH` remains registered with:
  - `has_replay = true`
  - `source_surface_family = SELLERSPRITE_PRODUCT_RESEARCH_AUTH`
  - `applicable_modules = ["market_export", "product_research"]`
- registry `last_verified_at` moved to `2026-04-11T00:13:42+08:00`
- Box 2 storage state is not empty:
  - cookies = `31`
  - origins = `1`
  - visible Product Research-related localStorage traces include keys like:
    - `productResearchOrder`
    - `closeMarketAiGuideNew`

## T02 STEP3 Rerun

### Command

```powershell
.\.venv\Scripts\python.exe scripts\export_market_report.py --context-row-index 2 --output-dir runs/manual/10_market/20260411_t02_landing_validation --log-dir logs/formal_t02_landing_validation_20260411/step3_market_export --entry-mode product_market_analysis --market-handoff-jsonl outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/13_step1_market_handoff.jsonl --max-attempts 1 --execution-mode auto
```

### Result

- status: `FAILED`
- reason_code: `MARKET_LOGIN_REDIRECT_BEFORE_REBIND`
- result type: stable reproducible blocker
- not `real workbook`
- not `real SOURCE_EMPTY`

### Evidence

- run log:
  - `logs/formal_t02_landing_validation_20260411/step3_market_export/latest_run.json`
- auth incident:
  - `logs/sellersprite_auth_incidents/incidents/2026-04-11T00-14-52-08-00-market_export-market_open_product_entry_warmup-SELLERSPRITE_PRODUCT_RESEARCH_AUTH.json`

### Current deeper truth from this rerun

- handoff object was consumed first
- replay was attempted and succeeded at the registry / profile-seeding layer
- execution mode became `persistent_profile`
- selected sample stayed:
  - `sample_id = PSMP_969FF7CC8E`
  - `sample_asin = B07P44GKJR`
- failure stage stayed:
  - `market_open_product_entry_warmup`
- login redirect timing stayed:
  - `before_rebind`
- rows never became visible
- market-analysis link never became visible
- workbook download was never attempted
- session bundle was still absent:
  - `market_session_bundle_path = ""`
  - `session_bundle_consumed = false`

### Interpretation

This slice did move execution input forward in one important way:

- the local replay directory is now consistent with the latest Box 2 asset instead of a drifted local state

But repo-visible runtime truth did **not** move past the same Product Research warmup redirect barrier.

So the current blocker is still closer to:

- `owner asset insufficiency for handoff-session replay`
- or a still-unrecovered `replayability mismatch` at Product Research warmup continuity

It is not yet justified to call this a final business-surface blocker.

## T02 STEP7 Rerun

### Command

```powershell
.\.venv\Scripts\python.exe scripts\build_candidate_pool.py --context-row-index 2 --step1-gate-csv outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/12_产品样本下推结果.csv --step2-gate-csv outputs/selection_runs/20260410_auth_replay_formal/02_generated_outputs/22_关键词证据词池下推结果.csv --step4-gate-csv outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/42_竞品基准下推结果.csv --output-dir outputs/selection_runs/20260411_t02_landing_validation_step7/02_generated_outputs --log-dir logs/formal_t02_landing_validation_20260411/step7_candidate_pool --batch-id STEP7_T02_LANDING_VALIDATION_20260411
```

### Result

- status: `HOLD`
- reason_code: `PRODUCT_FEASIBLE__MARKET_ABSTRACTION_PENDING`
- row_count: `46`

### Artifacts

- `outputs/selection_runs/20260411_t02_landing_validation_step7/02_generated_outputs/03_候选市场与候选品初筛池.csv`
- `outputs/selection_runs/20260411_t02_landing_validation_step7/02_generated_outputs/60_候选样品池.csv`
- `outputs/selection_runs/20260411_t02_landing_validation_step7/02_generated_outputs/60_候选样品池.md`
- run log:
  - `logs/formal_t02_landing_validation_20260411/step7_candidate_pool/latest_run.json`

### Projection meaning

- real product / benchmark evidence still projects forward
- market abstraction remains pending
- this is still a pending projection, not SellerSprite closure

## SellerSprite Closure Judgment

SellerSprite remains `SELLERSPRITE_NOT_CLOSED`.

Nothing in this slice justifies a closure claim because T02 STEP3 still did not produce:

- fresh `30 / 31 / 32`
- or real `SOURCE_EMPTY`

## Repo-Visible Changes In This Slice

- added:
  - `reports/CODEX_SELLERSPRITE_LANDING_VALIDATION_SUMMARY_20260410.md`

No repo code path was rewritten in this slice. The executable change was local-only replay asset refresh plus minimum rerun.

## Next Exact Slice

Keep scope narrow and do not expand to T03 / T04 / SIF.

Next slice should do exactly this:

1. keep the refreshed Box 2 Product Research replay asset as the current local execution input
2. probe whether a real session-continuity bundle can be materialized from a successful same-session Product Research handoff surface, instead of relying only on storage-state seeding
3. if a valid `13a_step1_market_session_bundle.json` can be formed, rerun:
   - `T02 STEP3`
   - `T02 STEP7`
4. if not, the next blocker judgment should stay on:
   - Product Research handoff-session replay insufficiency
   - not route semantics
   - not raw direct market URL as primary path
