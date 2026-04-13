# ADS_PHASE1_EXECUTION_EVIDENCE_CAPTURE_CHECKLIST

Current frozen blocker:

- `NO_FRESH_CANONICAL_EXECUTION_EVIDENCE__EXACT_BLOCKER_VISIBLE`

Use this checklist only when a real manual platform action or a real fresh
canonical-root rerun is actually being performed.

## Before execution

- [ ] exact execution mode identified: `manual_platform_execution` or `fresh_canonical_rerun`
- [ ] execution actor identified
- [ ] execution timestamp capture plan prepared
- [ ] packet id identified: `20260413-210213-B-A-ADS_PHASE1_EXECUTION-READY`
- [ ] mounted packet id identified: `20260413-210213-B-A-ADS_PHASE1_EXECUTION-READY-V2`
- [ ] canonical evidence root chosen: `E:/bzclaw-side/runs/ads_manual_adjustment/<execution_claim_id>/`
- [ ] exact marketplace / account / campaign / ad group / entity scope listed
- [ ] non-claims understood before execution starts

## During execution

- [ ] platform/manual action or fresh rerun step described exactly
- [ ] actor identity captured in the run note
- [ ] executed_at timestamp captured
- [ ] receipts / screenshots / exports saved repo-visibly
- [ ] every receipt / screenshot / export linked to the same `execution_claim_id`
- [ ] vague screenshots without identity/path/provenance are rejected

## After execution

- [ ] `EXECUTION_RUN_NOTE.md` written under `E:/bzclaw-side/runs/ads_manual_adjustment/<execution_claim_id>/`
- [ ] `ADS_PHASE1_EXECUTION_CLAIM.json` written under `E:/bzclaw-side/runs/ads_manual_adjustment/<execution_claim_id>/`
- [ ] receipts stored under `E:/bzclaw-side/runs/ads_manual_adjustment/<execution_claim_id>/receipts/`
- [ ] screenshots stored under `E:/bzclaw-side/runs/ads_manual_adjustment/<execution_claim_id>/screenshots/`
- [ ] result summary written under `E:/bzclaw-side/reports/ads_manual_adjustment/ADS_PHASE1_EXECUTION_RESULT_SUMMARY__<execution_claim_id>.md`
- [ ] verification note written under `E:/bzclaw-side/reports/ads_manual_adjustment/ADS_PHASE1_VERIFICATION_NOTES__<execution_claim_id>.md`
- [ ] any output/export copied under `E:/bzclaw-side/outputs/ads_manual_adjustment/<execution_claim_id>/`

## Truth classification

- [ ] evidence is repo-visible under `E:/bzclaw-side`
- [ ] claim is not based on temp-root PASS notes alone
- [ ] claim is not based on logs alone
- [ ] claim is not based on governance markdown alone
- [ ] result classified without inflation
- [ ] non-claims retained: no project completion / no runtime active / no formal publish

## Follow-on trigger

- [ ] follow-on batch requested only after the evidence bundle is fully repo-visible under canonical root
