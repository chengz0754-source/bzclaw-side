# State Sync Candidate Ingest (Current)

## Purpose

This document defines the candidate-only import layer from Machine B execution
into `chengz0754-source/bzclaw-side`.

The import layer accepts only audited candidate truth objects. It does not
accept raw runtime payloads, raw logs, Playwright captures, callback bodies, or
queue traffic.

## Automated Candidate Families

| Candidate family | Staging root | Active host stays unchanged |
| --- | --- | --- |
| `truth_pack_candidate` | `docs/truth_pack/candidates/` | `reports/sellersprite_truth_pack_current.json` |
| `board_candidate` | `reports/board/candidates/` | `reports/selection/MASTER_PROGRESS_BOARD__20260412.csv` |
| `current_state_candidate` | `docs/current_state/candidates/` | `README.md` and `reports/latest_sellersprite_stage_status.json` |

`owner_writeback` remains manual-only and is not part of the automated ingest
surface.

## Input Envelope

Automated candidate import must use
`contracts/state_sync_candidate_input_contract_v1.json`.

The envelope is fixed to:

- `schema_version = bzclaw.side.state_sync_candidate_input.v1`
- `source_repo = chengz0754-source/amazon-selection-automation`
- `source_plane = B_EXECUTION_SIDECAR`
- `review_flags.candidate_truth_only = true`
- `review_flags.runtime_payload_embedded = false`
- `review_flags.business_promotion_claimed = false`

The importer derives the destination from `candidate_family`. The caller may
not override the staging root.

## Allowed Provenance vs Forbidden Content

Allowed provenance refs may point to:

- `outputs/worker_runs/.../machine_b_run_receipt.json`
- `outputs/worker_runs/.../machine_b_artifact_manifest.json`
- `outputs/worker_runs/...` run-summary files
- repo-visible `contracts/`, `docs/`, and `reports/` snapshots

Those provenance refs are metadata only. They do not promote runtime outputs
into git truth by themselves.

Forbidden content includes:

- `logs/**`
- `playwright/**`
- `runs/**`
- `archive/**`
- `inbox/**`
- `.env*`, `storage_state*`, cookies, tokens, secrets
- raw screenshots, raw traces, raw downloads, raw callback bodies

If runtime evidence matters, rewrite it into a candidate truth object first and
sync only that candidate object.

## Materialized Output

Each accepted candidate import writes:

- `<candidate_id>.candidate.json`
- `<candidate_id>.payload.json|csv|md`

The record file is deterministic metadata plus provenance. The payload file is
the reviewable candidate truth object.

## CLI

Validate without writing:

```powershell
python scripts/import_state_sync_candidate.py --input tests/fixtures/state_sync_candidate_current_state_example.json --validate-only
```

Write into the repo staging roots:

```powershell
python scripts/import_state_sync_candidate.py --input path\\to\\candidate.json
```

The importer will refuse owner-writeback automation, forbidden provenance
prefixes, business-promotion claims, and payload/path overrides outside the
frozen candidate roots.

## Exchange-Gated Mode

When candidate envelopes arrive through the shared exchange plane, use
`scripts/import_exchange_state_sync.py`.

That harness adds:

- mandatory exchange preflight cleanup/archive
- A-side verification-result gating
- accepted vs rejected import proof notes under `verification/from_b_state/`

It still delegates the actual repo materialization step to this deterministic
candidate importer and does not overwrite active hosts directly.
