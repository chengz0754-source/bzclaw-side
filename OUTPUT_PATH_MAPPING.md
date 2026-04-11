# Output Path Mapping

## Scope

This file maps current B-side output roots into one stable ingest interpretation for Machine A.

Primary rule:

- use repo-relative paths for envelope metadata
- treat absolute paths as optional local-debug metadata only

Current path note on `2026-04-11`:

- canonical prompt alias: `E:\bzclaw-side`
- current observed runtime root from `configs/paths.json`: `E:\选品文件夹\amazon-selection-automation`

## Path Map

| Surface | Canonical relative path or pattern | Current observed example | Primary role | Object mapping | Git policy | Notes |
|---|---|---|---|---|---|---|
| Run root | `outputs/selection_runs/<batch_id>/` | `outputs/selection_runs/20260410_next_slice_formal/` | ingest carrier | `ArtifactReturnEnvelope` | ignored local runtime | Every controlled ingestable run anchors here. |
| Human summary | `outputs/selection_runs/<batch_id>/00_run_summary.md` | `outputs/selection_runs/20260407_p10_acceptance/00_run_summary.md` | summarized + reviewable | `ArtifactReturnEnvelope` support | ignored local runtime | Human-readable, not the primary machine anchor. |
| Machine manifest | `outputs/selection_runs/<batch_id>/00_run_manifest.json` | not yet observed; standardized by B3 | ingest-ready | `ArtifactReturnEnvelope` | ignored local runtime | New canonical machine envelope file. |
| Consumed inputs snapshot | `outputs/selection_runs/<batch_id>/01_consumed_inputs/` | `outputs/selection_runs/20260407_p10_acceptance/01_consumed_inputs/` | raw | supporting asset | ignored local runtime | Input snapshot used by the run. |
| Generated outputs root | `outputs/selection_runs/<batch_id>/02_generated_outputs/` | `outputs/selection_runs/20260410_auth_replay_formal/02_generated_outputs/` | mixed | mixed | ignored local runtime | Flat current output root; classified by file role. |
| Artifact index | `outputs/selection_runs/<batch_id>/02_generated_outputs/artifact_index.json` | not yet observed; standardized by B3 | ingest-ready | `ArtifactReturnEnvelope` support | ignored local runtime | Machine index for generated outputs and evidence refs. |
| Raw generated layer | `outputs/selection_runs/<batch_id>/02_generated_outputs/*_raw.json` and `*_原始结果.csv` | `product_research_raw.json`, `keyword_research_raw.json`, `10_产品样本原始结果.csv` | raw | `EvidencePack` source | ignored local runtime | Closest generated layer to collector output. |
| Cleaned or gate outputs | `outputs/selection_runs/<batch_id>/02_generated_outputs/*.csv` | `12_产品样本下推结果.csv`, `22_关键词证据词池下推结果.csv`, `32_市场调研下推结果.csv`, `42_竞品基准下推结果.csv` | summarized | supporting asset | ignored local runtime | Structured downstream artifacts; not a complete envelope by themselves. |
| Reviewable outputs | `outputs/selection_runs/<batch_id>/02_generated_outputs/*.md` and review CSVs | `60_候选样品池.csv`, `60_候选样品池.md`, `market_chain_output_index.md` | reviewable | `EvidencePack` source | ignored local runtime | Good for humans; still needs index/manifest for ingest. |
| Run logs root | `outputs/selection_runs/<batch_id>/03_logs/` | `outputs/selection_runs/20260407_p10_acceptance/03_logs/` | summarized + ingest support | mixed | ignored local runtime | Run-local structured logs and receipts. |
| Evidence pack | `outputs/selection_runs/<batch_id>/03_logs/evidence_pack.json` | not yet observed; standardized by B3 | ingest-ready | `EvidencePack` | ignored local runtime | Canonical evidence wrapper for screenshots, traces, workbooks, logs. |
| Model receipts | `outputs/selection_runs/<batch_id>/03_logs/model_inference_receipts/*.json` | not yet observed; current repo shows no stable receipt emission | ingest-ready | `ModelInferenceReceipt` | ignored local runtime | Emit only when real model calls happen. |
| Shadow receipt | `outputs/selection_runs/<batch_id>/03_logs/shadow_run_receipt.json` | not yet observed; nightly summary is the current precursor | ingest-ready | `ShadowRunReceipt` | ignored local runtime | Use for shadow, dry-run, or smoke classes only. |
| Namespace latest logs | `logs/<namespace>/latest_run.json` | `logs/formal_next_slice_20260410/step3_market_export/latest_run.json` | summarized | `EvidencePack` source | ignored local runtime | Good source material, but not A-ingest anchor by itself. |
| Namespace ledgers | `logs/<namespace>/*.jsonl` | `logs/market_exports/export_runs.jsonl`, `logs/sellersprite_auth_incidents/auth_incidents.jsonl` | summarized | `EvidencePack` source | ignored local runtime | Append-only ledgers and failure history. |
| Screenshots | `playwright/screenshots/<namespace>/**` | `playwright/screenshots/playwright-smoke.png`, `playwright/screenshots/sellersprite_auth_incidents/` | reviewable | `EvidencePack` source | ignored local runtime | Reviewable evidence, not business proof by itself. |
| Traces | `playwright/traces/<namespace>/**` or `playwright/traces/*.zip` | `playwright/traces/playwright-smoke.zip` | raw | `EvidencePack` source | ignored local runtime | Raw replay/debug evidence. |
| Smoke state | `playwright/auth/storage_state.smoke.json` | `playwright/auth/storage_state.smoke.json` | sensitive local only | not ingest payload | ignored local runtime | Unauthenticated smoke baseline only. |
| Reusable auth state | `playwright/auth/sellersprite.storage_state.json` | `playwright/auth/sellersprite.storage_state.json` | sensitive local only | not ingest payload | ignored local runtime | Never ingest raw content into A-side payload. |
| Auth replay metadata | `playwright/auth/login_replay_registry.json` and `playwright/auth/owner_recordings/*/recording_manifest.json` | `playwright/auth/owner_recordings/SELLERSPRITE_PRODUCT_RESEARCH_AUTH/recording_manifest.json` | summarized metadata | `EvidencePack` source only when redacted | ignored local runtime | Manifest metadata may be referenced; raw state files remain local only. |
| Browser profiles | `playwright/profiles/**` | `playwright/profiles/chromium-user-data/` | sensitive local only | not ingest payload | ignored local runtime | Runtime support only. |
| Raw market workbooks | `runs/manual/10_market/**` | `runs/manual/10_market/market-report-us-squeeze-toys-...xlsx` | raw | `EvidencePack` source | ignored local runtime | Keep-set rule still applies. |
| Raw keyword exports | `runs/manual/12_keyword_exports/**` and `runs/manual/20_keyword_exports/**` | `runs/manual/12_keyword_exports/` | raw | `EvidencePack` source | ignored local runtime | Download source for STEP2 evidence. |
| Raw product exports | `runs/manual/15_product_exports/**` | `runs/manual/15_product_exports/` | raw | `EvidencePack` source | ignored local runtime | Download source for STEP1 evidence. |
| Raw benchmark exports | `runs/manual/20_benchmark_exports/**` | `runs/manual/20_benchmark_exports/` | raw | `EvidencePack` source | ignored local runtime | Download source for STEP4 evidence. |

## Classification Rules

### Raw

Treat these as primary raw surfaces:

- `runs/manual/**`
- `playwright/traces/**`
- raw output files under `02_generated_outputs/`
- raw auth state files, but only as local-sensitive runtime state

### Summarized

Treat these as summarized:

- `00_run_summary.md`
- `logs/<namespace>/latest_run.json`
- `logs/<namespace>/*.jsonl`
- `*_summary.json`

### Reviewable

Treat these as reviewable:

- `playwright/screenshots/**`
- `*.md` outputs
- review-facing CSVs such as `60_候选样品池.csv`

### Ingest-ready

Treat only these as ingest-ready anchors:

- `00_run_manifest.json`
- `artifact_index.json`
- `evidence_pack.json`
- `model_inference_receipts/*.json`
- `shadow_run_receipt.json`

## Hard Boundaries

- Do not let A ingest a partial `02_generated_outputs/` directory as a full run envelope.
- Do not ingest raw auth state or browser profile content.
- Do not treat screenshots or traces alone as business closure.
- Do not use absolute Windows paths as the only key for artifact identity.
