# Ads Phase1 Decision Sheet

- decision_sheet_id: `ads-phase1-decision-example`
- linked_problem_card_id: `ads-phase1-problem-example`
- decision_owner: `B`
- approval_owner: `Pending Human Approval`
- approval_status: `PENDING`
- decision_date: `2026-04-13`

## Objective

Reduce wasted spend without reducing the converting exact target's traffic.

## Diagnosis

- Broad traffic is spending above tolerance with weak conversion.
- One exact target remains profitable and should be protected.

## Chosen Actions

- action_type: `LOWER_BID`
- scope: `broad target: squeeze toys sensory bin`
- expected_effect: Reduce CPC on low-efficiency traffic.
- guardrail: Keep the bid above the floor needed to maintain test traffic.

- action_type: `ADD_NEGATIVE`
- scope: `phrase negative: dog chew toy`
- expected_effect: Block irrelevant traffic leakage.
- guardrail: Apply only at the ad group where waste was observed.

## Verification Window

- same_session: Check row acceptance and the exact entity scope.
- plus_24h: Review spend pacing and wasted query share.
- plus_72h: Check ACOS trend and confirm the converting exact target kept volume.

## Rollback Trigger

Rollback if spend drops on the converting exact target or if the negative blocks relevant traffic.
