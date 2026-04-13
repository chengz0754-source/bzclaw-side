# ADS Phase1 Verify And Rollback Playbook

## Goal

Protect manual ads changes with explicit before-and-after checks plus a clear
rollback path.

## Before Manual Upload

- confirm the approved decision sheet matches the bulk draft
- snapshot current bid, budget, targeting, and negative state
- verify the operator, timestamp, and marketplace

## After Manual Upload

- record upload time and operator
- confirm the platform accepted the intended rows
- log partial failures or rejected rows immediately

## Verification Window

- same session: confirm row acceptance and settings appearance
- 24 hours: check pacing, spend, and anomaly flags
- 72 hours: compare efficiency, traffic quality, and rollback trigger status

## Rollback Triggers

- sudden spend spike without conversion lift
- severe traffic loss from overblocking
- wrong entity edited or wrong marketplace selected
- approval mismatch between sheet and manual action

## Required Artifacts

- upload receipt
- verification note
- rollback record if any reversal was needed

Use `templates/ads_manual_adjustment/ads_upload_receipt.template.md` and
`templates/ads_manual_adjustment/ads_verify_rollback.template.md`.
