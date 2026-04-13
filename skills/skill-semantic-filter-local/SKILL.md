---
name: skill-semantic-filter-local
description: Filter the latest `M03_niche_shortlist` workbook or csv with a local-only semantic denoise pass using Ollama's OpenAI-compatible endpoint and fixed model `qwen3:4b-instruct`. Use when Codex needs to remove only low-match noise from `PASS_TO_STEP2` rows, keep upstream hard gates intact, and emit `M03_semantic_filtered`, `semantic_filter_manifest`, and `semantic_benchmark_queue` outputs under timestamped run folders.
---

# Skill Semantic Filter Local

## Overview

Apply a conservative semantic filter on top of Step1 output.

Stay inside:

- `M03_niche_shortlist -> M03_semantic_filtered`
- `PASS_TO_STEP2 -> semantic_benchmark_queue`

Do not turn this skill into a final niche-selection decision maker.

## Runtime Contract

- Use only local Ollama.
- Use only `http://localhost:11434/v1/`.
- Use only model `qwen3:4b-instruct`.
- Use `api_key=ollama`.
- Do not call any external API.

## Input Contract

- Read the latest `M03_niche_shortlist__*.xlsx` or `.csv` under the selected
  root unless `--m03-file` is explicit.
- Read at least these fields:
  - `query_seed`
  - `dept_l1`
  - `parent_l2`
  - `niche_leaf`
  - `path_key`
  - `niche_en`
  - `niche_zh`
  - `market_path_raw`
  - `step1_score`
  - `step1_status`
  - `step1_pass_reason`
  - `step1_drop_reason`
- Treat `step1_status == PASS_TO_STEP2` as the only rows eligible for semantic
  downgrading.

## Decision Boundary

- Do not overturn upstream hard gates.
- Do not rescue rows already dropped by Step1.
- Only remove obvious low-match semantic noise from rows that already passed
  Step1.
- Use only these labels:
  - `KEEP`
  - `REVIEW`
  - `DROP_LOW_MATCH`
- Be conservative:
  - `KEEP` for direct or strong semantic matches
  - `REVIEW` for ambiguous or adjacent matches
  - `DROP_LOW_MATCH` only for clearly low-match noise

`final_keep_flag` should remain `True` for `KEEP` and `REVIEW`, and `False`
only for `DROP_LOW_MATCH` or non-`PASS_TO_STEP2` rows.

## Output Contract

Every run must create a unique `run_id` and write only inside this skill:

- `outputs/<run_id>/M03_semantic_filtered__{batch_id}.xlsx`
- `outputs/<run_id>/M03_semantic_filtered__{batch_id}.csv`
- `outputs/<run_id>/semantic_filter_manifest__{run_id}.json`
- `outputs/<run_id>/semantic_benchmark_queue__{batch_id}.csv`
- `logs/<run_id>/...`

Do not write result files back into the root workspace.

## Main Entrypoint

```powershell
python .\skill-semantic-filter-local\scripts\run_semantic_filter.py --root .
```

Supported flags:

- `--m03-file`
- `--batch-id`
- `--run-id`
- `--overwrite`
- `--debug`

## References Inside This Skill

- Read `configs/semantic_filter_config.yaml` for the fixed runtime contract and
  output conventions.
- Read `AGENTS.md` before changing the skill boundary.
- Use `README.md` for operator-facing run notes.
