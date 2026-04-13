# ADS Phase1 Decision Playbook

## Goal

Translate a verified diagnosis into a limited, reviewable action plan that a
human operator can approve and apply manually.

## Approved Action Types

- raise or lower bids within guardrails
- pause underperforming targets
- add exact or phrase negatives
- separate harvest candidates into tighter match types
- adjust placement modifiers only when evidence supports it

## Decision Rules

### Raise Bid

Use when impressions are constrained, conversion is healthy, and the target is
strategically important.

### Lower Bid

Use when the target spends meaningfully above tolerance and still fails to
convert.

### Pause Target

Use when the target repeatedly violates efficiency thresholds and no listing or
offer fix is expected in the near term.

### Add Negative

Use when search term evidence shows clear irrelevance or repeated low-value
traffic leakage.

## Guardrails

- avoid stacking more than two major changes on the same target in one batch
- never mix diagnosis uncertainty with aggressive budget expansion
- record approval owner, rollback trigger, and verification window for every
  proposal

## Required Output

Decision output must be captured in
`templates/ads_manual_adjustment/ads_decision_sheet.template.md` and, when
approved, translated into the review CSV draft.
