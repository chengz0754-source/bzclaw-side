# B Packet Intake Schema

## Purpose

This schema defines the minimum packet shape B expects when consuming A-side deliverables through the shared exchange layer.

It is the B-side intake contract for later bounded runs such as `B-12`.

## Canonical Packet Root

For this round:

- `E:\bzclaw-exchange\01_A_TO_B_INBOX\20260412-0334-A-B-A10_DELIVERABLES-READY`

General form:

- `E:\bzclaw-exchange\01_A_TO_B_INBOX\<packet_id>\`

## Minimum Required Files

Every A-to-B packet must contain:

- `PACKET_MANIFEST.json`
- `README.md`

For the A10 deliverable packet family, B also expects:

- `indexes/PROVENANCE_INDEX.json`
- `summaries/A_TO_B_DELIVERABLE_REGISTRY.md`
- `summaries/A_TO_B_PACKET_WRITER_RULES.md`

## Expected Subtrees

Required packet-local subtrees for `A10_DELIVERABLES` intake:

- `inputs/governance/a5/`
- `inputs/governance/a8/`
- `inputs/governance/a9/`
- `inputs/current/`
- `inputs/runtime/crossline/`
- `inputs/runtime/coldstart/`
- `inputs/registries/ops_v2/`
- `indexes/`
- `summaries/`

## Semantic Roles

Control layer:

- `PACKET_MANIFEST.json`
- `README.md`
- `indexes/PROVENANCE_INDEX.json`

Governance input layer:

- `inputs/governance/a5/*`
- `inputs/governance/a8/*`
- `inputs/governance/a9/*`

Current-state layer:

- `inputs/current/*`

Runtime evidence layer:

- `inputs/runtime/crossline/*`
- `inputs/runtime/coldstart/*`

Registry contract layer:

- `inputs/registries/ops_v2/*`

Summary layer:

- `summaries/*`

## Validation Rules

B intake validation must check:

1. packet folder exists at the exchange path
2. `PACKET_MANIFEST.json` exists
3. `README.md` exists
4. every required `must_copy` path recorded in `indexes/PROVENANCE_INDEX.json` exists inside the packet
5. every relative path listed in `PACKET_MANIFEST.json` exists inside the packet

If any required check fails:

- return `UPSTREAM_MISSING`
- include the missing relative path
- stop intake

## Special Classification Rules

`REFERENCE_NOT_VISIBLE`:

- lawful status for prompt-requested references that were not repo-visible on A side
- not a blocker by itself
- must not be rebuilt by B

`path_ref_only`:

- provenance-only anchor
- not a readable cross-machine payload
- must not be treated as a fallback read route

## Current A10 Packet Validation Result

For `20260412-0334-A-B-A10_DELIVERABLES-READY`:

- required packet root files: present
- expected subtrees: present
- `must_copy` paths: `39 / 39` present
- manifest-listed paths: `42 / 42` present

Result:

- schema validation passed
- the packet is ready for direct B-side consumption
