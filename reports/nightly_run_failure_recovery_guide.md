# Nightly Run Failure Recovery Guide

## Recovery Principle

This repository is fail-closed by design. If a nightly run cannot prove a live chain step, it must stay `HOLD` or `FAIL`. Never replace blocked truth with guessed data, copied business judgment, or manually fabricated PASS rows.

## First Triage

When a nightly acceptance run does not pass:

1. Open `outputs/selection_runs/<batch_id>/03_logs/nightly_acceptance_summary.json`.
2. Read the top-level `status` and `reason_code`.
3. Identify the first blocked step in `steps[]`.
4. Fix that upstream chain first.
5. Re-run with a **new** `batch_id`.

Do not delete the blocked archive unless you are explicitly cleaning local ignored artifacts.

## Common Failure Modes

### 1. `Acceptance run dir already exists`

Meaning:

- the requested `batch_id` already has an archive directory

Recovery:

1. Keep the old batch as evidence.
2. Pick a new `batch_id`.
3. Re-run the acceptance script.

### 2. `BLOCKED_BY_UPSTREAM_CHAIN__STEP2_ALL_RAW_RUNS_BLOCKED`

Meaning:

- SellerSprite STEP2 raw collection is still blocked
- the orchestrator cannot honestly consume a real `22_关键词证据词池下推结果.csv`

Recovery:

1. Inspect `logs/keyword_chain/latest_keyword_build_run.json`.
2. Fix SellerSprite auth or page-surface issues in:
   - `scripts/export_keyword_research.py`
   - `scripts/export_keyword_trend.py`
   - `scripts/build_keyword_evidence_pool.py`
3. Re-verify STEP2 standalone before re-running full acceptance.

### 3. `SIF_AUTH_REQUIRED`

Meaning:

- SIF profile/bootstrap exists, but authenticated detail/search access is not reusable

Recovery:

1. Inspect:
   - `logs/sif_surfaces/latest_bootstrap_run.json`
   - `logs/sif_surfaces/latest_detail_run.json`
   - `logs/sif_surfaces/latest_search_run.json`
2. Re-run:

```powershell
.\.venv\Scripts\python.exe scripts\bootstrap_sif_auth.py --probe-login-surface --headless
```

3. If auth is still blocked, repair the SIF login/bootstrap path before claiming Step 5 readiness.
4. Do not backfill SIF metrics by hand.

### 4. `BLOCKED_BY_SIF_OR_POOL_ALIGNMENT`

Meaning:

- candidate-pool rows and SIF rows could not be aligned into a truthful Step 5 package
- or the pool is still blocked upstream, so alignment must stay `HOLD`

Recovery:

1. Confirm `60_候选样品池.csv` exists in the current batch.
2. Confirm `50/51/52` exist and keep the same primary keys:
   - `样品ID`
   - fallback `样品ASIN`
3. Inspect:
   - `candidate_pool_summary.json`
   - `sif_detail_surface_probe.json`
   - `sif_search_surface_probe.json`
   - `sif_enrichment_daytime_pack_summary.json`
4. Fix the earliest missing or blocked upstream piece, then re-run acceptance with a new `batch_id`.

### 5. `REQUIRED_OUTPUT_MISSING`

Meaning:

- at least one required file did not land in `02_generated_outputs/`
- or the acceptance script could not complete one of its mandatory stages

Recovery:

1. Check the missing filename in `nightly_acceptance_summary.json`.
2. Run the corresponding stage directly and inspect its stderr/stdout.
3. Do not mark the run accepted until the missing artifact is present in the canonical location.

### 6. `STEP3_PASS_SEED_MISSING` or benchmark-trigger failures

Meaning:

- the current direction or keyword did not yield a valid upstream seed for Step 4

Recovery:

1. Inspect `batch_queue_status.csv`.
2. Confirm whether the direction was legitimately blocked in Step 1 to Step 3.
3. Keep the failure as data truth if upstream seeds do not exist.
4. Do not substitute market outputs for benchmark outputs.

## Safe Re-Run Sequence

Use this order after an upstream fix:

1. Re-test the repaired upstream script in isolation.
2. Confirm it now emits canonical outputs in its own batch directory.
3. Run `scripts/run_nightly_selection_acceptance.py` with a fresh `batch_id`.
4. Verify the new archive shape and summary.
5. Compare the new `reason_code` against the previous blocked batch.

## Input Safety Rules

- Never auto-fill manual-only fields.
- Never delete `inputs/selection_run_current/` during acceptance triage.
- Never reuse a blocked batch directory as the rerun target.
- Never move runtime outputs into git.

## Escalation Boundary

Escalate to manual daytime handling when:

- auth depends on an interactive human login
- a site surface materially changed and selectors are no longer trustworthy
- business interpretation would be required to decide PASS versus HOLD

Until those conditions are resolved, the correct operator action is to preserve the blocked run and keep the repo status at `HOLD`, not to force an acceptance success conclusion.
