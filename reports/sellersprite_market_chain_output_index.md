# SellerSprite Market Chain Output Index

## Contracted artifacts

| artifact_id | layer | artifact_name | default_location | generated_by | commit_policy | note |
| --- | --- | --- | --- | --- | --- | --- |
| `RAW_WORKBOOK` | raw_workbook_layer | `market-report-<site>-<keyword>-d<days>-new<months>m-sample<sample>-head<head>-<timestamp>.xlsx` | `runs/manual/10_market/` | `scripts/export_market_report.py` | `LOCAL_ONLY` | Canonical keep-set raw workbook naming for the verified export path |
| `MARKET_EXPORT_RUN_LOG_JSON` | raw_workbook_layer | `<timestamp>-market-export-<site>-<keyword>.json` | `logs/market_exports/` | `scripts/export_market_report.py` | `LOCAL_ONLY` | Per-run export log with resolved controls and attempts |
| `MARKET_EXPORT_RUNS_JSONL` | raw_workbook_layer | `export_runs.jsonl` | `logs/market_exports/` | `scripts/export_market_report.py` | `LOCAL_ONLY` | Append-only run ledger for export attempts |
| `MARKET_EXPORT_FAILURES_JSONL` | raw_workbook_layer | `export_failures.jsonl` | `logs/market_exports/` | `scripts/export_market_report.py` | `LOCAL_ONLY` | Append-only failure ledger written only for failed exports |
| `MARKET_WORKBOOK_INDEX_CSV` | raw_workbook_layer | `market_workbook_index.csv` | `outputs/selection_runs/<timestamp>/02_generated_outputs/` | `scripts/build_market_workbook_index.py` | `LOCAL_ONLY` | Inventory of all repo-visible workbook copies and selected keep-set |
| `MARKET_WORKBOOK_INDEX_MD` | raw_workbook_layer | `market_workbook_index.md` | `outputs/selection_runs/<timestamp>/02_generated_outputs/` | `scripts/build_market_workbook_index.py` | `LOCAL_ONLY` | Human-readable workbook inventory summary |
| `STEP3_RAW_INDEX` | raw_workbook_layer | `30_市场调研原始索引.csv` | `outputs/selection_runs/<timestamp>/02_generated_outputs/` | `scripts/build_market_workbook_index.py` | `LOCAL_ONLY` | Canonical raw index row for the selected workbook |
| `STEP3_CLEANED` | cleaned_layer | `31_市场调研清洗结果.csv` | `outputs/selection_runs/<timestamp>/02_generated_outputs/` | `scripts/build_market_workbook_index.py` | `LOCAL_ONLY` | Canonical STEP3 cleaned layer |
| `MARKET_CLEANED_ALIAS` | cleaned_layer | `market_cleaned.csv` | `outputs/selection_runs/<timestamp>/02_generated_outputs/` | `scripts/build_market_workbook_index.py` | `LOCAL_ONLY` | Compatibility alias of the canonical STEP3 cleaned layer |
| `STEP3_GATE_RESULT` | gate_result_layer | `32_市场调研下推结果.csv` | `outputs/selection_runs/<timestamp>/02_generated_outputs/` | `scripts/build_market_workbook_index.py` | `LOCAL_ONLY` | Canonical STEP3 gate result layer |
| `MARKET_CHAIN_OUTPUT_INDEX_CSV` | run_output_layer | `market_chain_output_index.csv` | `outputs/selection_runs/<timestamp>/02_generated_outputs/` | `scripts/build_market_workbook_index.py` | `LOCAL_ONLY` | Machine-readable inventory of the generated raw/cleaned/gate artifacts |
| `MARKET_CHAIN_OUTPUT_INDEX_MD` | run_output_layer | `market_chain_output_index.md` | `outputs/selection_runs/<timestamp>/02_generated_outputs/` | `scripts/build_market_workbook_index.py` | `LOCAL_ONLY` | Human-readable inventory of the generated raw/cleaned/gate artifacts |

## Canonical interpretation

- Raw export controls are resolved from `inputs/selection_run_current/01_市场入口与筛选参数.csv` or explicit CLI overrides.
- STEP3 field order and required columns are fixed by `templates/selection_canonical_standards/99_字段数据标准总表.csv`.
- STEP3 gate thresholds are fixed by `templates/selection_canonical_standards/90_下推参数表.csv`.
- These artifacts are runtime outputs and must not be committed to git.
