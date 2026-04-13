# B_ADS_MANUAL_EXECUTION_EVIDENCE_KIT

## 1. Current frozen blocker

- current exact blocker:
  - `NO_FRESH_CANONICAL_EXECUTION_EVIDENCE__EXACT_BLOCKER_VISIBLE`
- current final gate result:
  - `REVIEW_BLOCKED__CUTOVER_NOT_READY__EXACT_REASON_VISIBLE`
- active mounted packet:
  - `Z:/02_B_TO_A_OUTBOX/20260413-210213-B-A-ADS_PHASE1_EXECUTION-READY-V2/`
- active canonical main return path string:
  - `E:/bzclaw-side/returns/ads_phase1/20260413-210213-B-A-ADS_PHASE1_EXECUTION-READY`
- current truthful packet state:
  - `delivery_result = PARTIAL`
- current exact reason:
  - no fresh canonical-root rerun is repo-visible under `E:/bzclaw-side`
  - no repo-visible manual platform execution claim with exact provenance is
    visible under `E:/bzclaw-side`
  - the strongest currently visible evidence is still a provenance-safe
    canonical mirror of older temp-root PASS verification plus review/example
    assets

## 2. Exact evidence needed to clear or narrow the blocker

One future lawful evidence-upgrade source must be one of:

- fresh canonical-root rerun evidence
- repo-visible manual platform execution claim with exact provenance
- both

Minimum evidence fields required for any future upgrade attempt:

- what was executed
- where the execution occurred
- when it occurred
- who or what executed it
- which packet / run / asset family it corresponds to
- exact outputs or platform receipts
- exact non-claims if execution was partial

What can narrow the blocker:

- one repo-visible execution claim bundle that proves a bounded fresh
  canonical-root rerun or a bounded manual platform action occurred
- the bundle must include exact provenance, exact packet linkage, and exact
  evidence host paths under `E:/bzclaw-side`

What can clear the blocker enough for a later review/cutover decision:

- the same execution claim bundle plus receipts / exports / verification notes
  / result summary strong enough for a later batch to judge that the blocker is
  no longer `NO_FRESH_CANONICAL_EXECUTION_EVIDENCE__EXACT_BLOCKER_VISIBLE`
- this kit does **not** pre-judge whether that later outcome will be
  `REVIEW_ALLOWED__CUTOVER_READY`, `REVIEW_ALLOWED__CUTOVER_READY_WITH_LIMITS`,
  or still blocked

## 3. Canonical write locations

Primary future evidence host:

- `E:/bzclaw-side/runs/ads_manual_adjustment/<execution_claim_id>/`

Write these future objects under the primary evidence host:

- `E:/bzclaw-side/runs/ads_manual_adjustment/<execution_claim_id>/EXECUTION_RUN_NOTE.md`
- `E:/bzclaw-side/runs/ads_manual_adjustment/<execution_claim_id>/ADS_PHASE1_EXECUTION_CLAIM.json`
- `E:/bzclaw-side/runs/ads_manual_adjustment/<execution_claim_id>/receipts/<repo-visible-files>`
- `E:/bzclaw-side/runs/ads_manual_adjustment/<execution_claim_id>/screenshots/<repo-visible-files>`

Supporting report hosts:

- `E:/bzclaw-side/reports/ads_manual_adjustment/ADS_PHASE1_EXECUTION_RESULT_SUMMARY__<execution_claim_id>.md`
- `E:/bzclaw-side/reports/ads_manual_adjustment/ADS_PHASE1_VERIFICATION_NOTES__<execution_claim_id>.md`

Supporting output host:

- `E:/bzclaw-side/outputs/ads_manual_adjustment/<execution_claim_id>/<repo-visible-exports>`

Later packet-refresh targets if future evidence lands lawfully:

- `E:/bzclaw-side/returns/ads_phase1/20260413-210213-B-A-ADS_PHASE1_EXECUTION-READY/PACKET_MANIFEST.json`
- `E:/bzclaw-side/returns/ads_phase1/20260413-210213-B-A-ADS_PHASE1_EXECUTION-READY/README.md`
- `E:/bzclaw-side/returns/ads_phase1/20260413-210213-B-A-ADS_PHASE1_EXECUTION-READY/summaries/ADS_PHASE1_DELIVERY_SUMMARY.md`
- `E:/bzclaw-side/returns/ads_phase1/20260413-210213-B-A-ADS_PHASE1_EXECUTION-READY/indexes/RETURN_OBJECT_INDEX.json`

## 4. Evidence object list

- one execution run note with actor, timestamp, scope, and bounded meaning
- one execution claim JSON with exact provenance and repo-visible host paths
- one or more platform receipts / upload confirmations / export artifacts if a
  manual platform action actually occurred
- one verification note tied to the exact execution claim id
- one exact result summary stating whether the blocker is narrowed, cleared, or
  unchanged
- optional refreshed packet references only after the evidence above is
  actually landed repo-visibly

## 5. Owner/manual action checklist

- use [ADS_PHASE1_EXECUTION_EVIDENCE_CAPTURE_CHECKLIST.md](</E:/bzclaw-side/reports/governance/saves/20260414-072243-batch8-b-execution-evidence-kit/ADS_PHASE1_EXECUTION_EVIDENCE_CAPTURE_CHECKLIST.md>) during the real manual run
- fill [ADS_PHASE1_EXECUTION_CLAIM_TEMPLATE.json](</E:/bzclaw-side/reports/governance/saves/20260414-072243-batch8-b-execution-evidence-kit/ADS_PHASE1_EXECUTION_CLAIM_TEMPLATE.json>) only after real execution or rerun occurs
- capture exact packet linkage:
  - packet id `20260413-210213-B-A-ADS_PHASE1_EXECUTION-READY`
  - mounted packet id `20260413-210213-B-A-ADS_PHASE1_EXECUTION-READY-V2`
- record actor, timestamp, marketplace, scope, and exact changed entities
- land receipts / screenshots / exports under `E:/bzclaw-side`, not under the
  temp reference root
- do not treat `E:/选品文件夹/amazon-selection-automation` as the truth host for
  future evidence capture
- request the follow-on batch only after the future evidence bundle is repo
  visible under the canonical root

## 6. Non-claims

- no project completion
- no runtime active
- no formal publish
- no review-ready claim
- no cutover-ready claim
- no ADS complete claim
- no fresh execution claim inferred from old temp-root PASS notes
- no fresh execution claim inferred from review-only examples, packet refreshes,
  or governance markdown alone
