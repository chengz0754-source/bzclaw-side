# B Exchange Intake Rules

## Scope

This document fixes the B-side intake path for A-origin packets as of `2026-04-12`.

Canonical exchange root:

- `E:\bzclaw-exchange`

Canonical A-to-B intake lane:

- `E:\bzclaw-exchange\01_A_TO_B_INBOX`

This round is pinned to exactly one packet:

- packet id: `20260412-0334-A-B-A10_DELIVERABLES-READY`
- packet path: `E:\bzclaw-exchange\01_A_TO_B_INBOX\20260412-0334-A-B-A10_DELIVERABLES-READY`

## B-Side Intake Rule

B may consume A-side delivery only from packet-local copies inside the exchange packet.

Allowed read surface for this round:

- `PACKET_MANIFEST.json`
- `README.md`
- `indexes/PROVENANCE_INDEX.json`
- `summaries/*`
- `inputs/governance/*`
- `inputs/current/*`
- `inputs/runtime/*`
- `inputs/registries/*`

Forbidden default read surfaces:

- `E:\bzclaw\...`
- Downloads
- remembered A-local repo paths
- chat memory as if it were a received artifact

## Required Intake Sequence

1. read `PACKET_MANIFEST.json`
2. read `README.md`
3. read `summaries/A_TO_B_DELIVERABLE_REGISTRY.md`
4. read `summaries/A_TO_B_PACKET_WRITER_RULES.md`
5. read the packet-local governance files required by the current B task
6. use packet-local `inputs/current/*`, `inputs/runtime/*`, and `inputs/registries/*` as the evidence base

## Missing Input Rule

If the packet itself is missing, or if a required packet-local deliverable is absent, B must return:

- `UPSTREAM_MISSING`

Required response shape:

- name the missing relative packet path
- stop before semantic fallback
- do not attempt to reconstruct the missing file from `E:\bzclaw`

## Non-Blockers

These do not block intake by themselves:

- `REFERENCE_NOT_VISIBLE` items recorded in packet-local provenance
- `path_ref_only` entries recorded only as source provenance anchors

Those items are not B-readable transport payloads and must not trigger a fallback read to A-local paths.

## Current Packet Verdict

Observed on `2026-04-12`:

- packet exists: `YES`
- `must_copy` entries present: `39 / 39`
- manifest `contents` entries present: `42 / 42`
- `REFERENCE_NOT_VISIBLE` count: `3`
- `path_ref_only` count: `8`

Conclusion:

- `20260412-0334-A-B-A10_DELIVERABLES-READY` is fully consumable by B from packet-local copies only
- no lawful read to `E:\bzclaw` is required for this packet
