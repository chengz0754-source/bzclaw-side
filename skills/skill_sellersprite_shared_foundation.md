# skill_sellersprite_shared_foundation

## Purpose
- This skill is the shared SellerSprite foundation layer for all four purpose lines.
- It is not a closure skill.
- It exists to keep shared blockers, shared runner usage, and progress-board updates in one reusable place.

## Use This Skill When
- A shortlisted or purpose-routed SellerSprite line is blocked at:
  - `STEP1 Product Research`
  - `STEP4 Competitor / export-log`
- You need to update the shared foundation truth before reopening any line-specific closure work.

## Do Not Use This Skill For
- Rewriting route semantics
- Claiming SellerSprite closure
- Starting SIF
- Running T03/T04 empirical lines early

## Required Inputs
- Current route row in `inputs/selection_run_current/01_选品任务路由与目的.csv`
- Downstream validation input row for the current term
- Fixed STEP3 PASS slice when the active downstream term already came from shortlist confirmation

## Standard Command
```powershell
.\.venv\Scripts\python.exe scripts/run_sellersprite_shared_foundation.py --context-row-index 1
```

## Expected Outputs
- `reports/CODEX_SHARED_FOUNDATION_SUMMARY_20260412.md`
- `reports/MASTER_PROGRESS_BOARD__20260412.csv` updated in repo
- `logs/shared_foundation/latest_run.json`

## What To Read From The Result
- whether STEP1 still blocks before real product sample-source formation
- whether STEP4 still blocks before real competitor sample-source formation
- whether the blocker shrank from replay plumbing to a cleaner surface/auth usability truth
- what the next exact slice is for the active line
