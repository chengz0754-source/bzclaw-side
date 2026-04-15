# State Sync Exchange Ingest Runbook

## Purpose

This runbook freezes the Machine B state-side exchange ingest path for
`chengz0754-source/bzclaw-side`.

The ingest path reads:

- A-side verification results from `E:\bzclaw-exchange\verification\from_a\results\`
- B-side candidate envelopes from `E:\bzclaw-exchange\state_sync\from_b\candidates\`

It imports only candidate truth objects into frozen staging roots and only when
the A-side verification result explicitly allows downstream state sync.

## Boundary

- exchange is transport only, not truth host
- imported material stays in candidate staging roots only
- active hosts remain unchanged until deterministic review/promotion
- owner writeback remains manual-only
- technical success and receipt visibility do not imply business verification

## Entrypoint

- `scripts/import_exchange_state_sync.py`

Minimal run against the live B-side exchange root:

```powershell
python scripts/import_exchange_state_sync.py --exchange-root E:\bzclaw-exchange
```

Strict packet selection:

```powershell
python scripts/import_exchange_state_sync.py `
  --exchange-root E:\bzclaw-exchange `
  --packet-id packet_exchange_happy `
  --packet-id packet_exchange_rollback
```

Preflight only:

```powershell
python scripts/import_exchange_state_sync.py --preflight-only
```

## Preflight

Before any import decision, the harness cleans the two B-state intake roots:

- `verification/from_a/results/`
- `state_sync/from_b/candidates/`

The preflight step:

- archives stale or unrelated files
- archives duplicate live files, keeping only the newest packet-local file
- quarantines BOM-tainted, malformed, or nonconforming JSON
- keeps only one live candidate envelope per packet
- keeps only one live verification result per packet

This follows the mandatory exchange hygiene rule from
`01__EXCHANGE_PREFLIGHT_AND_ARCHIVE_RULE_CURRENT.md`.

## Verification Gate

Candidate import is allowed only when all of the following are true:

- candidate envelope satisfies `contracts/state_sync_candidate_input_contract_v1.json`
- A-side verification result satisfies `harness_kind = a_exchange_verification_result_v1`
- candidate `packet_id`, `event_id`, and `job_id` match the verification result
- `downstream_state_sync_allowed = true`

The harness rejects candidate import when:

- no verification result exists for the candidate packet
- verification linkage is ambiguous or mismatched
- A-side verification explicitly denies downstream sync

## Import Target

Accepted candidate envelopes are materialized only through
`scripts/import_state_sync_candidate.py`.

The import stays limited to the frozen candidate staging roots:

- `docs/truth_pack/candidates/`
- `reports/board/candidates/`
- `docs/current_state/candidates/`

The exchange harness does not write directly to:

- `reports/sellersprite_truth_pack_current.json`
- `reports/selection/MASTER_PROGRESS_BOARD__20260412.csv`
- `README.md`
- `reports/latest_sellersprite_stage_status.json`
- owner writeback hosts

## Proof Notes

Each run writes both:

- machine-readable proof JSON
- human-readable proof markdown

under:

- `E:\bzclaw-exchange\verification\from_b_state\`

These proof notes show which candidates were accepted, which were rejected,
which staging files were written, and which boundary rules were preserved.
