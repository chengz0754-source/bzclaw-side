# SellerSprite Market Chain Contract

## Scope

- This contract standardizes the SellerSprite market-research chain without replacing the already verified raw export path.
- Upstream gate: P02 canonical standards are already landed in `templates/selection_canonical_standards/`.
- Repo truth first:
  - raw workbook export remains profile-based and browser-driven
  - standard parsing and gating are added as a downstream layer
  - runtime outputs stay under ignored `runs/`, `outputs/`, and `logs/`

## Control Surfaces

- Raw export controls come from `inputs/selection_run_current/01_市场入口与筛选参数.csv` or explicit CLI overrides:
  - `方向词`
  - `站点`
  - `时间范围_天`
  - `新品定义_天`
  - `样本数前N`
  - `头部商品前N`
- STEP3 field contracts come from:
  - `templates/selection_canonical_standards/99_字段数据标准总表.csv`
- STEP3 gate thresholds come from:
  - `templates/selection_canonical_standards/90_下推参数表.csv`
- Important boundary:
  - `90_下推参数表.csv` currently governs the `32_市场调研下推结果.csv` gate layer.
  - Export controls such as site / time window / sample size / head size are still resolved from current input `01` or explicit CLI overrides, because those controls are not encoded as rows in the current `90` table.

## Layers

### 1. Raw workbook layer

- Canonical export runner:
  - `scripts/export_market_report.py`
- Canonical workbook naming:
  - `runs/manual/10_market/market-report-<site>-<keyword>-d<days>-new<months>m-sample<sample>-head<head>-<timestamp>.xlsx`
- Keep-set selection rule:
  - prefer newest `market-report-*.xlsx`
  - fallback to newest non-diagnostic `.xlsx`
  - fail closed if only `diag-*` / `archive-*` copies remain
- Runtime logs:
  - `logs/market_exports/<timestamp>-market-export-<site>-<keyword>.json`
  - `logs/market_exports/export_runs.jsonl`
  - `logs/market_exports/export_failures.jsonl`
  - `logs/market_exports/latest_run.json`

### 2. Cleaned layer

- Standard builder:
  - `scripts/build_market_workbook_index.py`
- Canonical cleaned output:
  - `31_市场调研清洗结果.csv`
- Compatibility alias:
  - `market_cleaned.csv`
- Both files in the standard chain use the canonical STEP3 cleaned schema from `99_字段数据标准总表.csv`.

### 3. Gate result layer

- Canonical gate output:
  - `32_市场调研下推结果.csv`
- Rule source:
  - `templates/selection_canonical_standards/90_下推参数表.csv`
- Gate semantics:
  - any hard-fail rule breach => `FAIL`
  - otherwise any soft-fail rule breach => `HOLD`
  - only all-pass rows => `PASS`
  - only `PASS` rows may be marked `是否下推到Step4 = 是`

## Standard Outputs

- Raw workbook inventory:
  - `market_workbook_index.csv`
  - `market_workbook_index.md`
- STEP3 canonical outputs:
  - `30_市场调研原始索引.csv`
  - `31_市场调研清洗结果.csv`
  - `32_市场调研下推结果.csv`
- Standard output inventory:
  - `market_chain_output_index.csv`
  - `market_chain_output_index.md`

By default these files are generated into:

`outputs/selection_runs/<timestamp>/02_generated_outputs/`

They are runtime artifacts and must not enter git.

## Commands

### Raw export dry-run

```powershell
.\.venv\Scripts\python.exe scripts\export_market_report.py --dry-run --context-row-index 1
```

### Raw export actual run

```powershell
.\.venv\Scripts\python.exe scripts\export_market_report.py --context-row-index 1
```

### STEP3 standard build from latest keep-set workbook

```powershell
.\.venv\Scripts\python.exe scripts\build_market_workbook_index.py `
  --context-row-index 1 `
  --direction-id DIR_001
```

## Fail-Closed Rules

- Do not auto-fill manual fields in current input `01`.
- If `方向ID` is blank in `inputs/selection_run_current/01_市场入口与筛选参数.csv`, the standard builder must fail closed unless the operator passes `--direction-id`.
- If the selected canonical workbook name encodes controls that do not match the resolved site / time / sample / head settings, the builder must fail closed.
- If workbook parsing cannot identify a stable market sheet/header row, the builder must fail closed.
- Diagnostic or archive workbook copies may be retained locally, but they must not be selected as the default keep-set workbook.

## Current Repo Truth

- Current verified keep-set workbook:
  - `runs/manual/10_market/market-report-us-squeeze-toys-d30-new6m-sample100-head10-20260406_055235.xlsx`
- Verified live `claw machine / US` export on `2026-04-09`:
  - `scripts/export_market_report.py --context-row-index 3` reached the page successfully
  - SellerSprite returned `暂无结果` under the canonical `US / 30天 / 新品180天 / 样本100 / 头部10` controls
  - therefore no canonical raw market workbook was downloaded for `claw machine`, and no `30/31/32` package could be built for that direction
- Current repo-visible `01` now contains a manual `方向ID` for the `claw machine` validation row.
