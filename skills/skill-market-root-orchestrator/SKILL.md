---
name: skill-market-root-orchestrator
description: Orchestrate root-dropzone SellerSprite market-line runs by chaining M01->M02, validating latest M02 quality, and launching Step1->Step3 only from approved upstream files.
---

# Skill Market Root Orchestrator

## When To Use

Use this skill when the working root contains:

- `skill-market-route-m01-to-m02`
- `skill-market-route-step1-to-step3`
- zero or more `Market-research*.xlsx` files in the root dropzone

And the goal is to run the market-line root workflow without leaving stale raw
files behind or consuming stale M02 outputs.

## Workflow

1. Scan the root dropzone for `Market-research*.xlsx`
2. Run `skill-market-route-m01-to-m02`
3. Verify processed root inputs moved into archive
4. Validate the newest manifest-approved `M02`
5. If valid, run `skill-market-route-step1-to-step3` with explicit `--m02-file`
6. Write one orchestrator manifest with final root-clean status

## Quality Gate

The orchestrator blocks downstream execution when the newest manifest-approved
M02 fails any hard gate:

- required columns missing
- ratio fields outside `0~1`
- `seller_share_parse_flag` contains `INVALID_PARSE`
- seller-share abnormal rate exceeds config

## Root Cleanliness Contract

- The root dropzone must not retain processed `Market-research*.xlsx`
- The root dropzone must not receive `M02` outputs
- The orchestrator verifies final root cleanliness after both skills run

## Entrypoint

```powershell
python .\skill-market-root-orchestrator\scripts\run_market_root_orchestrator.py --root .
```
