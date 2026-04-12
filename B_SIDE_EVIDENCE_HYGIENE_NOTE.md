# B Side Evidence Hygiene Note

## Current Effective Result

- effective consumed A packet: `20260412-0631-A-B-BATCH5-FRONTEND-REFRESH-READY`
- effective B->A packet: `20260412-0750-B-A-B12_BATCH5_INTEGRATED_RUN-READY`
- effective run bundle: `selection_repo:outputs/selection_runs/20260412_b12_batch5_packet_row1_v1`

## Active vs Archived Exchange State

- active B->A packet remains in:
  - `E:\bzclaw-exchange\02_B_TO_A_OUTBOX\20260412-0750-B-A-B12_BATCH5_INTEGRATED_RUN-READY`
- superseded old B-12 packet was moved out of the active outbox and archived at:
  - `E:\bzclaw-exchange\05_ARCHIVE\2026-04\20260412-0649-B-A-B12_INTEGRATED_RUN-READY`
- the archived old packet includes:
  - `SUPERSESSION_NOTE.md`

## Runtime Evidence Ownership

- selection repo remains the canonical owner of runtime evidence and run bundles
- `bzclaw-side` must not keep raw runtime evidence copies as repo-visible mirrors
- shared exchange keeps transport packets, not unbounded raw runtime payload piles

## Current Batch-5 Evidence Refs

- `APacketIntakeLog`
  - `selection_repo:outputs/selection_runs/20260412_b12_batch5_packet_row1_v1/03_logs/a_packet_intake.json`
- `ArtifactReturnEnvelope`
  - `selection_repo:outputs/selection_runs/20260412_b12_batch5_packet_row1_v1/00_run_manifest.json`
- `EvidencePack`
  - `selection_repo:outputs/selection_runs/20260412_b12_batch5_packet_row1_v1/03_logs/evidence_pack.json`
- `ShadowRunReceipt`
  - `selection_repo:outputs/selection_runs/20260412_b12_batch5_packet_row1_v1/03_logs/shadow_run_receipt.json`
- `ModelInferenceReceipt`
  - `NOT_EMITTED`

## Hygiene Rules Going Forward

- keep only the current active B->A packet in `02_B_TO_A_OUTBOX` when a newer packet supersedes an older one
- archive superseded transport packets by month and add explicit supersession context
- do not delete selection run bundles merely because an exchange packet was superseded
- do not copy raw screenshots, traces, downloads, or workbook payloads into `bzclaw-side`
- keep `bzclaw-side` as reference/governance only; keep runtime evidence in selection outputs and exchange packets

## Result

- current batch-5 B-12 evidence remains intact and reachable
- the old A10-based B-12 transport result no longer pollutes the active exchange lane
- `bzclaw-side` no longer acts like a second evidence warehouse
