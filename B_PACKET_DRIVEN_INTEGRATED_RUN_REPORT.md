# B Packet-Driven Integrated Run Report

## Scope

- date: `2026-04-12`
- governance repo: `E:\bzclaw-side`
- selection repo: `selection_repo`
- consumed A packet: `20260412-0631-A-B-BATCH5-FRONTEND-REFRESH-READY`
- supersedes consumed A packet: `20260412-0334-A-B-A10_DELIVERABLES-READY`
- B->A return packet: `20260412-0750-B-A-B12_BATCH5_INTEGRATED_RUN-READY`
- supersedes B->A return packet: `20260412-0649-B-A-B12_INTEGRATED_RUN-READY`

## Intake Verdict

- targeted A packet on B: `20260412-0631-A-B-BATCH5-FRONTEND-REFRESH-READY`
- intake status: `EXECUTED`
- required packet-local payloads present: `52 / 52`
- fallback used: `FALSE`
- old A10 packet was not read during this rerun
- `REFERENCE` payloads remained non-blocking and were not reconstructed

## Execution Matrix

| surface | execution_status | result_state | note |
| --- | --- | --- | --- |
| `A packet intake` | `EXECUTED` | `PASS` | batch-5 packet-local validation completed |
| `DATA` | `NOT_EXECUTED` | `HOST_NOT_OBSERVED` | contract surface only on this machine |
| `B02` | `NOT_EXECUTED` | `HOST_NOT_OBSERVED` | contract surface only on this machine |
| `BT-11 / nightly acceptance shadow bundle` | `EXECUTED` | `HOLD` | one real B-side business chain completed against batch-5 packet truth |
| `ModelInferenceReceipt` | `NOT_EMITTED` | `NO_MODEL_CALL_IN_THIS_BATCH` | no model call happened in this run |

## Real Business Chain

- batch_id: `20260412_b12_batch5_packet_row1_v1`
- entrypoint: `scripts/run_nightly_selection_acceptance.py`
- posture: `shadow / dry_run`
- final status: `HOLD`
- reason_code: `BATCH_QUEUE_HAS_FAIL_ROWS; NO_REAL_CANDIDATE_ROWS; BLOCKED_BY_SIF_OR_POOL_ALIGNMENT__NO_REAL_CANDIDATE_ROWS__SIF_DETAIL_SURFACE_NOT_COLLECTED__SIF_SEARCH_SURFACE_NOT_COLLECTED`
- observed business path: row 1 nightly acceptance lane with real direction-batch, candidate-pool, SIF probe, and enrichment steps
- current business truth remains blocked rather than fabricated into pass

## Return Objects

- `APacketIntakeLog`: `selection_repo:outputs/selection_runs/20260412_b12_batch5_packet_row1_v1/03_logs/a_packet_intake.json`
- `ArtifactReturnEnvelope`: `selection_repo:outputs/selection_runs/20260412_b12_batch5_packet_row1_v1/00_run_manifest.json`
- `EvidencePack`: `selection_repo:outputs/selection_runs/20260412_b12_batch5_packet_row1_v1/03_logs/evidence_pack.json`
- `ShadowRunReceipt`: `selection_repo:outputs/selection_runs/20260412_b12_batch5_packet_row1_v1/03_logs/shadow_run_receipt.json`
- `ModelInferenceReceipt`: `NOT_EMITTED`
- evidence item count: `43`

## Supersession

- prior B-12 run batch: `20260412_b12_packet_driven_row1_v1`
- prior B-12 truth source: `20260412-0334-A-B-A10_DELIVERABLES-READY`
- current B-12 truth source: `20260412-0631-A-B-BATCH5-FRONTEND-REFRESH-READY`
- changed input surface: batch-5 rerun now carries A14/A15/A16 governance, frontend repo packet-local copies, runtime DATA proof surfaces, and OPS V2 registries from the refreshed A packet
- unchanged execution truth: `BT-11` remained `HOLD`, `DATA` remained `NOT_EXECUTED`, `B02` remained `NOT_EXECUTED`, and `ModelInferenceReceipt` remained `NOT_EMITTED`
- conclusion: the earlier A10-based B-12 result is superseded for batch-5 truth and must not be treated as current

## Exchange Closure

- consumed input packet: `exchange:01_A_TO_B_INBOX/20260412-0631-A-B-BATCH5-FRONTEND-REFRESH-READY`
- returned output packet: `exchange:02_B_TO_A_OUTBOX/20260412-0750-B-A-B12_BATCH5_INTEGRATED_RUN-READY`
- this closes one real A->B->A loop through the shared exchange layer using batch-5 A truth
- it does not claim business verified, owner-approved closeout, or formal publish
