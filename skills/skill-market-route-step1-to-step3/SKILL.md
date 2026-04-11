---
name: skill-market-route-step1-to-step3
description: Drive SellerSprite market-line files from M02 through K02 with config-driven state transitions, queue files, and resumable local runs.
---

# Skill Market Route Step1 To Step3

## When To Use

Use this skill when the working folder already contains:

- `skill-market-route-m01-to-m02`
- upstream `M02_market_cleaned` outputs

And you need to advance the SellerSprite market line without crossing into final selection judgment.

## Workflow Contract

This skill only advances:

1. `M02_market_cleaned -> M03_niche_shortlist`
2. `M03_niche_shortlist -> benchmark_asin_download_queue -> M04_benchmark_asin_scored`
3. `M04_benchmark_asin_scored -> reverse_keyword_download_queue -> K01_keyword_pool -> K02_keyword_shortlist`

The workflow is data-driven and file-driven:

- thresholds come from config
- statuses are persisted to files
- manifests and run logs are written every run
- future Playwright automation consumes queue files only
- orchestrated runs should pass one validated upstream `M02` file via
  `--m02-file`

## Run Directory Contract

The dropzone root is expected to be the parent directory of this skill, for example:

- `E:\bzclaw_inputs\选品`

The skill writes only into its own subdirectories:

- `outputs/<run_id>/`
- `logs/<run_id>/`
- `archive/<run_id>/manifests/`
- `inbox/benchmark_raw/`
- `inbox/keyword_raw/`

## Root Cleanliness Contract

This skill does not write result tables back into the root dropzone.

It reads upstream `M02` artifacts from:

- `../skill-market-route-m01-to-m02/outputs/<run_id>/`

It does not delete or rewrite upstream outputs or archives.

## Timestamped Output Contract

Every run generates a unique `run_id` in `YYYYMMDD_HHMMSS` format.

All outputs for a run are grouped under that `run_id`:

- step workbooks
- csv files
- queue files
- manifests
- step logs
- pipeline summaries

## Archive Contract

This skill does not hard-delete evidence.

It stores pipeline manifests and summary artifacts under:

- `archive/<run_id>/manifests/`

The inbox folders remain as evidence drop points for future downloaded raw tables.

## State Machine

Supported states:

- `READY_FOR_STEP1`
- `PASS_TO_STEP2`
- `REVIEW_BUFFER`
- `DROP`
- `WAIT_BENCHMARK_RAW`
- `READY_FOR_STEP2_PROCESSING`
- `PASS_TO_STEP3`
- `WAIT_KEYWORD_RAW`
- `READY_FOR_STEP3_PROCESSING`
- `PASS_READY_FOR_SIF`

## Operational Rules

- Do not invent benchmark or keyword raw files.
- Do not replace hard gates with LLM judgment.
- Do not delete rows silently.
- Keep `DROP` rows in the output with reasons.
- Keep `REVIEW_BUFFER` rows for later human review.
- Queue generation is mandatory when the next raw evidence file is missing.

## Main Entrypoint

```powershell
python .\skill-market-route-step1-to-step3\scripts\run_market_route_pipeline.py --root .
```

Supported flags:

- `--start-step step1|step2|step3`
- `--mode balanced|new_seller|low_competition|opportunity|manual_review_heavy`
- `--dry-run`
- `--batch-id`
- `--m02-file`
- `--overwrite`
- `--debug`
