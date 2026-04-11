# SellerSprite Recording And Export Stability Guide

## Why Raw Codegen Is No Longer Recommended

Direct raw codegen from the SellerSprite home page is too fragile for this repo because the live surface can be interrupted by:

- upgrade prompts
- floating customer-service widgets
- tutorial banners
- marketing overlays
- guest/login redirects
- export-center tasks that require polling instead of dead waiting

The repo now treats recording and execution as two separate layers:

1. Recording only captures short, stable interaction fragments.
2. Overlay governance, retries, polling, downloads, screenshots, and failure classification stay in code.

## New Entry Points

### 1. Recording launcher

- Script: `scripts/record_sellersprite_keyword_export_flow.py`

Modes:

- `keyword_result`
  - opens the direct SellerSprite `v3/keyword-miner` result route
  - runs overlay governance
  - opens `page.pause()` for segmented recording
- `export_log`
  - opens `https://www.sellersprite.com/v2/export-log`
  - runs overlay governance
  - opens `page.pause()` for segmented recording

Recommended commands:

```powershell
.\.venv\Scripts\python.exe scripts\record_sellersprite_keyword_export_flow.py --mode keyword_result
```

```powershell
.\.venv\Scripts\python.exe scripts\record_sellersprite_keyword_export_flow.py --mode export_log
```

Self-test form without opening the inspector:

```powershell
.\.venv\Scripts\python.exe scripts\record_sellersprite_keyword_export_flow.py --mode keyword_result --headless --no-pause --dry-run
```

```powershell
.\.venv\Scripts\python.exe scripts\record_sellersprite_keyword_export_flow.py --mode export_log --headless --no-pause --dry-run
```

### 2. Export executor

- Script: `scripts/run_sellersprite_keyword_export_flow.py`

Purpose:

- trigger export from the direct `v3/keyword-miner` result page
- handle the confirmation prompt
- enter `我的导出`
- lock the correct task row by task-name tokens such as `KeywordHistory`, keyword slug, and site
- poll task status until completed with a conservative interval
- click download inside the matched row only
- validate that the file was really downloaded

Recommended command:

```powershell
.\.venv\Scripts\python.exe scripts\run_sellersprite_keyword_export_flow.py --context-row-index 1
```

More conservative live command:

```powershell
.\.venv\Scripts\python.exe scripts\run_sellersprite_keyword_export_flow.py --context-row-index 1 --max-wait-seconds 120 --poll-interval-seconds 8
```

Dry-run command:

```powershell
.\.venv\Scripts\python.exe scripts\run_sellersprite_keyword_export_flow.py --context-row-index 1 --dry-run
```

## What To Record

### On `keyword_result`

Only record small segments such as:

- row selection
- export button click
- export confirmation dialog recognition

Do not record:

- home-page navigation
- repeated overlay closing
- polling loops
- hard-coded sleeps

### On `export_log`

Only record stable page interactions such as:

- export task row observation
- download button location inside the matched task row

Do not record:

- waiting several minutes manually
- refresh timing by hand
- timeout judgment
- failure routing

Those are now handled by `run_sellersprite_keyword_export_flow.py`.

## Overlay Governance

- Public module: `scripts/sellersprite_overlay_guard.py`

The guard works in two layers:

1. Close predictable overlays normally when a stable close control exists.
2. Hide persistent blocking layers with injected CSS and conservative JS fallback rules.

It is intentionally re-run before critical actions.

## Waiting Logic That Must Stay In Code

These waits must not be recorded into Playwright snippets:

- waiting for the export dialog
- waiting for the export-log task to appear
- waiting for `导出中` to become `已完成`
- waiting for the browser download event
- validating file existence, filename, suffix, and file size

## Main Failure Reason Codes

- `RESULT_PAGE_BLOCKED_BY_OVERLAY`
  - the intended click target on the result page was still blocked after overlay governance and one retry
- `EXPORT_DIALOG_NOT_VISIBLE`
  - export was triggered, but the expected confirmation prompt did not appear in time
- `EXPORT_CONFIRM_BUTTON_NOT_VISIBLE`
  - the prompt appeared, but no stable `前往查看` / `查看` control could be found
- `EXPORT_LOG_TASK_NOT_FOUND`
  - no sufficiently matching task row was found in `我的导出`
- `EXPORT_LOG_STATUS_TIMEOUT`
  - the task row was found, but it never reached a completed state before timeout
- `EXPORT_DOWNLOAD_BUTTON_NOT_VISIBLE`
  - the completed row was found, but the download control was not visible
- `EXPORT_FILE_NOT_DOWNLOADED`
  - the download event did not fire, the file did not land, the size was zero, or the saved filename failed validation
- `UNEXPECTED_MODAL_BLOCKING_ACTION`
  - a blocking modal, alert, or unplanned popup interrupted the current action
- `SELLERSPRITE_AUTH_REQUIRED`
  - the current storage state or profile still lands on guest/login state

## Runtime Artifacts

Local-only runtime paths used by the new flow:

- Logs:
  - `logs/sellersprite_keyword_export_flow/`
- Screenshots:
  - `playwright/screenshots/sellersprite_keyword_export_flow/`
- Downloads:
  - `runs/manual/20_keyword_exports/`

These artifacts must stay out of git.

## Current Repo Truth On 2026-04-08

- `我的导出` stable route is `https://www.sellersprite.com/v2/export-log`
- current stable result surface is `https://www.sellersprite.com/v3/keyword-miner/?q=<keyword>&marketId=<id>&batch=0`
- the executor no longer treats the old `v2/keyword-research` submit path as the primary export trigger path
- the executor uses conservative pacing, bounded retries, bounded polling, and explicit reason codes instead of dead waits
- if auth is not reusable, the scripts still fail closed with explicit reason codes rather than pretending the export succeeded
