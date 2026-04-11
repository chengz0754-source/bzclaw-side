# Shadow Runner Spec

## 1. Scope

This spec fixes Machine B as a `shadow candidate runner` for business tracks,
candidate skill surfaces, and bounded probes.

The role is intentionally narrower than approval:

- shadow runs are real execution
- shadow runs are evidence-producing
- shadow runs are comparison-ready
- shadow runs are not business closure

As of `2026-04-12`, no repo-visible A-machine `A3` or `A8` return artifacts were
found under `E:\bzclaw-side`, so this spec also falls back to the package A2 /
scorebook / proof materials.

## 2. What Counts As A Shadow Candidate

Current B-side shadow candidates include:

- script-first business chains under `scripts/**`
  - STEP1 product research
  - STEP2 keyword chain
  - STEP3 market report
  - STEP4 benchmark competitor
  - STEP7 candidate pool
  - SIF surface collection
  - SIF enrichment
- controlled dry-run packaging
  - `scripts/run_nightly_selection_acceptance.py`
- auth replay probes and bounded recovery attempts
- approved skills when they are deliberately exercised in canary mode instead of
  approved mode

## 3. Shadow Execution Classes

Allowed shadow execution classes are:

- `dry_run`
- `shadow`
- `smoke`
- `probe`
- `limited_shadow`

Typical current B carriers:

- `outputs/selection_runs/<batch_id>/00_run_summary.md`
- `outputs/selection_runs/<batch_id>/00_run_manifest.json`
- `outputs/selection_runs/<batch_id>/03_logs/shadow_run_receipt.json`
- `logs/**/latest_run.json`
- `logs/**/latest_*_run.json`

## 4. Mandatory Object Set For Shadow Runs

Shadow posture must still resolve into standard objects.

### Required runtime objects

- `ArtifactReturnEnvelope`
- `EvidencePack`
- `ShadowRunReceipt`
- `SkillObservation`

### Required closeout slots

- `ExecutionReceipt`
  - may still be satisfied by current B precursors such as `latest_run.json`
- `VerificationResult`
  - may remain `HOLD` or `NOT_RUN`
- `RollbackTrace`
  - may remain present as a slot even when rollback is not triggered

### Conditional objects

- `ModelInferenceReceipt`
  - only when a shadow run performs a real model call
- `HumanReviewEntry`
  - placeholder-only

## 5. Standard Shadow Closeout Fields

Every shadow run must produce or reserve the following closeout facts:

- `input_summary`
- `output_summary`
- `kpi_delta`
- `verify_status`
- `rollback_triggered`
- `error_type`
- `operator_score_placeholder`

Recommended `kpi_delta` examples:

- row-count delta
- artifact-count delta
- workbook download success / failure delta
- auth-hit count
- trace count
- retry count
- model latency delta when applicable

## 6. Comparison Rule

Shadow does not require a publish baseline, but it does require a comparison
surface.

Preferred comparison anchors:

- last stable run summary for the same surface
- last stable `*_output_index.*`
- last stable workbook / raw artifact pair
- last stable auth incident / replay state for the same surface family
- for approved-skill canaries, the last approved closeout packet

If no comparison anchor exists:

- the run may still execute
- `verify_status` should stay `NOT_RUN` or `HOLD`
- the missing comparator must stay explicit in `SkillObservation`

## 7. Failure Taxonomy For Shadow Runs

Current normalized shadow failure classes should remain explicit:

- `AUTH_REQUIRED`
- `EXPORT_LOG_BLOCKED`
- `SOURCE_EMPTY`
- `UPSTREAM_CHAIN_BLOCKED`
- `MODEL_UNAVAILABLE`
- `VERIFY_FAILED`
- `ROLLBACK_TRIGGERED`
- `UNAUTHORIZED_ATTEMPT`
- `RUNTIME_PATH_MISSING`
- `OUTPUT_MISSING`

Native step `reason_code` values from current scripts must be preserved instead
of being replaced by vague summary labels.

## 8. Observation Rule

Shadow runs are allowed to collect and emit:

- workbooks
- raw JSON outputs
- receipts
- screenshots
- traces
- auth incidents
- nightly output summaries

These surfaces map into:

- `EvidencePack`
- `ArtifactReturnEnvelope`
- `SkillObservation`
- `ShadowRunReceipt`

These surfaces do not map into:

- final business verdict
- promotion decision
- publish truth

## 9. Rollback Rule

Shadow rollback stays bounded:

- discard a failed shadow package
- revert to last stable local input snapshot
- restore previous local storage state or profile backup
- link to rollback evidence through `RollbackTrace`

Shadow rollback may not:

- overwrite A-side truth
- self-promote a candidate
- self-retire a surface

## 10. Current Default Shadow Carrier

Current repo-visible default shadow carrier is:

- `scripts/run_nightly_selection_acceptance.py`

Its current behavior already proves the correct posture:

- emits archive-shaped dry-run packages
- emits `ArtifactReturnEnvelope`
- emits `EvidencePack`
- emits `ShadowRunReceipt`
- keeps the run explicitly dry-run

That is the baseline Machine B should keep using for shadow candidate closeout.
