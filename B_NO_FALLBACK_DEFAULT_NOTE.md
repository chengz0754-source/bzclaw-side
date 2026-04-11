# B No-Fallback Default Note

## Decision

As of `2026-04-12`, fallback has exited the default B-side intake path.

Default path now:

- B reads A delivery from packet-local copies in `E:\bzclaw-exchange\01_A_TO_B_INBOX\<packet_id>\`

Fallback is now limited to:

- startup-period bootstrapping
- explicitly scoped emergency or manual recovery
- non-default reference context clearly labeled as fallback

Fallback is not allowed to masquerade as:

- a received A artifact
- a packet-local payload
- a lawful substitute for a missing required deliverable

## What B Must Not Do

B must not:

- assume it can read `E:\bzclaw`
- silently reopen A-local paths when packet payload is missing
- treat `REFERENCE_NOT_VISIBLE` as a reason to reconstruct content from elsewhere
- treat packet provenance anchors as cross-machine readable content

## What B Must Do

If packet-local required content is missing:

- return `UPSTREAM_MISSING`
- name the missing relative packet path
- stop before semantic execution

If packet-local required content is present:

- continue using the packet as the sole intake base
- keep fallback dormant

## Current Round Answer

Pinned packet:

- `20260412-0334-A-B-A10_DELIVERABLES-READY`

Observed on `2026-04-12`:

- packet can be fully consumed by B: `YES`
- missing must-enter deliverables: `NO`
- fallback used to complete intake: `NO`
- fallback still default route: `NO`

## Operational Consequence

For later B-side bounded work, including `B-12`, the intake contract is:

1. look for the explicit packet under the shared exchange layer
2. consume packet-local copies only
3. if required content is absent, return `UPSTREAM_MISSING`
4. do not fallback to `E:\bzclaw` as the default operating path
