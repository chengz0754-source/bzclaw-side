# A/B Handoff Protocol

## Scope

- Date: `2026-04-12`
- Governance repo: `E:\bzclaw-side`
- Business execution owner repo: `E:\选品文件夹\amazon-selection-automation`
- Source set:
  - B1 through B8 outputs in `E:\bzclaw-side`
  - fallback A-side docs from the prompt pack because repo-visible A5/A9 return objects were not present on this machine

## Current Truth Boundary

- `DATA` and `B02` execution hosts were not observed in repo-visible local state on `2026-04-12`.
- `E:\bzclaw` and the package-referenced host scripts were absent.
- Therefore this round treats `DATA` and `B02` as contract-intake surfaces only, not as locally executed hostlines.
- The only real integrated execution completed in this round is the B-side shadow nightly bundle at:
  - `E:\选品文件夹\amazon-selection-automation\outputs\selection_runs\20260412_b9_integrated_row1_v3`

## A To B Dispatch Contract

Every incoming dispatch should provide these minimum fields:

- `dispatch_id`
- `lane_id`
- `task_envelope_ref`
- `run_mode`
- `permission_profile`
- `input_summary`
- `target_surface`
- `expected_return_objects`
- `verify_expectation`
- `rollback_expectation`
- `operator_note` when the lane is owner-sensitive or auth-sensitive

Current lane routing on B:

| lane_id | B-side role | local execution status | return mode |
| --- | --- | --- | --- |
| `DATA` | handoff intake surface | `HOST_NOT_OBSERVED` | contract note plus reference-first return only |
| `B02` | handoff intake surface | `HOST_NOT_OBSERVED` | contract note plus reference-first return only |
| `BT-11/Nightly acceptance` | shadow candidate runner | `EXECUTED` | full archive-shaped bundle |
| approved imported skills `SK-01..SK-04` | approved skill executor | `NOT_RUN_THIS_ROUND` | bounded approved-execution return when explicitly dispatched |

## B To A Return Contract

When B executes a real controlled run, the return bundle should include:

- `ArtifactReturnEnvelope`
- `EvidencePack`
- `ShadowRunReceipt` when `dispatch_mode=shadow` or `execution_class=dry_run`
- `ModelInferenceReceipt` only when a real model call was emitted
- `reviewable summary`
- `telemetry/evidence index`
- `business boundary note`

Return semantics:

- `HOLD` is a valid return state when the run is structurally complete and truth-preserving.
- `HOLD` does not equal business closure, publish approval, or owner verification.
- auth/profile/cookie/storage-state materials stay local-only and travel by reference, not attachment.
- screenshots, page snapshots, workbooks, receipts, manifests, and reviewable markdown may travel as references.

## Current Bundle Example

Current B9 bundle of record:

- `ArtifactReturnEnvelope`
  - `E:\选品文件夹\amazon-selection-automation\outputs\selection_runs\20260412_b9_integrated_row1_v3\00_run_manifest.json`
- `EvidencePack`
  - `E:\选品文件夹\amazon-selection-automation\outputs\selection_runs\20260412_b9_integrated_row1_v3\03_logs\evidence_pack.json`
- `ShadowRunReceipt`
  - `E:\选品文件夹\amazon-selection-automation\outputs\selection_runs\20260412_b9_integrated_row1_v3\03_logs\shadow_run_receipt.json`
- `Artifact index`
  - `E:\选品文件夹\amazon-selection-automation\outputs\selection_runs\20260412_b9_integrated_row1_v3\02_generated_outputs\artifact_index.json`
- `Reviewable summary`
  - `E:\选品文件夹\amazon-selection-automation\outputs\selection_runs\20260412_b9_integrated_row1_v3\00_run_summary.md`
- `Auth incident evidence`
  - incident JSON: `E:\选品文件夹\amazon-selection-automation\logs\sellersprite_auth_incidents\incidents\2026-04-12T00-50-45-08-00-benchmark_export-stage_b_export_log_baseline-SELLERSPRITE_EXPORT_LOG_AUTH.json`
  - screenshot: `E:\选品文件夹\amazon-selection-automation\playwright\screenshots\sellersprite_auth_incidents\2026-04-12T005045_0800-benchmark_export-stage_b_export_log_baseline-auth.png`
  - page snapshot JSON: `E:\选品文件夹\amazon-selection-automation\logs\sellersprite_auth_incidents\page_snapshots\2026-04-12T005045_0800-benchmark_export-stage_b_export_log_baseline-SELLERSPRITE_EXPORT_LOG_AUTH.json`
  - page snapshot HTML: `E:\选品文件夹\amazon-selection-automation\logs\sellersprite_auth_incidents\page_snapshots\2026-04-12T005045_0800-benchmark_export-stage_b_export_log_baseline-SELLERSPRITE_EXPORT_LOG_AUTH.html`
- `Telemetry index`
  - `E:\bzclaw-side\TELEMETRY_EVIDENCE_OUTPUT_INDEX.csv`

## Model Receipt Rule

- The current B9 integrated run emitted no real model call.
- Therefore `ModelInferenceReceipt` remains intentionally empty for batch `20260412_b9_integrated_row1_v3`.
- A should ingest this as `NOT_EMITTED`, not as a failed model call.

## Verify And Scorebook Boundary

- A may ingest this bundle for contract conformance, evidence review, telemetry review, and scorebook-ready observation.
- A may not rewrite this bundle as `business verified`, `formal publish`, or `owner-approved closeout`.
- `DATA_ONLY__SELECTIVE_PUBLISH_ACTIVE` remains an A-side program truth, not something B-side can assert by itself.
