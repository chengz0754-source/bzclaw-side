# MARKET EXPORT PROOF

## Scripts

- `scripts/bootstrap_sellersprite_auth.py`
  - Manual login refresh entrypoint. It opens the dedicated SellerSprite automation profile, waits for manual login, and saves a fresh local `storage_state` snapshot.
- `scripts/check_sellersprite_session.py`
  - Reuse check for the saved local session snapshot. Run it after a refresh if you want a clean-context validation.
- `scripts/export_market_report.py`
  - Daily market-table export runner. It uses the dedicated local SellerSprite automation profile, supports dry-run / retry / run logs, and saves the workbook into `runs/manual/10_market/`.
- `scripts/build_market_workbook_index.py`
  - Standard STEP3 builder. It converts the selected keep-set workbook into `30/31/32` canonical outputs plus workbook/output indexes.
- `scripts/record_login_with_edge.py`
  - Backward-compatible alias to the auth bootstrap flow.
- `scripts/record_market_export.py`
  - Backward-compatible alias to the formal market export runner.

## Normal Use Order

1. Refresh auth only when SellerSprite login is expired:
   - `.\.venv\Scripts\python.exe scripts\bootstrap_sellersprite_auth.py`
2. Optionally verify the saved session snapshot:
   - `.\.venv\Scripts\python.exe scripts\check_sellersprite_session.py`
3. Run the daily market export:
   - `.\.venv\Scripts\python.exe scripts\export_market_report.py`
4. Build the standard STEP3 data layer from the selected keep-set workbook:
   - `.\.venv\Scripts\python.exe scripts\build_market_workbook_index.py --context-row-index 1 --direction-id DIR_001`

## Default Export Inputs

- Site: `US`
- Keyword: `Squeeze Toys`
- Range: `last 30 days`
- New product window: `6 months`
- Listing sample size: `top 100`
- Head listing size: `top 10`
- Output directory: `runs/manual/10_market/`
- Standard output directory for parsed STEP3 artifacts:
  - `outputs/selection_runs/<timestamp>/02_generated_outputs/`

## Standardized Chain Outputs

- Raw workbook layer:
  - `runs/manual/10_market/market-report-*.xlsx`
  - `logs/market_exports/*.json`
- Cleaned layer:
  - `31_市场调研清洗结果.csv`
  - `market_cleaned.csv` (compatibility alias)
- Gate result layer:
  - `32_市场调研下推结果.csv`
- Index artifacts:
  - `market_workbook_index.csv`
  - `market_workbook_index.md`
  - `market_chain_output_index.csv`
  - `market_chain_output_index.md`

## Auth Stability Decision

- The dedicated local Edge profile at `playwright/profiles/sellersprite-main/` is the default execution path for daily exports.
- The saved `playwright/auth/sellersprite.storage_state.json` remains useful as a local session snapshot and refresh validation artifact.
- Local testing on `2026-04-06` showed that the profile path completed a real workbook download, while a clean `storage_state` context reused the session for page entry but did not reliably surface the export control in the same flow.

## Last Verified Export

- Verified on: `2026-04-06`
- Runner: `scripts/export_market_report.py`
- Output directory: `runs/manual/10_market/`
- Saved file: `market-report-us-squeeze-toys-d30-new6m-sample100-head10-20260406_055235.xlsx`
- SellerSprite suggested file name: `Market-research(1)SqueezeToys-US-Last-30-days.xlsx`

## Latest Standardization Probe

- Verified on: `2026-04-07`
- Export dry-run:
  - `.\.venv\Scripts\python.exe scripts\export_market_report.py --dry-run --context-row-index 1`
- STEP3 build probe:
  - `.\.venv\Scripts\python.exe scripts\build_market_workbook_index.py --context-row-index 1 --direction-id DIR_001 --output-dir outputs/selection_runs/20260407_p03_probe/02_generated_outputs`
- Result:
  - raw workbook keep-set was selected successfully
  - `30_市场调研原始索引.csv`, `31_市场调研清洗结果.csv`, and `32_市场调研下推结果.csv` were generated successfully
  - current probe gate summary was `PASS=1 FAIL=0 HOLD=0`

## Do Not Commit

- `playwright/auth/sellersprite.storage_state.json`
- `playwright/profiles/sellersprite-main/`
- `runs/manual/10_market/*.xlsx`
- `playwright/screenshots/`
- `playwright/traces/`
