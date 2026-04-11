# SellerSprite Benchmark Chain Contract

## Scope

- This contract standardizes the SellerSprite benchmark / competitor chain for STEP4.
- The chain does not replace STEP3 market gating or pretend STEP2 is already live.
- Runtime artifacts stay under ignored `outputs/`, `logs/`, and `runs/`.

## Upstream Seed Rules

- Standard seed priority:
  - STEP1 PASS product seed from `12_产品样本下推结果.csv`
  - otherwise STEP3 PASS market seed from `32_市场调研下推结果.csv`
  - otherwise manual seed override for explicit diagnostic runs only
- Current repo truth on `2026-04-09`:
  - the code now resolves benchmark seeds from STEP1 before STEP3; STEP2 is no longer the formal STEP4 seed surface
  - `claw machine / US` can resolve a formal STEP1 seed when a valid `12_产品样本下推结果.csv` exists
  - if neither STEP1 nor STEP3 can provide a PASS seed, the canonical chain still fails closed
- The benchmark chain must fail closed if no PASS STEP1/STEP3 seed can be resolved.

## Control Surfaces

- STEP4 field contracts come from:
  - `templates/selection_canonical_standards/99_字段数据标准总表.csv`
- STEP4 gate thresholds come from:
  - `templates/selection_canonical_standards/90_下推参数表.csv`
- Current execution context still resolves from:
  - `inputs/selection_run_current/01_市场入口与筛选参数.csv`
- Manual fields remain manual:
  - `方向ID`
  - any later compliance / improvement / final decision fields

## Collector

- Raw collector:
  - `scripts/export_benchmark_competitors.py`
- Query surface:
  - `https://www.sellersprite.com/v3/competitor-lookup`
- Export-log surface:
  - `https://www.sellersprite.com/v2/export-log`
- Live data route:
  - query on the benchmark page
  - trigger page export
  - poll `我的导出`
  - download `Competitor-*.xlsx`
  - parse workbook into `benchmark_competitor_raw.json`
- Verified execution mode on `2026-04-09`:
  - dedicated persistent profile `playwright/profiles/sellersprite-main/`
  - headed Edge context
- Current compatibility note:
  - the headed profile path can trigger export and poll export-log successfully
  - export-log does not auto-refresh, so the collector must reload it at a bounded interval
  - because of that, the default live collector keeps `headless=False`

## Standard Outputs

- Raw JSON artifact:
  - `benchmark_competitor_raw.json`
- Canonical STEP4 outputs:
  - `40_竞品基准结果.csv`
  - `41_候选产品种子池.csv`
  - `42_竞品基准下推结果.csv`
- Output indexes:
  - `benchmark_chain_output_index.csv`
  - `benchmark_chain_output_index.md`

By default these files are generated into:

`outputs/selection_runs/<timestamp>/02_generated_outputs/`

They are runtime artifacts and must not enter git.

## Layer Semantics

### 1. Raw benchmark layer

- `benchmark_competitor_raw.json`
- Captures:
  - resolved upstream seed context
  - applied page filters
  - export-log task metadata
  - downloaded workbook path / sheet metadata
  - raw competitor item list parsed from SellerSprite export workbook

### 2. Canonical raw CSV layer

- `40_竞品基准结果.csv`
- One row per raw benchmark competitor item.
- Field order is locked to `99_字段数据标准总表.csv`.

### 3. Candidate seed pool layer

- `41_候选产品种子池.csv`
- Deterministic dedupe rule:
  - prefer `父体ASIN`
  - fallback to `样品ASIN`
  - keep the row with the highest `评论数`, then `评分`, then `价格`
- No human explanation or “改良点” is generated here.

### 4. Gate result layer

- `42_竞品基准下推结果.csv`
- Rule source:
  - STEP4 rows in `90_下推参数表.csv`
- Current STEP4 aggregate metrics:
  - `候选ASIN数`
  - `评分中位数`
  - `头部评论占比`
  - `价格离散度`
- Gate semantics:
  - any hard-fail breach => `FAIL`
  - otherwise any soft-fail breach => `HOLD`
  - only all-pass candidate pools => `PASS`

## Commands

### Live benchmark collection

```powershell
.\.venv\Scripts\python.exe scripts\export_benchmark_competitors.py `
  --context-row-index 1 `
  --output-dir outputs/selection_runs/20260408_p05_probe/02_generated_outputs
```

### Live benchmark collection with direct seed override

```powershell
.\.venv\Scripts\python.exe scripts\export_benchmark_competitors.py `
  --context-row-index 3 `
  --seed-keyword "claw machine" `
  --seed-market-name "claw machine" `
  --output-dir outputs/selection_runs/20260409_claw_machine/02_generated_outputs
```

### Optional workbook re-parse

```powershell
.\.venv\Scripts\python.exe scripts\parse_benchmark_export_workbook.py `
  --workbook runs/manual/20_benchmark_exports/sample_inspect/Competitor-US-Last-30-days-145827.xlsx `
  --context-row-index 1 `
  --output-dir outputs/selection_runs/20260408_p05_probe/02_generated_outputs
```

### STEP4 canonical build

```powershell
.\.venv\Scripts\python.exe scripts\build_benchmark_seed_pool.py `
  --context-row-index 1 `
  --direction-id DIR_001 `
  --output-dir outputs/selection_runs/20260408_p05_probe/02_generated_outputs
```

## Fail-Closed Rules

- Do not use STEP3 market outputs as fake STEP4 benchmark rows.
- If the page export does not create a usable `Competitor-*` task in `我的导出`, the collector must block.
- If the downloaded workbook cannot be saved or parsed, the collector must block.
- If no PASS STEP1/STEP3 seed can be resolved, the collector must block.
- If `方向ID` is blank and not explicitly overridden, the STEP4 builder must block.
- If the raw benchmark artifact is missing or not `PASS`, the STEP4 builder must block.

## Current Repo Truth

- Verified STEP4 live page export on `2026-04-09` through the formal STEP1 seed route:
  - query keyword: `claw machine`
  - seed source step: `STEP1_PRODUCT_GATE`
  - candidate market name: `Arcade & Table Games`
  - page export created `Competitor-US-Last-30-days-177154` in `我的导出`
  - downloaded `Competitor-US-Last-30-days-177154.xlsx` parsed successfully into `benchmark_competitor_raw.json`
  - canonical `40/41/42` then built successfully with overall STEP4 gate status `PASS`
- Verified product-first nightly routing on `2026-04-09`:
  - `export_benchmark_competitors.py` now resolves formal seeds from `12_产品样本下推结果.csv` before falling back to `32_市场调研下推结果.csv`
  - `claw machine / US` resolved a formal STEP1 seed with `candidate_market_name=Arcade & Table Games`
  - the current live blocker is no longer missing seed resolution; it is SellerSprite auth on `v2/export-log`, which returned `SELLERSPRITE_AUTH_REQUIRED` in the `nightly_v3` run before workbook download began
- Current status classification:
  - collector/page-download route: `CLOSED_AT_CHAIN_LAYER`
  - formal upstream seed routing: `CLOSED_AT_CODE_LAYER`
  - latest nightly stability for `claw machine / US`: `PARTIAL`, because `v2/export-log` auth can still regress between runs
