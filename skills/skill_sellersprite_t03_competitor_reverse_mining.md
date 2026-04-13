# skill_sellersprite_t03_competitor_reverse_mining

## Purpose
- This skill is the reusable T03 / `COMPETITOR_REVERSE_MINING` line runner for one real ASIN / brand / seller seed.
- It exists to keep the `STEP4 benchmark -> reverse seed lineage -> STEP2 keyword/traffic -> STEP1 product remap -> optional STEP3 market remap -> STEP7 candidate pool` path deterministic.
- It is a line-closure skill, not a SellerSprite-wide closure claim.

## Use This Skill When
- The line purpose is `COMPETITOR_REVERSE_MINING`.
- The seed is real and comes from T01 or T02 repo-visible outputs.
- We want one reverse-mining pilot to reach Candidate Pool and become reusable.

## Do Not Use This Skill For
- Inventing a virtual ASIN / brand / seller seed
- Skipping the reverse seed lineage or keyword / traffic layer
- Rewriting the route into market-first
- Reopening T01 / T02 / T04 closure work
- Entering SIF
- Claiming SellerSprite-wide closure

## Required Inputs
- Pilot input:
  - `inputs/selection_run_current/05C__INPUT_TEMPLATE__T03_COMPETITOR_REVERSE_MINING__20260412.csv`
- Real seed lineage:
  - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/11_产品样本种子池.csv`
  - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/12_产品样本下推结果.csv`
- Deepest empirical reverse/validation artifacts currently reused by the pilot:
  - STEP4:
    - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/41_候选产品种子池.csv`
    - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/42_竞品基准下推结果.csv`
  - STEP2:
    - `outputs/selection_runs/20260410_auth_replay_formal/02_generated_outputs/22_关键词证据词池下推结果.csv`
  - STEP1 remap:
    - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/12_产品样本下推结果.csv`
  - STEP3 optional remap:
    - `outputs/selection_runs/20260411_t02_toy_parameterized_step3/02_generated_outputs/32_市场调研下推结果.csv`

## Standard Command
```powershell
.\.venv\Scripts\python.exe scripts/run_t03_competitor_reverse_mining.py
```

## Expected Outputs
- `reports/CODEX_T03_COMPETITOR_REVERSE_MINING_SUMMARY_20260412.md`
- `reports/MASTER_PROGRESS_BOARD__20260412.csv` updated on row `P3`
- `logs/t03_competitor_reverse_mining/latest_run.json`

## What To Read From The Result
- which real seed was consumed and where it came from
- whether the reverse-mining line reaches Candidate Pool
- whether STEP3 stayed optional enrichment instead of a universal hard gate
- which parts are inherited from deepest empirical truth versus freshly rerun in this slice
