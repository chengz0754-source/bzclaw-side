---
name: skill-market-route-m01-to-m02
description: Clean local SellerSprite market export workbooks named `Market-research*.xlsx` into reusable M02 intermediate tables for the market route. Use when Codex or an operator needs to parse the sheet's second-row headers, preserve first-row grouping semantics, split market paths and compound text fields, and emit `market_cleaned`, `path_summary`, `field_dictionary`, and `run_log` outputs without making final product-selection judgments.
---

# Skill Market Route M01 To M02

## Overview

Convert one or more local SellerSprite market-research Excel exports into a
standard M02 intermediate package.

Stay inside `M01_raw_market_export -> M02_market_cleaned`. Do not make final
selection, profitability, shortlist, or competitor decisions.

## Inputs

- Scan only the current input directory for `Market-research*.xlsx`.
- Do not recurse into subdirectories.
- Treat row 1 as a grouping row and row 2 as the true header row.
- Ignore `Notes` for tabular parsing, but preserve its presence in run metadata.

## Required Outputs

For each input workbook, emit one output basename under `outputs/`:

- `M02_market_cleaned__{marketplace}__{batch_id}.xlsx`
- matching `.csv`
- matching `.jsonl`

The workbook must contain:

- `market_cleaned`
- `path_summary`
- `field_dictionary`
- `run_log`

## Core Transform Rules

- Normalize output field names to English snake_case.
- Keep the raw workbook untouched.
- Split:
  - market path by `:`
  - sample counts by labeled lines
  - seller type by strict `FBA:` / `AMZ:` / `FBM:` percentage regex
  - seller country and share from the multi-line country block
- Store percentage fields as 0 to 1 decimals only for the fields declared in
  the schema.
- Emit `seller_share_sum` and `seller_share_parse_flag` for downstream quality
  validation.
- Leave uncertain filename-derived fields blank and log the uncertainty instead
  of guessing.
- Default control fields:
  - `keep_flag = REVIEW_PENDING`
  - `drop_reason = ""`
  - `next_action = BUILD_NICHE_SHORTLIST`
  - `next_object_type = niche`

## Run Order

1. Run `run_market_m01_to_m02.py` directly, or use the `.bat` / `.ps1`
   wrappers.
2. Review `run_log` and logs under `logs/` for parse warnings or failures.
3. Use `path_summary` to decide later path contraction in `M03`.

## Run Directory Contract

- Treat the root workspace as a temporary dropzone only.
- Scan only the selected input directory for `Market-research*.xlsx`.
- Do not recurse into subdirectories.
- Do not treat files inside the skill folder as inputs.

## Root Cleanliness Contract

- Do not leave successfully processed raw inputs in the root dropzone.
- Do not write output workbook, csv, or jsonl files into the root dropzone.
- Default behavior is archive move, not destructive deletion.
- Only allow hard-delete style source removal when the operator explicitly uses
  `--hard-delete-root-input-after-success`.

## Timestamped Output Contract

- Generate one unique `run_id` per execution.
- Write all outputs for that run under `outputs/{run_id}/`.
- Write all logs for that run under `logs/{run_id}/`.
- Do not mix multiple runs into one flat directory.

## Archive Contract

- On success, move raw inputs to `archive/processed/{run_id}/raw_inputs/`.
- On failure, move raw inputs to `archive/failed/{run_id}/raw_inputs/`.
- Write `run_manifest.json` under `archive/processed/{run_id}/manifests/`.
- If any failures occurred, also write `run_manifest.json` under
  `archive/failed/{run_id}/manifests/`.
- Never delete a raw input unless archive safety has already succeeded.

## References Inside This Skill

- Read `schema/m02_market_cleaned_schema.json` for field order, types, and
  source mappings.
- Read `prompts/codex_operator_prompt.md` when handing this skill to another
  Codex session.
- Read `AGENTS.md` before making changes so the skill stays in the M02
  boundary.

## Non-Goals

- Do not score products.
- Do not recommend a final niche.
- Do not do competitor analysis.
- Do not delete rows just because the route is broad or noisy.
- Do not treat this stage as business proof or final selection output.
