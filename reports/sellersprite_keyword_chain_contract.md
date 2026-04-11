# SellerSprite Keyword Chain Contract

## Scope

- This contract standardizes the SellerSprite keyword-research and keyword-trend chain for STEP2.
- Canonical field and gate sources remain:
  - `templates/selection_canonical_standards/99_字段数据标准总表.csv`
  - `templates/selection_canonical_standards/90_下推参数表.csv`
- Runtime outputs stay local-only under ignored `logs/`, `outputs/`, and `playwright/`.

## Modules

### 1. Keyword research module

- Script: `scripts/export_keyword_research.py`
- Page/export target:
  - `https://www.sellersprite.com/v3/keyword-miner`
  - `https://www.sellersprite.com/v2/export-log`
- Purpose:
  - reuse the stabilized page-export workflow in `scripts/run_sellersprite_keyword_export_flow.py`
  - trigger `KeywordHistory-*` export from the live v3 keyword result page
  - download the workbook from `我的导出`
  - parse the latest-month history row into repo-local raw JSON for downstream canonicalization

### 2. Keyword trend module

- Script: `scripts/export_keyword_trend.py`
- Page target: `https://www.sellersprite.com/v3/keyword-miner`
- Purpose:
  - open the live v3 keyword miner result route directly with the resolved keyword/site
  - read the visible related-keyword result table from the page surface itself
  - capture trend-oriented keyword evidence and trend-surface presence
  - persist a repo-local raw JSON artifact for downstream canonicalization

### 3. Canonical STEP2 builder

- Script: `scripts/build_keyword_evidence_pool.py`
- Purpose:
  - combine successful raw module outputs
  - standardize them into canonical STEP2 raw / cleaned / gate layers
  - fail closed when no successful raw collector output is available

## Canonical Outputs

- Raw layer:
  - `20_关键词证据词池原始结果.csv`
- Cleaned layer:
  - `21_关键词证据词池清洗结果.csv`
- Gate result layer:
  - `22_关键词证据词池下推结果.csv`
- Runtime output index:
  - `keyword_chain_output_index.csv`
  - `keyword_chain_output_index.md`

By default these files are emitted into:

`outputs/selection_runs/<timestamp>/02_generated_outputs/`

They are local runtime artifacts and must not enter git.

## Control Surfaces

- Current input context comes from:
  - `inputs/selection_run_current/01_市场入口与筛选参数.csv`
- STEP2 gate rules come from:
  - `templates/selection_canonical_standards/90_下推参数表.csv`
- STEP2 field order comes from:
  - `templates/selection_canonical_standards/99_字段数据标准总表.csv`

Current repo-standard STEP2 gate rules in `90_下推参数表.csv` are:

- `S2_MIN_SEARCH_VOLUME`
- `S2_MIN_GROWTH_PCT`
- `S2_MAX_CLICK_CONCENTRATION`
- `S2_MAX_TRAFFIC_COST_INDEX`
- `S2_REQUIRE_OPPORTUNITY_OR_TREND`

## Important Boundary

- The current canonical `90_下推参数表.csv` does not contain a dedicated noise-word rule row.
- To avoid inventing unapproved gate logic:
  - noise handling is limited to deterministic cleaned-layer exclusion in `21_关键词证据词池清洗结果.csv`
  - the STEP2 gate in `22_关键词证据词池下推结果.csv` still uses only the current repo-standard rule rows from `90_下推参数表.csv`
- This keeps the pipeline fail-closed and avoids pretending that a missing canonical rule already exists.

## Deterministic Cleaned-Layer Rules

- The model is not used to expand keywords.
- The builder only performs deterministic:
  - normalization
  - de-duplication
  - role tagging
  - grouping
- The cleaned layer may mark a keyword as excluded when it is:
  - blank or non-signal
  - numeric-only
  - an ASIN-like token
  - too short
  - an exact platform-noise term such as `amazon` / `tiktok` / `temu` / `shein`

## Derived Metric Notes

- SellerSprite surfaces expose PPC bid values in USD more directly than a native `流量成本指数`.
- To stay inside the `99_字段数据标准总表.csv` allowance for an internal normalized indicator, the builder currently derives:
  - `流量成本指数 = min(100, PPC竞价_USD * 100)`
- This means the current STEP2 threshold `70` maps to a normalized equivalent of `0.70 USD`.

## Live Truth On 2026-04-09

- `scripts/run_sellersprite_keyword_export_flow.py` has already proven the live page route:
  - open `v3/keyword-miner/?q=...`
  - select a result row
  - click `导出明细`
  - jump to `我的导出`
  - poll until `已完成`
  - download `KeywordHistory-*.xlsx`
- `scripts/export_keyword_research.py` reuses that stabilized export route and parses the downloaded workbook instead of relying on the old `v2/keyword-research` submit path.
- Verified execution detail on `2026-04-09`:
  - the dedicated persistent profile currently lands `v3/keyword-miner` in a `未登录 / 游客` surface for `claw machine`, so the export button remains disabled there
  - switching the same collector to `--execution-mode storage_state` restores the export workflow and downloads `KeywordHistory-claw-machine-US-*.xlsx`
  - `scripts/export_keyword_trend.py` can still read the visible v3 result table directly from the page surface even when the page header shows `未登录 / 游客`
- Verified live `claw machine / US` run on `2026-04-09`:
  - `keyword_research_raw.json`: `PASS` through `storage_state`, workbook `KeywordHistory-claw-machine-US-*.xlsx` downloaded successfully
  - `keyword_trend_raw.json`: `PASS`, `20` visible keyword rows parsed successfully
  - `20/21/22`: built successfully, current gate summary `PASS=0 / FAIL=7 / HOLD=12`

This means STEP2 can now produce the canonical `20/21/22` artifact package for `claw machine`, but the gate layer still fail-closes under the current canonical thresholds.

Additional same-day auth truth on `2026-04-09`:

- Formal STEP2 main path is:
  - `keyword_research(storage_state workbook export)` + `keyword_trend(v3 visible table)` + `build_keyword_evidence_pool`
- A later re-run at `04:26 +08:00` showed the repo-local `storage_state` had degraded to the SellerSprite login page for keyword research.
- The persistent profile also degraded for the keyword surfaces, so fresh raw recollection is currently auth-blocked again.
- This auth regression does not erase the earlier same-day real `20/21/22` package; it means the current raw-collection state requires auth refresh before a new workbook/table capture can be claimed.

Current status classification on `2026-04-09`:

- artifact chain: `CLOSED_AT_ARTIFACT_LAYER`
- business gate: `HOLD`
- fresh raw recollection: `BLOCKED_BY_AUTH_REPLAY_GAP`

## Commands

### Keyword research dry-run

```powershell
.\.venv\Scripts\python.exe scripts\export_keyword_research.py --dry-run --context-row-index 1
```

### Keyword research live attempt

```powershell
.\.venv\Scripts\python.exe scripts\export_keyword_research.py --context-row-index 1 --execution-mode storage_state
```

### Keyword trend dry-run

```powershell
.\.venv\Scripts\python.exe scripts\export_keyword_trend.py --dry-run --context-row-index 1
```

### Keyword trend live attempt

```powershell
.\.venv\Scripts\python.exe scripts\export_keyword_trend.py --context-row-index 1
```

### STEP2 canonical build

```powershell
.\.venv\Scripts\python.exe scripts\build_keyword_evidence_pool.py `
  --context-row-index 1 `
  --direction-id DIR_001
```

## Fail-Closed Rules

- Do not auto-fill manual `方向ID`.
- If `方向ID` is blank, `scripts/build_keyword_evidence_pool.py` must fail closed unless an explicit CLI override is provided.
- If no successful raw keyword collector output exists, the builder must fail closed and log the blocker.
- If SellerSprite redirects keyword-research to login, do not fabricate raw rows.
- If the trend page surface is visible but no stable query request/result table can be proven, do not fabricate trend rows.
- In the nightly router, a real STEP2 build with `gate_summary.PASS = 0` must stay `HOLD`; it may not block downstream real-sample fallback paths by pretending to be `PASS`.
