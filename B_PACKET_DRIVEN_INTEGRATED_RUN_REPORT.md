# B Packet-Driven Integrated Run Report

## Scope

- date: `2026-04-12`
- governance repo: `E:\bzclaw-side`
- selection repo: `selection_repo`
- consumed A packet: `20260412-0334-A-B-A10_DELIVERABLES-READY`
- B->A return packet: `20260412-0649-B-A-B12_INTEGRATED_RUN-READY`

## Intake Verdict

- latest visible A packet on B: `20260412-0334-A-B-A10_DELIVERABLES-READY`
- intake status: `EXECUTED`
- missing must-copy payloads: `0`
- fallback used: `FALSE`
- `REFERENCE_NOT_VISIBLE` remained non-blocking and was not reconstructed.

## Execution Matrix

| surface | execution_status | result_state | note |
| --- | --- | --- | --- |
| `A packet intake` | `EXECUTED` | `PASS` | packet-local validation completed |
| `DATA` | `NOT_EXECUTED` | `HOST_NOT_OBSERVED` | contract-only surface on this machine |
| `B02` | `NOT_EXECUTED` | `HOST_NOT_OBSERVED` | contract-only surface on this machine |
| `BT-11 / nightly acceptance shadow bundle` | `EXECUTED` | `HOLD` | one real B-side business chain completed packet-driven |
| `ModelInferenceReceipt` | `NOT_EMITTED` | `NO_MODEL_CALL_IN_THIS_BATCH` | no model call happened in this run |

## Real Business Chain

- batch_id: `20260412_b12_packet_driven_row1_v1`
- entrypoint: `scripts/run_nightly_selection_acceptance.py`
- posture: `shadow / dry_run`
- final status: `HOLD`
- reason_code: `BATCH_QUEUE_HAS_FAIL_ROWS; NO_REAL_CANDIDATE_ROWS; BLOCKED_BY_SIF_OR_POOL_ALIGNMENT__NO_REAL_CANDIDATE_ROWS__SIF_DETAIL_SURFACE_NOT_COLLECTED__SIF_SEARCH_SURFACE_NOT_COLLECTED`
- observed business path: row 1 nightly acceptance lane with real direction-batch, candidate-pool, SIF probe, and enrichment steps
- current business truth remains blocked rather than fabricated into pass

## Return Objects

- `ArtifactReturnEnvelope`: `selection_repo:outputs/selection_runs/20260412_b12_packet_driven_row1_v1/00_run_manifest.json`
- `EvidencePack`: `selection_repo:outputs/selection_runs/20260412_b12_packet_driven_row1_v1/03_logs/evidence_pack.json`
- `ShadowRunReceipt`: `selection_repo:outputs/selection_runs/20260412_b12_packet_driven_row1_v1/03_logs/shadow_run_receipt.json`
- `ModelInferenceReceipt`: `NOT_EMITTED`
- evidence item count: `41`

## Exchange Closure

- consumed input packet: `exchange:01_A_TO_B_INBOX/20260412-0334-A-B-A10_DELIVERABLES-READY`
- returned output packet: `exchange:02_B_TO_A_OUTBOX/20260412-0649-B-A-B12_INTEGRATED_RUN-READY`
- this closes one real A->B->A loop through the shared exchange layer
- it does not claim business verified, owner-approved closeout, or formal publish
