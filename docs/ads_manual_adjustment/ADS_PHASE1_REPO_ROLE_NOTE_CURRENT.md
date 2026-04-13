# ADS Phase1 Repo Role Note

## Purpose

This repository is the execution workspace for Ads Phase1 manual adjustment
preparation. It stores operator-facing docs, review templates, helper scripts,
supporting-only skills, and evidence reports needed to prepare a manual ads
change package.

## What This Repo Is Allowed To Do

- collect and structure adjustment evidence
- render review sheets for human approval
- build review-only bulk CSV proposals
- store receipts, verification notes, and run manifests

## What This Repo Must Not Do

- auto-open the advertising console
- claim runtime execution on the platform
- auto-upload or auto-apply changes
- skip approval for bid, budget, target, or negative actions

## Human Control Requirements

- every change proposal needs explicit approval before manual upload
- the final bulk CSV is a draft artifact for review, not proof of execution
- verification and rollback steps must be recorded after the operator acts

## Delivery Anchor

The delivery index for this landing set is
`docs/ads_manual_adjustment/ADS_PHASE1_DELIVERY_INDEX.md`.
