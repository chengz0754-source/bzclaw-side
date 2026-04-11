# B Integrated Runs Report

## Scope

- Date: `2026-04-12`
- Fallback A-side docs were used because repo-visible A5/A9 outputs were not present locally.
- This report covers:
  - `DATA`
  - `B02`
  - one real B-side business execution chain

## Integrated Surface Summary

| surface | local status | execution result | note |
| --- | --- | --- | --- |
| `DATA` | `HOST_NOT_OBSERVED` | `NOT_EXECUTED` | no repo-visible local hostline was present on this machine |
| `B02` | `HOST_NOT_OBSERVED` | `NOT_EXECUTED` | release-bridge semantics remain contract-only on B in this round |
| `BT-11 / nightly acceptance shadow bundle` | `EXECUTED` | `HOLD` | structurally complete envelope emitted at `20260412_b9_integrated_row1_v3` |

## Nightly Execution Of Record

- Repo root: `E:\选品文件夹\amazon-selection-automation`
- Command:
  - `.\.venv\Scripts\python.exe scripts\run_nightly_selection_acceptance.py --batch-id 20260412_b9_integrated_row1_v3 --row-indices 1`
- Dispatch mode: `shadow`
- Execution class: `dry_run`
- Final status: `HOLD`
- Final reason code:
  - `BATCH_QUEUE_HAS_FAIL_ROWS; NO_REAL_CANDIDATE_ROWS; BLOCKED_BY_SIF_OR_POOL_ALIGNMENT__NO_REAL_CANDIDATE_ROWS__SIF_DETAIL_SURFACE_NOT_COLLECTED__SIF_SEARCH_SURFACE_NOT_COLLECTED`

## Orchestration Hardening Performed In This Round

Two earlier attempts exposed fail-open gaps:

- `20260412_b9_integrated_row1`
  - runner aborted when `sif_detail_surface_probe.json` was missing
- `20260412_b9_integrated_row1_v2`
  - runner progressed further but aborted when `sif_enrichment_daytime_pack_summary.json` was missing

The runner was then hardened so that missing SIF probe/daytime-pack outputs are converted into blocked fallback artifacts instead of aborting the entire archive.

Result:

- `20260412_b9_integrated_row1_v3` emitted a full archive-shaped sidecar bundle
- `00_run_manifest.json` exists
- `artifact_index.json` exists
- `evidence_pack.json` exists
- `shadow_run_receipt.json` exists

## Step Results

- `direction_batch`
  - status: `FAIL`
  - reason: `BATCH_QUEUE_HAS_FAIL_ROWS`
- `candidate_pool`
  - status: `HOLD`
  - reason: `NO_REAL_CANDIDATE_ROWS`
- `sif_detail_probe`
  - status: `HOLD`
  - reason: `NO_REAL_CANDIDATE_ROWS`
  - current run now emits a blocked fallback summary and header-only `50`
- `sif_search_probe`
  - status: `HOLD`
  - reason: `NO_REAL_CANDIDATE_ROWS`
  - current run now emits a blocked fallback summary and header-only `51/52`
- `sif_enrichment`
  - status: `HOLD`
  - reason: `BLOCKED_BY_SIF_OR_POOL_ALIGNMENT__NO_REAL_CANDIDATE_ROWS__SIF_DETAIL_SURFACE_NOT_COLLECTED__SIF_SEARCH_SURFACE_NOT_COLLECTED`
  - current run now emits blocked `53/61` plus summary and markdown

## Business Evidence Observed

- `STEP3 market trigger`
  - `DRY_RUN`
  - summary path: `E:\选品文件夹\amazon-selection-automation\outputs\selection_runs\20260412_b9_integrated_row1_v3\03_logs\direction_batch\row_001_toy\step3_market\latest_run.json`
- `STEP4 benchmark trigger`
  - blocked at SellerSprite export-log auth surface
  - summary path: `E:\选品文件夹\amazon-selection-automation\outputs\selection_runs\20260412_b9_integrated_row1_v3\03_logs\direction_batch\row_001_toy\step4_benchmark\latest_benchmark_export_run.json`
  - reason: `SELLERSPRITE_AUTH_REQUIRED`
  - auth replay attempt status inside summary: `PASS`
  - replay improved local readiness but did not turn the surface into a business pass
- `auth incident evidence`
  - incident JSON: `E:\选品文件夹\amazon-selection-automation\logs\sellersprite_auth_incidents\incidents\2026-04-12T00-50-45-08-00-benchmark_export-stage_b_export_log_baseline-SELLERSPRITE_EXPORT_LOG_AUTH.json`
  - screenshot: `E:\选品文件夹\amazon-selection-automation\playwright\screenshots\sellersprite_auth_incidents\2026-04-12T005045_0800-benchmark_export-stage_b_export_log_baseline-auth.png`
  - page snapshot JSON: `E:\选品文件夹\amazon-selection-automation\logs\sellersprite_auth_incidents\page_snapshots\2026-04-12T005045_0800-benchmark_export-stage_b_export_log_baseline-SELLERSPRITE_EXPORT_LOG_AUTH.json`
  - page snapshot HTML: `E:\选品文件夹\amazon-selection-automation\logs\sellersprite_auth_incidents\page_snapshots\2026-04-12T005045_0800-benchmark_export-stage_b_export_log_baseline-SELLERSPRITE_EXPORT_LOG_AUTH.html`

## Telemetry Bundle Emitted

- `ArtifactReturnEnvelope`
  - `E:\选品文件夹\amazon-selection-automation\outputs\selection_runs\20260412_b9_integrated_row1_v3\00_run_manifest.json`
- `EvidencePack`
  - `E:\选品文件夹\amazon-selection-automation\outputs\selection_runs\20260412_b9_integrated_row1_v3\03_logs\evidence_pack.json`
  - `item_count = 36`
- `ShadowRunReceipt`
  - `E:\选品文件夹\amazon-selection-automation\outputs\selection_runs\20260412_b9_integrated_row1_v3\03_logs\shadow_run_receipt.json`
- `ModelInferenceReceipt`
  - none emitted
- `Trace`
  - no fresh run-local trace zip was emitted by the current nightly batch
  - runtime trace baseline remains `E:\选品文件夹\amazon-selection-automation\playwright\traces\playwright-smoke.zip`

## What This Round Proves

- B can now return a full archive-shaped sidecar bundle even when downstream business truth is blocked.
- The bundle is ingest-stable for A because manifest, evidence pack, artifact index, and shadow receipt are all present.
- The nightly path now preserves blocked truth instead of aborting on missing SIF intermediate files.

## What This Round Does Not Prove

- It does not prove `DATA` local execution readiness.
- It does not prove `B02` local execution readiness.
- It does not prove business verification, owner approval, or formal publish.
- It does not prove model-receipt coverage because no model call was exercised in this integrated run.
