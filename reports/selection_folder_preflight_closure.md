# Selection Folder Preflight Closure

## Summary

- Audit baseline: `CONDITIONAL`
- Current decision: `PREFLIGHT_CLOSED`
- Preparation status: `READY_FOR_FORMAL_IMPLEMENTATION`
- can_start_formal_implementation: `YES`
- downstream prompt blocked: `NO`

## Git truth recheck

- `git status --short --branch` at preflight start returned `## main...origin/main`
- `git branch --show-current` returned `main`
- `git log --oneline -n 20` returned the visible recent commits:
  - `b442723 项目更新`
  - `31322de 项目更新`
  - `8c22f1a 项目更新`
  - `2f54a27 项目更新`
  - `d2e9d09 项目更新`
  - `198af91 add sellersprite auth bootstrap baseline`
  - `a441a8f bootstrap selection automation repo boundary and legacy skill import`
- No pre-existing tracked dirty files were present before the current closure work started.

## Closure decisions

### 1. Auth path alignment

- Current operational auth path is `playwright/auth/sellersprite.storage_state.json`.
- Verified scripts already used the canonical path:
  - `scripts/bootstrap_sellersprite_auth.py`
  - `scripts/check_sellersprite_session.py`
- Updated current operational docs:
  - `README.md`
  - `reports/NEXT_ACTIONS.md`
- Historical audit artifacts still preserve the old `playwright/auth/storage_state.json` reference as evidence of the original mismatch:
  - `reports/selection_folder_preflight_checklist.md`
  - `reports/selection_folder_audit_baseline.csv`
  - `reports/selection_folder_audit_dataflow_status.csv`
- Those historical files are not the current operational source of truth and were intentionally left intact.

### 2. `runs/manual/10_market/` keep-set / archive-set

- Repo-visible files under `runs/manual/10_market/`:
  - `market-report-us-squeeze-toys-d30-new6m-sample100-head10-20260406_055235.xlsx`
  - `Market-research(1)SqueezeToys-US-Last-30-days.xlsx`
  - `diag-old-Market-research(1)SqueezeToys-US-Last-30-days.xlsx`
- All three `.xlsx` files have identical internal workbook entry hashes, so they are content-equivalent business workbooks.
- Canonical keep-set decision:
  - keep `market-report-us-squeeze-toys-d30-new6m-sample100-head10-20260406_055235.xlsx` as the authoritative default raw workbook
- Archive / diagnostic-set decision:
  - `Market-research(1)SqueezeToys-US-Last-30-days.xlsx` remains a preserved SellerSprite-suggested name copy
  - `diag-old-Market-research(1)SqueezeToys-US-Last-30-days.xlsx` remains a local diagnostic/archive copy
- Script hardening landed in `scripts/map_market_report_to_candidate_pool.py`:
  - prefer newest `market-report-*.xlsx`
  - fallback to newest non-diagnostic `.xlsx`
  - fail closed if only `diag-*` / `archive-*` copies remain

### 3. Partial archive semantics

- `outputs/selection_runs/20260407_004949` contains only `02_generated_outputs/`.
- That directory is now explicitly classified as a `partial mapping artifact package`.
- It is not a full run archive because it does not contain:
  - `00_run_summary.md`
  - `01_consumed_inputs/`
  - `03_logs/`
- `outputs/selection_runs/20260407_090101` is the current repo-visible example of a full archive package.
- README and `reports/中文CSV运行归档规则.md` now encode this distinction.

### 4. Current working inputs

- Current repo-visible working inputs are:
  - `inputs/selection_run_current/00_选品运行目标与边界.csv`
  - `inputs/selection_run_current/01_市场入口与筛选参数.csv`
  - `inputs/selection_run_current/03_候选市场与候选品初筛池.csv`
- Evidence:
  - current `00/01/03` hashes differ from both:
    - `templates/selection_csv_cn_reference/`
    - `outputs/selection_runs/20260407_090101/01_consumed_inputs/`
- `inputs/selection_run_current/02_账号与合规预检查.csv` still matches the template and the archived consumed-input snapshot.
- `templates/selection_csv_cn_reference/04_供应链询价与利润核算.csv` remains a post-cost sheet and is not a preflight blocker.
- Important boundary:
  - current `00/01/03` are the authoritative repo-visible working copies for formal development
  - current business values are still provisional/example values and must be manually confirmed before live business execution

### 5. Script-level preflight verification

- `.venv\Scripts\python.exe -c "import openpyxl"` passed.
- `scripts/map_market_report_to_candidate_pool.py` previously failed on current working inputs because it assumed `utf-8-sig` only.
- The script now supports `utf-8-sig`, `utf-8`, `gb18030`, and `gbk` when reading current input CSV files.
- Verified command:

```powershell
.\.venv\Scripts\python.exe scripts\map_market_report_to_candidate_pool.py --dry-run --output-dir outputs/selection_runs/20260407_preflight_probe/02_generated_outputs
```

- Result:
  - dry-run completed successfully
  - no candidate CSV was rewritten
  - a local ignored probe artifact was created under `outputs/selection_runs/20260407_preflight_probe/`

## Worktree classification

- Tracked changes to review/commit:
  - `README.md`
  - `reports/NEXT_ACTIONS.md`
  - `reports/中文CSV运行归档规则.md`
  - `reports/selection_folder_preflight_closure.md`
  - `reports/selection_folder_preflight_closure.csv`
  - `reports/selection_folder_rebuild_decision.csv`
  - `scripts/map_market_report_to_candidate_pool.py`
- Local ignored runtime data that should be retained locally and not committed:
  - `playwright/auth/sellersprite.storage_state.json`
  - `playwright/auth/storage_state.smoke.json`
  - `playwright/profiles/chromium-user-data/`
  - `playwright/profiles/sellersprite-main/`
  - `runs/manual/10_market/*.xlsx`
  - `outputs/selection_runs/20260407_004949/`
  - `outputs/selection_runs/20260407_090101/`
  - `outputs/selection_runs/20260407_preflight_probe/`
- No user input files were deleted.
- No manual business fields were auto-filled by this closure pass.

## Final decision

- rebuild_needed: `NO`
- rebuild_level: `KEEP_SKELETON_AND_CONTINUE`
- can_start_formal_implementation: `YES`
- downstream prompt blocked: `NO`
