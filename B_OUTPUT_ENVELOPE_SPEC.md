# B-side Output Envelope Spec

## Scope

This spec standardizes how Machine B packages runtime outputs so Machine A can ingest them without guessing path meaning.

This spec does not change B-side repo identity:

- B remains an independent sidecar repo
- B is not A-side truth host
- B is not a formal publish host
- B is not being rewritten here as a mature worker platform

## Sources Used

This spec is based on:

- `B_SIDECAR_BASELINE.md`
- `B_TO_A_OBJECT_MAPPING.csv`
- `B_SIDE_CONFORMANCE_NOTE.md`
- `B_RETURN_SHAPE_SAMPLES.md`
- `configs/paths.json`
- `scripts/smoke_playwright.py`
- repo-visible README and runbook/contract docs
- current local runtime path observations under the existing execution root

## Current Path State On 2026-04-11

Two path layers currently coexist:

- canonical repo alias used by prompts: `E:\bzclaw-side`
- observed runtime root still referenced by `configs/paths.json`: `E:\选品文件夹\amazon-selection-automation`

Because those two roots are not yet unified at runtime, B-side ingest metadata must use:

1. repo-relative paths as the primary identity
2. optional observed absolute paths only as local-debug support

Machine A ingest must not key on absolute Windows drive paths.

## Current Observed Runtime Surfaces

Observed current local runtime paths include:

- auth state and replay metadata
  - `playwright/auth/sellersprite.storage_state.json`
  - `playwright/auth/storage_state.smoke.json`
  - `playwright/auth/login_replay_registry.json`
  - `playwright/auth/owner_recordings/*/recording_manifest.json`
- screenshots
  - `playwright/screenshots/playwright-smoke.png`
  - `playwright/screenshots/sellersprite_auth_incidents/`
  - `playwright/screenshots/sellersprite_keyword_export_flow/`
  - `playwright/screenshots/benchmark_chain/`
- traces
  - `playwright/traces/playwright-smoke.zip`
- raw workbook/download roots
  - `runs/manual/10_market/`
  - `runs/manual/12_keyword_exports/`
  - `runs/manual/15_product_exports/`
  - `runs/manual/20_benchmark_exports/`
  - `runs/manual/nightly_downloads/`
- run archives
  - `outputs/selection_runs/<batch_id>/`
- step logs and ledgers
  - `logs/<namespace>/latest_run.json`
  - `logs/<namespace>/*.jsonl`

These observations are the source material for the standard below.

## Controlled Run Root

Every controlled B-side run that is intended to be ingestable by A must normalize to:

- `outputs/selection_runs/<batch_id>/`

Required run-root members:

- `00_run_summary.md`
  - human-readable summary
  - summarized + reviewable
- `00_run_manifest.json`
  - machine-readable root manifest
  - ingest-ready
  - primary `ArtifactReturnEnvelope` carrier
- `01_consumed_inputs/`
  - snapshot of inputs used by the run
  - raw
- `02_generated_outputs/`
  - generated business artifacts and artifact indexes
  - mixed
- `03_logs/`
  - structured logs, receipts, and evidence pack
  - mixed

Hard boundary:

- a directory that only contains `02_generated_outputs/` is a partial artifact package
- it is not a complete run root
- it must not be labeled `ArtifactReturnEnvelope`

## Directory Semantics

### 1. Raw

Primary raw surfaces:

- `runs/manual/**`
- `playwright/traces/**`
- workbook downloads such as `KeywordHistory-*.xlsx` and `market-report-*.xlsx`
- raw generated files inside `02_generated_outputs/`
  - `*_raw.json`
  - `*_原始结果.csv`
  - handoff JSONL files such as `13_step1_market_handoff.jsonl`

Raw means:

- closest to collector or download output
- may be large, noisy, or sensitive
- may be evidence-worthy
- not yet safe to treat as ingest-ready object output by itself

### 2. Summarized

Primary summarized surfaces:

- `00_run_summary.md`
- `03_logs/**/latest_run.json`
- `03_logs/**/*.jsonl`
- `02_generated_outputs/*_summary.json`
- `03_logs/nightly_acceptance_summary.json`

Summarized means:

- structured status exists
- status and reason codes are present
- useful for operator reading and failure triage
- still not enough by itself for stable A-side ingest

### 3. Reviewable

Primary reviewable surfaces:

- `playwright/screenshots/**`
- `02_generated_outputs/*.md`
- review-facing CSV outputs such as:
  - `60_候选样品池.csv`
  - shortlist CSV/MD outputs
  - per-chain `*_output_index.md`
- `00_run_summary.md`

Reviewable means:

- meant for human inspection
- may support EvidencePack
- not the primary machine-ingest anchor

### 4. Ingest-ready

Primary ingest-ready surfaces:

- `outputs/selection_runs/<batch_id>/00_run_manifest.json`
- `outputs/selection_runs/<batch_id>/02_generated_outputs/artifact_index.json`
- `outputs/selection_runs/<batch_id>/03_logs/evidence_pack.json`
- `outputs/selection_runs/<batch_id>/03_logs/model_inference_receipts/*.json`
- `outputs/selection_runs/<batch_id>/03_logs/shadow_run_receipt.json`

Ingest-ready means:

- stable object name is explicit
- metadata is complete enough for A to parse without guessing
- relative paths are normalized
- verify linkage placeholders exist
- state token exists

## Required Ingest-ready Objects

### 1. `ArtifactReturnEnvelope`

Canonical B-side carrier:

- `outputs/selection_runs/<batch_id>/00_run_manifest.json`

It must summarize:

- run identity
- run status and reason code
- canonical run-root paths
- artifact index reference
- evidence pack reference
- zero or more model receipt references
- optional shadow receipt reference
- manifest state token

### 2. `EvidencePack`

Canonical B-side carrier:

- `outputs/selection_runs/<batch_id>/03_logs/evidence_pack.json`

It must index reviewable and raw evidence references such as:

- screenshots
- traces
- workbooks
- raw JSON collector outputs
- handoff JSONL
- selected step logs

Important boundary:

- raw auth state files are never embedded as ingest payload
- only redacted metadata or path references may appear in the evidence pack

### 3. `ModelInferenceReceipt`

Canonical B-side carrier:

- `outputs/selection_runs/<batch_id>/03_logs/model_inference_receipts/<receipt_id>.json`

Emit this only when a real model call happens.

If a run contains no model call:

- do not fabricate a receipt
- keep `model_inference_receipt_refs = []` in `00_run_manifest.json`
- use `NOT_EMITTED` only for the missing object slot, not as a fake success

### 4. `ShadowRunReceipt`

Canonical B-side carrier:

- `outputs/selection_runs/<batch_id>/03_logs/shadow_run_receipt.json`

Emit this when the run is explicitly:

- `shadow`
- `dry_run`
- `smoke`

Important boundary:

- `ShadowRunReceipt` is not business closure
- smoke success is not a business completion claim
- dry-run success is not a business completion claim

## Artifact Index Standard

Every ingestable run must emit:

- `outputs/selection_runs/<batch_id>/02_generated_outputs/artifact_index.json`

This file is the normalized machine index for generated artifacts and evidence refs used by the run manifest.

Each artifact entry must include at least:

- `artifact_id`
- `logical_name`
- `object_mapping`
- `relative_path`
- `path_scope`
- `content_role`
- `category`
- `sensitivity`
- `status`
- `reason_code`
- `state_token`
- `producer_script`
- `captured_at`

Optional but preferred:

- `observed_absolute_path`
- `size_bytes`
- `sha256`
- `review_ready`
- `ingest_ready`
- `verify_linkage`

## Metadata Policy

### Path policy

- primary reference field: `relative_path`
- optional debug field: `observed_absolute_path`
- do not use absolute path as the canonical identity
- do not use a drive letter path as the only path field

### Status policy

Required on manifest and receipt objects:

- `status`
  - `PASS`
  - `HOLD`
  - `FAIL`
- `reason_code`
- `state_token`

Preferred artifact state tokens:

- `CAPTURED_RAW`
- `SUMMARIZED`
- `REVIEWABLE`
- `INGEST_READY`
- `BLOCKED`
- `SENSITIVE_LOCAL_ONLY`
- `NOT_EMITTED`

### Sensitivity policy

Allowed sensitivity classes:

- `tracked_safe`
- `ignored_local_runtime`
- `sensitive_auth`
- `redacted_metadata_only`

Hard boundary:

- `playwright/auth/*.json`
- `playwright/profiles/**`
- cookies
- tokens
- raw storage states

must never be copied into ingest payload as raw content.

Only these are allowed for auth-related ingest support:

- redacted manifest metadata
- path reference
- checksum or hash
- reason code
- surface family

### Verify linkage policy

Every ingest-ready object should reserve linkage fields for:

- `artifact_return_envelope_ref`
- `evidence_pack_ref`
- `model_inference_receipt_ref`
- `shadow_run_receipt_ref`
- optional `decision_draft_ref`

B-side is not inventing final A-side verification truth here.
These are linkage placeholders so A can join objects deterministically.

## Naming And Placement Policy

### Run id

Use existing `batch_id` as the stable run directory id:

- `outputs/selection_runs/<batch_id>/`

Do not create a second run-id namespace for the same run.

### Receipt ids

Recommended receipt-id pattern:

- `<batch_id>__<namespace>__<step_name>__<timestamp>`

### Manifest placement

- `00_run_manifest.json` stays at run root
- do not bury the primary envelope manifest under deep log namespaces

### Artifact index placement

- `artifact_index.json` stays under `02_generated_outputs/`
- it is the machine index for artifacts, not the human summary

## Minimal Controlled-run Deliverable Set

For A-side ingest, the minimum controlled-run package is:

- `00_run_summary.md`
- `00_run_manifest.json`
- `01_consumed_inputs/`
- `02_generated_outputs/`
- `02_generated_outputs/artifact_index.json`
- `03_logs/`
- `03_logs/evidence_pack.json`

Conditional additions:

- `03_logs/model_inference_receipts/*.json`
  - only when model calls happened
- `03_logs/shadow_run_receipt.json`
  - only when run class is `shadow`, `dry_run`, or `smoke`

## Fail-closed Rules

- If `00_run_manifest.json` is missing, the run is not ingest-ready.
- If `artifact_index.json` is missing, generated outputs are not ingest-ready.
- If `EvidencePack` is required by the run but `evidence_pack.json` is missing, the run stays `HOLD` or `FAIL` according to the controlling script.
- If a run used screenshots, traces, or workbooks, but only a prose report exists and no machine index exists, the run is reviewable only, not ingest-ready.
- If a model was not called, do not fabricate `ModelInferenceReceipt`.
- If auth state exists, mark it `SENSITIVE_LOCAL_ONLY`; never publish raw state content into the envelope.

## Final Position

This B3 spec keeps the current B-side archive shape and runtime roots recognizable, while adding a stable ingest layer on top:

- `ArtifactReturnEnvelope` at run root
- `EvidencePack` under `03_logs/`
- `ModelInferenceReceipt` under `03_logs/model_inference_receipts/`
- `ShadowRunReceipt` under `03_logs/`

This is enough to let future B-side controlled runs package outputs in one stable way for A-side ingest, without pretending B is a truth host or a mature orchestration platform.
