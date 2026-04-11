# B Runtime Observation Schema

## 1. Scope

This document defines how one Machine B run should be read as a single
observation bundle without inventing a second object family.

Current rule on `2026-04-12`:

- use canonical A2 object names where available
- keep `ModelInferenceReceipt` and `ShadowRunReceipt` as B/V3 intake targets
- when A3 or A8 real return schemas arrive, replace placeholder field details
  with the real host definitions

## 2. Runtime Observation Bundle

Every B-side run should be interpretable as this object set:

- `SkillObservation`
  - governance anchor for run closeout facts
- `ArtifactReturnEnvelope`
  - run-level carrier
- `EvidencePack`
  - evidence index
- `ExecutionReceipt`
  - generic runtime receipt
- `VerificationResult`
  - verify result or placeholder
- `RollbackTrace`
  - rollback fact or placeholder
- optional `ModelInferenceReceipt`
  - only when a real model call occurred
- optional `ShadowRunReceipt`
  - only for shadow / dry-run / smoke / probe posture
- optional `HumanReviewEntry`
  - operator score placeholder only

No single new B-only object name is introduced here. The bundle is only a way to
read the current objects together.

## 3. Current Observed Runtime Anchors

Observed local runtime examples on this machine still live under the business
execution repo:

- workbooks
  - `E:\选品文件夹\amazon-selection-automation\runs\manual\15_product_exports\20260410_next_slice_formal\Product-US-Last-30-days-209236.xlsx`
  - `E:\选品文件夹\amazon-selection-automation\runs\manual\20_benchmark_exports\20260410_next_slice_formal\Competitor-US-Last-30-days-209270.xlsx`
- screenshots
  - `E:\选品文件夹\amazon-selection-automation\playwright\screenshots\sellersprite_auth_incidents\2026-04-11T235410_0800-benchmark_export-stage_b_export_log_baseline-auth.png`
- traces
  - `E:\选品文件夹\amazon-selection-automation\playwright\traces\playwright-smoke.zip`
- auth incidents
  - `E:\选品文件夹\amazon-selection-automation\logs\sellersprite_auth_incidents\latest_auth_incident.json`
- step receipts
  - `E:\选品文件夹\amazon-selection-automation\logs\candidate_pool\latest_run.json`
  - `E:\选品文件夹\amazon-selection-automation\logs\benchmark_chain\latest_benchmark_export_run.json`
- archive-shaped run outputs
  - `E:\选品文件夹\amazon-selection-automation\outputs\selection_runs\20260407_090101\00_run_summary.md`

Canonical prompt repo remains:

- `E:\bzclaw-side`

Interpretation rule:

- repo-relative identity first
- observed absolute runtime path second
- secret payloads never become canonical closeout content

## 4. `SkillObservation` Minimum Fields

`SkillObservation` is the primary closeout anchor for B.

Minimum fields per run:

- `object_name`
  - fixed: `SkillObservation`
- `surface_id`
  - `SK-*` or `BT-*`
- `run_role`
  - `approved_skill_executor`
  - `shadow_candidate_runner`
  - `observation_only`
- `dispatch_mode`
  - `approved`
  - `shadow`
  - `manual_local`
  - `unknown`
- `execution_class`
  - `formal`
  - `dry_run`
  - `smoke`
  - `probe`
  - `manual_support`
- `input_summary`
  - run name, direction id, site, input refs, entrypoint ref
- `output_summary`
  - primary artifacts, row counts, status, reason code
- `kpi_delta`
  - local runtime deltas only
- `verify_status`
  - `PASS`
  - `HOLD`
  - `FAIL`
  - `NOT_RUN`
- `rollback_triggered`
  - boolean
- `error_type`
  - normalized failure class
- `operator_score_placeholder`
  - `PENDING`
  - `NOT_SET`
- `object_refs`
  - refs to the runtime objects listed in Section 2

### Example skeleton

```json
{
  "object_name": "SkillObservation",
  "surface_id": "BT-12",
  "run_role": "shadow_candidate_runner",
  "dispatch_mode": "shadow",
  "execution_class": "dry_run",
  "input_summary": {
    "batch_id": "20260407_p10_acceptance",
    "direction_id": "DIR_CLAW_MACHINE_001",
    "site": "US",
    "entrypoint_ref": "scripts/run_nightly_selection_acceptance.py"
  },
  "output_summary": {
    "status": "HOLD",
    "reason_code": "BLOCKED_BY_UPSTREAM_CHAIN__STEP2_ALL_RAW_RUNS_BLOCKED",
    "primary_output_refs": [
      "outputs/selection_runs/20260407_p10_acceptance/00_run_manifest.json",
      "outputs/selection_runs/20260407_p10_acceptance/03_logs/evidence_pack.json"
    ]
  },
  "kpi_delta": [
    {
      "metric": "final_row_count",
      "before": 0,
      "after": 20
    }
  ],
  "verify_status": "HOLD",
  "rollback_triggered": false,
  "error_type": "UPSTREAM_CHAIN_BLOCKED",
  "operator_score_placeholder": "PENDING",
  "object_refs": {
    "artifact_return_envelope_ref": "outputs/selection_runs/20260407_p10_acceptance/00_run_manifest.json",
    "evidence_pack_ref": "outputs/selection_runs/20260407_p10_acceptance/03_logs/evidence_pack.json",
    "execution_receipt_ref": "__PRECURSOR__",
    "verification_result_ref": "__PLACEHOLDER__",
    "rollback_trace_ref": "__PLACEHOLDER__",
    "shadow_run_receipt_ref": "outputs/selection_runs/20260407_p10_acceptance/03_logs/shadow_run_receipt.json",
    "human_review_entry_ref": "__PLACEHOLDER__"
  }
}
```

## 5. Closeout Field Mapping

Required per-run closeout facts map this way:

| closeout fact | preferred object | current B carrier / precursor |
|---|---|---|
| input summary | `SkillObservation` | `01_consumed_inputs/**`, route decision log, current input CSV refs |
| output summary | `SkillObservation` | `00_run_summary.md`, `latest_run.json`, `batch_run_summary.json` |
| KPI change | `SkillObservation` | row counts, artifact counts, retry counts, latency facts from run summaries |
| verify pass | `VerificationResult` | current placeholder or deterministic-check precursor |
| rollback triggered | `RollbackTrace` | current placeholder, rollback note, replay/profile recovery evidence |
| error type | `ExecutionReceipt` + `SkillObservation` | native `reason_code`, auth incident family, runtime exception class |
| operator score placeholder | `HumanReviewEntry` | placeholder only, no scorebook truth |

## 6. Evidence Item Taxonomy

All major B-side evidence surfaces must be objectized through `EvidencePack`.

| evidence surface | current example | canonical object | content role | sensitivity |
|---|---|---|---|---|
| workbook | `runs/manual/**/*.xlsx` | `EvidencePack` | `raw` + `reviewable` | `ignored_local_runtime` |
| screenshot | `playwright/screenshots/**/*.png` | `EvidencePack` | `reviewable` | `ignored_local_runtime` |
| trace zip | `playwright/traces/**/*.zip` | `EvidencePack` | `raw` | `ignored_local_runtime` |
| auth incident json | `logs/sellersprite_auth_incidents/latest_auth_incident.json` | `EvidencePack` + `SkillObservation` | `summarized` | `ignored_local_runtime` |
| replay attempt json | `logs/sellersprite_auth_incidents/latest_replay_attempt.json` | `EvidencePack` | `summarized` | `ignored_local_runtime` |
| step receipt | `logs/**/latest_run.json`, `latest_*_run.json` | `ExecutionReceipt` precursor | `summarized` | `ignored_local_runtime` |
| run summary | `outputs/selection_runs/<batch_id>/00_run_summary.md` | `ArtifactReturnEnvelope` support | `reviewable` | `ignored_local_runtime` |
| run manifest | `outputs/selection_runs/<batch_id>/00_run_manifest.json` | `ArtifactReturnEnvelope` | `ingest_ready` | `ignored_local_runtime` |
| artifact index | `outputs/selection_runs/<batch_id>/02_generated_outputs/artifact_index.json` | `ArtifactReturnEnvelope` support | `ingest_ready` | `ignored_local_runtime` |
| shadow receipt | `outputs/selection_runs/<batch_id>/03_logs/shadow_run_receipt.json` | `ShadowRunReceipt` | `ingest_ready` | `ignored_local_runtime` |
| model receipt | `outputs/selection_runs/<batch_id>/03_logs/model_inference_receipts/*.json` | `ModelInferenceReceipt` | `ingest_ready` | `ignored_local_runtime` |

## 7. Verify And Rollback Semantics

`VerificationResult` on B must follow the fallback scorebook hard-gate rule:

- schema / contract pass
- deterministic check pass
- verify pass
- rollback available
- no severe side effect
- no unauthorized attempt

`RollbackTrace` on B must answer:

- whether rollback was triggered
- why it was triggered
- which local asset was restored or discarded
- which evidence ref proves the rollback path

Neither object lets B claim final governance truth.

## 8. Model And Shadow Supplements

### `ModelInferenceReceipt`

Emit only when a real model call happened.

Minimum fields:

- provider
- model
- invocation or prompt ref
- output ref
- latency / usage when available
- verify linkage

Current note:

- B3 already reserved the carrier path
- fallback A2 host freeze for this object name is still unresolved
- the object name stays because B2 / B3 / B8 require it

### `ShadowRunReceipt`

Use only for:

- `shadow`
- `dry_run`
- `smoke`
- `probe`

Minimum fields:

- run posture
- status
- reason code
- comparison anchor ref when present
- verify linkage

## 9. Business Boundary

Runtime observation is not business closure.

The following facts do not become final verdict by themselves:

- workbook download success
- screenshot capture
- trace presence
- auth replay success
- shadow receipt success
- model call success

Machine B may emit closeout facts, observation, and evidence. Machine A remains
the owner of promotion, retirement, and final business judgment.
