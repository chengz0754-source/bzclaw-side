# Bulk Builder Contract

## Purpose

Render a review-only bulk CSV from a human-approved plan.

## Inputs Required

- stable campaign and ad group names
- explicit action type
- target expression or negative scope
- approval-gated status marker

## Boundaries

- no platform upload
- no browser control
- no hidden default approvals

## Success Criteria

- output CSV matches the repository template header
- every row preserves the approved scope and note
