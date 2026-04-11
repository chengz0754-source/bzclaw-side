# Semantic Filter Local

`skill-semantic-filter-local` adds one local semantic denoise layer between
Step1 and benchmark download.

It reads the newest `M03_niche_shortlist__*.xlsx` or `.csv`, sends only local
requests to Ollama's OpenAI-compatible endpoint, and writes filtered outputs
into timestamped run folders inside this skill.

## Hard Constraints

- No external API calls
- Ollama only
- Fixed model: `qwen3:4b-instruct`
- Fixed endpoint: `http://localhost:11434/v1/`
- Fixed api key value: `ollama`
- Semantic labels only:
  - `KEEP`
  - `REVIEW`
  - `DROP_LOW_MATCH`

## Boundary

- Semantic filtering is allowed only on rows where `step1_status` is
  `PASS_TO_STEP2`.
- Rows already blocked by Step1 stay blocked.
- The semantic layer may only remove low-match noise.
- `KEEP` and `REVIEW` continue to the benchmark queue.
- `DROP_LOW_MATCH` is the only semantic outcome that flips
  `final_keep_flag` to `False`.

## Input Fields

The runner validates at least these columns:

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

## Outputs

Each run writes:

- `outputs/<run_id>/M03_semantic_filtered__{batch_id}.xlsx`
- `outputs/<run_id>/M03_semantic_filtered__{batch_id}.csv`
- `outputs/<run_id>/semantic_filter_manifest__{run_id}.json`
- `outputs/<run_id>/semantic_benchmark_queue__{batch_id}.csv`
- `logs/<run_id>/semantic_filter_run_log__{run_id}.json`

The root workspace stays clean.

## Run

From the workspace root:

```powershell
python .\skill-semantic-filter-local\scripts\run_semantic_filter.py --root .
```

Optional examples:

```powershell
python .\skill-semantic-filter-local\scripts\run_semantic_filter.py --root . --debug
python .\skill-semantic-filter-local\scripts\run_semantic_filter.py --root . --batch-id market_research_200_squeezetoys_us_last_30_days
python .\skill-semantic-filter-local\scripts\run_semantic_filter.py --root . --m03-file .\skill-market-route-step1-to-step3\outputs\20260401_172239\step1\xlsx\M03_niche_shortlist__market_research_200_squeezetoys_us_last_30_days.xlsx
```

Wrappers:

- `bat/run_semantic_filter.bat`
- `ps1/run_semantic_filter.ps1`

## Output Columns Added

The filtered table always includes:

- `semantic_label`
- `semantic_reason`
- `semantic_confidence`
- `final_keep_flag`

It also writes helper fields such as `semantic_applied`, `semantic_run_id`,
and `semantic_model` for traceability.
