# skill_sellersprite_t01_market_discovery

## Purpose
- This skill is the reusable T01 / `MARKET_DISCOVERY` line runner for one shortlisted market term.
- It is a line-closure skill, not a program-wide closure skill.
- It exists to keep the `shortlist -> product -> benchmark -> keyword/traffic -> candidate pool` path deterministic for one real T01 term.

## Use This Skill When
- The active line is a shortlisted market term under `MARKET_DISCOVERY`.
- You want to run or rerun the first full SellerSprite downstream-validation lane for that term.
- The term already has a confirmed STEP3 shortlist slice or a fixed market-pass slice.

## Do Not Use This Skill For
- Reopening `claw machine`
- Rewriting route semantics
- Running T02 / T03 / T04 empirical closure work
- Entering SIF
- Claiming SellerSprite-wide closure
- Treating owner-side manual writeback fields as current-stage blockers

## Required Inputs
- Pilot input in `inputs/selection_run_current/05A__INPUT_TEMPLATE__T01_MARKET_DISCOVERY__20260412.csv`
- Active T01 row in `inputs/selection_run_current/01_选品任务路由与目的.csv`
- Active line input in `inputs/selection_run_current/01__SHORTLIST_DOWNSTREAM_VALIDATION_INPUT__TOY_2_TERMS__20260411.csv` or the current T01 line input replacement
- A fixed STEP3 pass slice for the current shortlisted term

## Standard Command
```powershell
.\.venv\Scripts\python.exe scripts/run_t01_market_discovery.py --context-row-index 1
```

## Expected Outputs
- `reports/CODEX_T01_MARKET_DISCOVERY_SUMMARY_20260412.md`
- `reports/MASTER_PROGRESS_BOARD__20260412.csv` updated on row `P1`
- `logs/t01_market_discovery/latest_run.json`

## What To Read From The Result
- whether STEP1 formed a real product sample source
- whether STEP4 formed a real competitor sample source
- whether STEP2 evidence formed even if workbook export stayed blocked
- whether STEP7 emitted real candidate rows or remained fail-closed
- whether the `05A` pilot input stayed aligned with the active `T11` lane
- what the next exact slice is for the T01 line

## Stage Boundary
- This skill ends at the SellerSprite current-stage candidate-pool boundary.
- Blank owner-side fields in `60_候选样品池.csv` do not mean current-stage flow failure:
  - `合规`
  - `改良点`
  - `最终解释`
  - `利润核价`
- Those fields belong to owner-side manual writeback, not SellerSprite current-stage blocking logic.
