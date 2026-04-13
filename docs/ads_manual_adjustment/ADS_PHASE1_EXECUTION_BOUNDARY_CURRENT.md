# ADS Phase1 Execution Boundary

## Scope

This Phase1 landing set supports manual ads adjustment preparation only.

## Inputs

- problem evidence captured by analysts or operators
- approved decision context for a limited change batch
- target-level plan rows for review CSV generation

## Outputs

- context pack markdown and manifest
- decision sheet markdown
- review-only bulk CSV draft
- verification notes and run records

## Hard Boundaries

- no platform auto-upload
- no platform runtime-open claim
- no approval bypass
- no writes outside this business repository for this batch

## Approval Rules

- `requires_approval` is mandatory for both supporting skills
- any proposed change must remain reversible
- approval identity and timestamp must be captured before manual application

## Storage Rules

- docs live in `docs/ads_manual_adjustment/`
- reusable templates live in `templates/ads_manual_adjustment/`
- helper scripts live in `scripts/ads_manual_adjustment/`
- supporting-only skills live in `skills/ads_manual_adjustment_*`
- reports, runs, inputs, and outputs stay under their matching repo folders
