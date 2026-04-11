# B Return Shape Samples

These are conformance samples for B2 intake only.

They do not claim that B already emits fully frozen canonical objects on disk.

Rules for reading this file:

- keep the object names exactly as written below
- treat `__MISSING__` as a real current gap
- when A3 real host schemas arrive, replace these placeholders with the canonical host fields instead of inventing a parallel B-only schema

Important freeze note:

- `DecisionDraft`, `EvidencePack`, and `ArtifactReturnEnvelope` are explicitly visible in the fallback A2 baseline
- `ModelInferenceReceipt` and `ShadowRunReceipt` are kept here because the B2 task requires them and package-level V3 materials reference them, but their fallback-A2 host freeze is not explicit

## 1. `DecisionDraft`

Closest current B surface:

- `logs/<namespace>/latest_route_decision.json`
- `logs/<namespace>/latest_run.json`
- `outputs/selection_runs/<batch_id>/02_generated_outputs/03_候选市场与候选品初筛池.csv`
- `outputs/selection_runs/<batch_id>/02_generated_outputs/60_候选样品池.csv`

```json
{
  "object_name": "DecisionDraft",
  "observed_b_surface": {
    "primary_ref": "logs/<namespace>/latest_route_decision.json",
    "supporting_refs": [
      "logs/<namespace>/latest_run.json",
      "outputs/selection_runs/<batch_id>/02_generated_outputs/03_候选市场与候选品初筛池.csv",
      "outputs/selection_runs/<batch_id>/02_generated_outputs/60_候选样品池.csv"
    ]
  },
  "current_b_payload": {
    "status": "<from B log>",
    "reason_code": "<from B log>",
    "purpose_type": "<from B log>",
    "run_name": "<from B log>",
    "direction_id": "<from B log>"
  },
  "missing_for_conformance": {
    "object_id": "__MISSING__",
    "contract_version": "__MISSING__",
    "upstream_dispatch_ref": "__MISSING__",
    "verify_linkage": "__MISSING__",
    "state_token": "__MISSING__"
  }
}
```

## 2. `EvidencePack`

Closest current B surface:

- `playwright/screenshots/**`
- `playwright/traces/**`
- `runs/manual/**/*.xlsx`
- `logs/**/*.json*`
- `outputs/selection_runs/<batch_id>/02_generated_outputs/*_output_index.*`
- `outputs/selection_runs/<batch_id>/02_generated_outputs/13_step1_market_handoff.jsonl`

```json
{
  "object_name": "EvidencePack",
  "observed_b_surface": {
    "evidence_refs": [
      "playwright/screenshots/**",
      "playwright/traces/**",
      "runs/manual/**/*.xlsx",
      "logs/**/*.json*",
      "outputs/selection_runs/<batch_id>/02_generated_outputs/*_output_index.*",
      "outputs/selection_runs/<batch_id>/02_generated_outputs/13_step1_market_handoff.jsonl"
    ]
  },
  "current_b_payload": {
    "evidence_scope": "playwright + workbook + raw json + step logs + output indexes",
    "packaging_state": "scattered_runtime_evidence"
  },
  "missing_for_conformance": {
    "pack_id": "__MISSING__",
    "typed_items": "__MISSING__",
    "hashes_or_checksums": "__MISSING__",
    "verify_linkage": "__MISSING__",
    "state_token": "__MISSING__"
  }
}
```

## 3. `ArtifactReturnEnvelope`

Closest current B surface:

- full run archive under `outputs/selection_runs/<batch_id>/`

```json
{
  "object_name": "ArtifactReturnEnvelope",
  "observed_b_surface": {
    "run_archive_dir": "outputs/selection_runs/<batch_id>/",
    "required_layers": [
      "00_run_summary.md",
      "01_consumed_inputs/",
      "02_generated_outputs/",
      "03_logs/"
    ]
  },
  "current_b_payload": {
    "summary_ref": "outputs/selection_runs/<batch_id>/00_run_summary.md",
    "consumed_inputs_dir": "outputs/selection_runs/<batch_id>/01_consumed_inputs/",
    "generated_outputs_dir": "outputs/selection_runs/<batch_id>/02_generated_outputs/",
    "logs_dir": "outputs/selection_runs/<batch_id>/03_logs/"
  },
  "missing_for_conformance": {
    "envelope_id": "__MISSING__",
    "returned_object_refs": "__MISSING__",
    "verify_linkage": "__MISSING__",
    "state_token": "__MISSING__"
  }
}
```

Do not use this object name for a directory that only contains `02_generated_outputs/`. That is a partial artifact package, not a full envelope.

## 4. `ModelInferenceReceipt`

Closest current B surface:

- `configs/model.json`
- `models/README.md`
- no stable emitted receipt file observed under repo-declared runtime paths

```json
{
  "object_name": "ModelInferenceReceipt",
  "observed_b_surface": {
    "provider_ref": "configs/model.json",
    "model_ref": "models/README.md",
    "emitted_receipt_ref": "__NOT_OBSERVED__"
  },
  "current_b_payload": {
    "default_provider": "ollama_local",
    "default_model": "qwen3:4b-instruct",
    "protocol": "openai_compatible",
    "base_url": "http://127.0.0.1:11434/v1"
  },
  "missing_for_conformance": {
    "receipt_id": "__MISSING__",
    "prompt_or_invocation_ref": "__MISSING__",
    "output_artifact_ref": "__MISSING__",
    "usage_and_latency": "__MISSING__",
    "verify_linkage": "__MISSING__",
    "state_token": "__MISSING__"
  }
}
```

## 5. `ShadowRunReceipt`

Closest current B surface:

- `reports/nightly_run_operator_runbook.md`
- `outputs/selection_runs/<batch_id>/00_run_summary.md`
- `outputs/selection_runs/<batch_id>/03_logs/nightly_acceptance_summary.json`

```json
{
  "object_name": "ShadowRunReceipt",
  "observed_b_surface": {
    "contract_ref": "reports/nightly_run_operator_runbook.md",
    "summary_ref": "outputs/selection_runs/<batch_id>/00_run_summary.md",
    "log_ref": "outputs/selection_runs/<batch_id>/03_logs/nightly_acceptance_summary.json"
  },
  "current_b_payload": {
    "run_kind": "nightly acceptance dry-run",
    "status": "<PASS|HOLD|FAIL from B summary>",
    "reason_codes": [
      "<from B summary>"
    ]
  },
  "missing_for_conformance": {
    "receipt_id": "__MISSING__",
    "upstream_dispatch_ref": "__MISSING__",
    "permission_profile": "__MISSING__",
    "verify_linkage": "__MISSING__",
    "state_token": "__MISSING__"
  }
}
```

`ShadowRunReceipt` is not business closure. It is only the shaped receipt for a bounded shadow or dry-run result.
