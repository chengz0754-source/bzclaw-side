# B12 Rerun With Batch5 Packet Note

## Purpose

This note records the forced B-D2 rerun of B-12 against the latest visible batch-5 A packet and fixes the supersession boundary between the old A10-based result and the current batch-5 result.

## Packet Gate

- forced input packet: `20260412-0631-A-B-BATCH5-FRONTEND-REFRESH-READY`
- packet-local payload completeness: `52 / 52`
- intake result: `EXECUTED`
- fallback used: `FALSE`
- forbidden inputs not used: old A10 packet, `E:\bzclaw`, remembered A-local paths

## Superseded Result

- prior consumed A packet: `20260412-0334-A-B-A10_DELIVERABLES-READY`
- prior B->A packet: `20260412-0649-B-A-B12_INTEGRATED_RUN-READY`
- prior run batch_id: `20260412_b12_packet_driven_row1_v1`
- prior status posture: packet-driven but not batch-5 current

## Current Effective Result

- current consumed A packet: `20260412-0631-A-B-BATCH5-FRONTEND-REFRESH-READY`
- current B->A packet: `20260412-0750-B-A-B12_BATCH5_INTEGRATED_RUN-READY`
- current run batch_id: `20260412_b12_batch5_packet_row1_v1`
- current real business chain: `BT-11 / nightly acceptance shadow bundle`
- current final status: `HOLD`

## State Diff

| surface | prior result | current result | change |
| --- | --- | --- | --- |
| `A packet intake` | `EXECUTED` on old A10 packet | `EXECUTED` on batch-5 packet | changed input truth source |
| `BT-11 / nightly acceptance` | `EXECUTED / HOLD` | `EXECUTED / HOLD` | no host-side change observed |
| `DATA` | `NOT_EXECUTED` | `NOT_EXECUTED` | no local hostline observed |
| `B02` | `NOT_EXECUTED` | `NOT_EXECUTED` | no local hostline observed |
| `ModelInferenceReceipt` | `NOT_EMITTED` | `NOT_EMITTED` | no model call occurred |

## Intake Evidence Written Into Run Bundle

- `selection_repo:outputs/selection_runs/20260412_b12_batch5_packet_row1_v1/01_consumed_inputs/a_packet_intake/PACKET_MANIFEST.json`
- `selection_repo:outputs/selection_runs/20260412_b12_batch5_packet_row1_v1/01_consumed_inputs/a_packet_intake/README.md`
- `selection_repo:outputs/selection_runs/20260412_b12_batch5_packet_row1_v1/01_consumed_inputs/a_packet_intake/indexes/PROVENANCE_INDEX.json`
- `selection_repo:outputs/selection_runs/20260412_b12_batch5_packet_row1_v1/01_consumed_inputs/a_packet_intake/summaries/A_TO_B_PACKET_REFRESH_NOTE.md`
- `selection_repo:outputs/selection_runs/20260412_b12_batch5_packet_row1_v1/01_consumed_inputs/a_packet_intake/summaries/A_TO_B_DELIVERABLE_REGISTRY.md`
- `selection_repo:outputs/selection_runs/20260412_b12_batch5_packet_row1_v1/01_consumed_inputs/a_packet_intake/summaries/A_TO_B_PACKET_WRITER_RULES.md`
- `selection_repo:outputs/selection_runs/20260412_b12_batch5_packet_row1_v1/03_logs/a_packet_intake.json`

## Decision

- effective current B-12 result for batch-5 truth: `20260412-0750-B-A-B12_BATCH5_INTEGRATED_RUN-READY`
- old A10-based B-12 result: `SUPERSEDED`
- usage rule: downstream A/B reasoning must use the batch-5 rerun and must not continue treating the old A10-based run as current
