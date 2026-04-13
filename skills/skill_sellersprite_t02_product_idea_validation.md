# skill_sellersprite_t02_product_idea_validation

## Purpose
- This skill is the reusable T02 / `PRODUCT_IDEA_VALIDATION` line runner for one exact product-idea pilot.
- It exists to keep the `STEP1 product -> STEP4 benchmark -> STEP2 keyword/traffic -> optional STEP3 broad market mapping -> STEP7 candidate pool` path deterministic.
- It is a line-closure skill, not a SellerSprite-wide closure claim.

## Use This Skill When
- The target line is one exact product idea under `PRODUCT_IDEA_VALIDATION`.
- The repo already contains deeper existing truth for that idea than the active mainline does.
- You want to materialize that existing truth into a reusable line runner, summary, and progress-board update.

## Do Not Use This Skill For
- Rewriting T02 into a market-first line
- Promoting STEP3 back into a universal hard gate
- Reopening T03 / T04 empirical work
- Entering SIF
- Claiming SellerSprite-wide closure

## Required Inputs
- Pilot input:
  - `inputs/selection_run_current/05B__INPUT_TEMPLATE__T02_PRODUCT_IDEA_VALIDATION__20260412.csv`
- Deepest existing truth for the pilot idea:
  - formal STEP1 artifacts
  - formal STEP4 artifacts
  - formal STEP2 artifacts
  - optional STEP3 artifacts
  - candidate-pool projection

## Standard Command
```powershell
.\.venv\Scripts\python.exe scripts/run_t02_product_idea_validation.py
```

## Expected Outputs
- `reports/CODEX_T02_PRODUCT_IDEA_VALIDATION_SUMMARY_20260412.md`
- `reports/MASTER_PROGRESS_BOARD__20260412.csv` updated on row `P2`
- `logs/t02_product_idea_validation/latest_run.json`

## What To Read From The Result
- whether the line closure standard is met at the reusable-process layer
- whether STEP3 stays optional enrichment instead of a mandatory gate
- whether Candidate Pool already forms real rows from the formal artifacts
- which non-PASS business layers still keep SellerSprite overall `NOT_CLOSED`
