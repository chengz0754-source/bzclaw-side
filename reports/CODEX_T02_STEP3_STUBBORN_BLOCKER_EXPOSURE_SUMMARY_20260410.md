# CODEX T02 STEP3 Stubborn Blocker Exposure Summary (2026-04-10)

## Current Git Truth

- Program current remains purpose-routed.
- Repo-level SellerSprite truth remains `SELLERSPRITE_NIGHTLY_READY`.
- Business-level SellerSprite truth remains `SELLERSPRITE_NOT_CLOSED`.
- T02 remains `PRODUCT_IDEA_VALIDATION`.
- T02 keeps `STEP3_REQUIRED = false`.
- T02 keeps `STEP3_OPTIONAL_ENRICHMENT = true`.
- T02 STEP3 remains the current first live blocker.

## Was The Stubborn Problem Solved?

No.

This slice did repair the previously visible replay binding mismatch and replay consumption mismatch, but T02 STEP3 still does not land a real workbook and still does not land a real `SOURCE_EMPTY`.

## What Was Fixed In This Slice

### Replay lineage repair

Before this slice:

- registry surface family: `SELLERSPRITE_PRODUCT_RESEARCH_AUTH`
- runtime incident surface family: `SELLERSPRITE_PRODUCT_RESEARCH_AUTH`
- manifest source surface family: `SELLERSPRITE_KEYWORD_MINER_AUTH`
- manifest storage state path: keyword-miner owner recording

That was not metadata-only. It was structural, because the replay application actually seeded Product Research from the wrong owner recording.

After this slice:

- registry surface family: `SELLERSPRITE_PRODUCT_RESEARCH_AUTH`
- runtime consumed surface family: `SELLERSPRITE_PRODUCT_RESEARCH_AUTH`
- manifest source surface family: `SELLERSPRITE_PRODUCT_RESEARCH_AUTH`
- manifest storage state path: `playwright/auth/owner_recordings/SELLERSPRITE_PRODUCT_RESEARCH_AUTH/storage_state.json`

### Replay consumption repair

Before this slice, `export_market_report.py` still opened persistent mode from the main profile path and ignored the replay profile path used by persistent replay.

After this slice:

- `export_market_report.py` now uses `preferred_sellersprite_profile_dir()`
- when the replay profile is preferred, it launches a runtime-seeded persistent context through `launch_runtime_seeded_persistent_context()`
- the run log now captures:
  - execution mode actually used
  - runtime replay surface used
  - runtime replay profile directory
  - exact failure stage name
  - redirect timing
  - whether rebind began
  - whether rows became visible
  - whether the market-analysis link became visible
  - whether popup / same-tab navigation happened
  - whether workbook download was attempted

### Product Research warmup probe

This slice also tried a Product Research-specific warmup:

1. open base `v3/product-research?market=US`
2. then open the captured STEP1 results URL

This was meant to test whether the remaining issue was only deep-link reopening. The warmup still redirected to login, so the blocker is earlier than exact sample rebind.

## Replay Lineage Summary

### Repo-visible changes

- `scripts/sellersprite_auth_replay.py`
  - `SELLERSPRITE_PRODUCT_RESEARCH_AUTH` now sources itself instead of `SELLERSPRITE_KEYWORD_MINER_AUTH`
  - applicable modules now include `market_export`
- `scripts/sellersprite_auth_registry.py`
  - default registry metadata now reflects Product Research usage by both `product_research` and `market_export`
- `scripts/export_market_report.py`
  - market export now consumes replay-backed persistent contexts the same way as benchmark/product chains
  - market export now exposes full chain execution details in the run record

### Local-only assets updated

- `playwright/auth/owner_recordings/SELLERSPRITE_PRODUCT_RESEARCH_AUTH/recording_manifest.json`
- `playwright/auth/login_replay_registry.json`
- `playwright/auth/login_replays/sellersprite_product_research_auth_replay.py`

### Final replay lineage state

- registered family: `SELLERSPRITE_PRODUCT_RESEARCH_AUTH`
- consumed family at runtime: `SELLERSPRITE_PRODUCT_RESEARCH_AUTH`
- mismatch after repair: none
- remaining problem after repair: the Product Research owner replay state is still not usable on the Product Research handoff reopening surface

## T02 STEP3 Rerun Result

### Final rerun used for judgment

- log: `logs/formal_t02_step3_stubborn_20260410/step3_market_export_v3/latest_run.json`
- status: `FAILED`
- reason_code: `SELLERSPRITE_AUTH_REQUIRED`
- result type: stable reproducible blocker

### Full chain exposure

1. Handoff object selected
   - path: `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/13_step1_market_handoff.jsonl`
   - selected sample: `PSMP_969FF7CC8E / B07P44GKJR`
   - selected candidate market: `Arcade & Table Games`
   - selected visible market-analysis href: `https://www.sellersprite.com/v2/market-research?marketId=1&nodeIdPath=3375251:10971181011:706808011:7427858011&nodeIdPathEqual=true`

2. Replay applied
   - surface family: `SELLERSPRITE_PRODUCT_RESEARCH_AUTH`
   - manifest path: `playwright/auth/owner_recordings/SELLERSPRITE_PRODUCT_RESEARCH_AUTH/recording_manifest.json`
   - snippet path: `playwright/auth/login_replays/sellersprite_product_research_auth_replay.py`
   - replay kind: `persistent_profile_seed`
   - manifest source surface family: `SELLERSPRITE_PRODUCT_RESEARCH_AUTH`
   - source storage state path: `playwright/auth/owner_recordings/SELLERSPRITE_PRODUCT_RESEARCH_AUTH/storage_state.json`

3. Execution mode actually used
   - `persistent_profile`
   - execution warning shows runtime replay consumption:
     - `using_runtime_replay_surface=SELLERSPRITE_PRODUCT_RESEARCH_AUTH`
     - runtime profile dir under `logs/runtime_replay_profiles/...`

4. Product Research warmup phase
   - attempted URL: `https://www.sellersprite.com/v3/product-research?market=US`
   - final URL: `https://www.sellersprite.com/w/user/login?callback=%2Fv3%2Fproduct-research%3Fmarket%3DUS`
   - failure stage name: `market_open_product_entry_warmup`
   - login redirect timing: `before_rebind`

5. Consequences
   - exact sample rebind: not attempted
   - rows visible: `false`
   - market-analysis link visible: `false`
   - popup/new-tab/context inheritance: `not_attempted`
   - workbook download attempted: `false`

### Interpretation

The replay binding mismatch is no longer the active blocker.

The active blocker is now fully opened:

- Product Research replay is structurally aligned
- runtime replay consumption is structurally aligned
- but the Product Research owner recording still cannot open even the base Product Research surface in an authenticated usable state during STEP3 handoff reopening

## T02 STEP7 Rerun Result

- log: `logs/formal_t02_step3_stubborn_20260410/step7_candidate_pool_v2/latest_run.json`
- status: `HOLD`
- reason_code: `PRODUCT_FEASIBLE__MARKET_ABSTRACTION_PENDING`
- row count: `46`

Artifacts:

- `outputs/selection_runs/20260410_t02_step7_after_stubborn_step3_v2/02_generated_outputs/03_候选市场与候选品初筛池.csv`
- `outputs/selection_runs/20260410_t02_step7_after_stubborn_step3_v2/02_generated_outputs/60_候选样品池.csv`
- `outputs/selection_runs/20260410_t02_step7_after_stubborn_step3_v2/02_generated_outputs/60_候选样品池.md`

Meaning:

- STEP1 and STEP4 remain real usable sources
- STEP3 still contributes no fresh workbook and no fresh `SOURCE_EMPTY`
- Candidate Pool remains a downgrade projection, not a closure claim

## SellerSprite Closure Judgment

SellerSprite remains `SELLERSPRITE_NOT_CLOSED`.

Nothing in this slice justifies a closure claim.

## Manual Owner Intervention Required?

Yes.

The current code path now shows:

- the correct Product Research surface family is chosen
- the correct Product Research manifest is chosen
- the correct Product Research storage state is chosen
- the replay-backed runtime persistent context is actually consumed

Yet Product Research still redirects to login at warmup before rebind begins.

That means the next most likely blocking asset is the owner recording state itself, not the current repo-side binding logic.

## Next Exact Slice

1. Refresh or re-record `SELLERSPRITE_PRODUCT_RESEARCH_AUTH` owner state.
2. Re-register only that Product Research replay asset.
3. Rerun T02 STEP3 with the existing handoff object first.
4. If Product Research warmup finally opens, continue to:
   - exact sample rebind
   - visible market-analysis click
   - market workbook / `SOURCE_EMPTY` judgment
5. Then rerun T02 STEP7 once more.
