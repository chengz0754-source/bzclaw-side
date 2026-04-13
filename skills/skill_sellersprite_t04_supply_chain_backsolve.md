# skill_sellersprite_t04_supply_chain_backsolve

## Purpose
- This skill is the reusable T04 / `SUPPLY_CHAIN_BACKSOLVE` line runner for one real supplier-family boundary.
- It exists to keep the `supply boundary -> STEP1 product evidence + STEP3 market remap -> STEP4 benchmark -> STEP2 keyword/traffic -> STEP7 candidate pool` path deterministic.
- It is a line-closure skill, not a SellerSprite-wide closure claim.

## Use This Skill When
- The line purpose is `SUPPLY_CHAIN_BACKSOLVE`.
- The pilot starts from one real `supplier_family`.
- We want one supplier-family backsolve pilot to reach Candidate Pool and become reusable.

## Do Not Use This Skill For
- Leaving `supplier_family` blank
- Rewriting the line into T01 market discovery or T02 exact-product validation
- Skipping the supply boundary, market remap, benchmark, or keyword/traffic evidence layers
- Reopening T01 / T02 / T03 closure work
- Entering SIF
- Claiming SellerSprite-wide closure

## Required Inputs
- Pilot input:
  - `inputs/selection_run_current/05D__INPUT_TEMPLATE__T04_SUPPLY_CHAIN_BACKSOLVE__20260412.csv`
- Real supplier-family source:
  - `inputs/selection_run_current/01B_产品与竞品种子输入.csv`
- Deepest empirical artifacts currently reused by the pilot:
  - STEP1:
    - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/12_产品样本下推结果.csv`
  - STEP4:
    - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/41_候选产品种子池.csv`
    - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/42_竞品基准下推结果.csv`
  - STEP2:
    - `outputs/selection_runs/20260410_auth_replay_formal/02_generated_outputs/22_关键词证据词池下推结果.csv`
  - STEP3 optional market remap:
    - `outputs/selection_runs/20260411_t02_toy_parameterized_step3/02_generated_outputs/32_市场调研下推结果.csv`

## Standard Command
```powershell
.\.venv\Scripts\python.exe scripts/run_t04_supply_chain_backsolve.py
```

## Expected Outputs
- `reports/CODEX_T04_SUPPLY_CHAIN_BACKSOLVE_SUMMARY_20260412.md`
- `reports/MASTER_PROGRESS_BOARD__20260412.csv` updated on row `P4`
- `logs/t04_supply_chain_backsolve/latest_run.json`

## What To Read From The Result
- which real supplier family was consumed and where it came from
- which real product/market lineage the supplier family backsolved through
- whether the supplier-family line reaches Candidate Pool
- whether STEP3 stayed optional enrichment instead of becoming a universal hard gate
- which parts are inherited from deepest empirical truth versus freshly rerun in this slice
