# SellerSprite Market Route Step1 To Step3

This skill advances the SellerSprite market line from `M02_market_cleaned` to:

- `M03_niche_shortlist`
- `M04_benchmark_asin_scored`
- `K01_keyword_pool`
- `K02_keyword_shortlist`

It is a file-first, config-driven workflow. It does not make final launch, profit, supply-chain, IP, or SIF decisions.

## Scope

This skill is responsible for:

- `M02_market_cleaned -> M03_niche_shortlist`
- `M03_niche_shortlist -> benchmark_asin_download_queue -> M04_benchmark_asin_scored`
- `M04_benchmark_asin_scored -> reverse_keyword_download_queue -> K01_keyword_pool -> K02_keyword_shortlist`

This skill does not include:

- SIF
- final product selection
- launch approval
- browser automation
- SellerSprite downloading

Future Playwright handoff points are:

- `benchmark_asin_download_queue`
- `reverse_keyword_download_queue`

## Inputs

- Upstream `M02_market_cleaned*.csv|xlsx|jsonl` files under `../skill-market-route-m01-to-m02/outputs/<run_id>/`
- Benchmark raw files dropped into `inbox/benchmark_raw/`
- Keyword raw files dropped into `inbox/keyword_raw/`

The default Step1 scanner only reads upstream output folders, not upstream archive folders, unless the code is explicitly extended for that purpose.

When orchestrated, Step1 should receive one explicit validated upstream file via
`--m02-file` instead of guessing from mixed historical outputs.

## Outputs

Each pipeline run creates a unique `run_id` under:

- `outputs/<run_id>/step1/`
- `outputs/<run_id>/step2/`
- `outputs/<run_id>/step3/`
- `outputs/<run_id>/summaries/`
- `logs/<run_id>/`
- `archive/<run_id>/manifests/`

## Run

From the dropzone root:

```powershell
python .\skill-market-route-step1-to-step3\scripts\run_market_route_pipeline.py --root .
```

Examples:

```powershell
python .\skill-market-route-step1-to-step3\scripts\run_market_route_pipeline.py --root . --mode balanced
python .\skill-market-route-step1-to-step3\scripts\run_market_route_pipeline.py --root . --start-step step2 --batch-id market_research_200_squeezetoys_us_last_30_days
python .\skill-market-route-step1-to-step3\scripts\run_market_route_pipeline.py --root . --m02-file .\skill-market-route-m01-to-m02\outputs\20260401_045329\csv\M02_market_cleaned__US__market_research_200_squeezetoys_us_last_30_days.csv
python .\skill-market-route-step1-to-step3\scripts\run_market_route_pipeline.py --root . --dry-run
```

Windows wrappers:

- `bat/run_market_route_pipeline.bat`
- `ps1/run_market_route_pipeline.ps1`

## Status Model

Persisted status codes:

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

Every step writes status into its output table and manifest. Nothing depends on hidden in-memory state.

## Path Policy

`configs/path_policy.yaml` supports:

- `mode: advisory`
- `mode: strict_include_only`

In `strict_include_only`, only whitelist hits may reach `PASS_TO_STEP2`. All
other paths become `DROP__PATH_POLICY`.

## Resume Model

- Step1 reads the latest upstream `M02` output per `batch_id`
- Step2 waits if `inbox/benchmark_raw/` does not contain usable raw evidence
- Step3 waits if `inbox/keyword_raw/` does not contain usable raw evidence
- Once raw files are present, rerun the same pipeline entrypoint and it will continue from files

## Boundary

This skill stops at `K02_keyword_shortlist` with a max forward state of `PASS_READY_FOR_SIF`.

It does not:

- decide if the market should be launched
- decide final supply-chain feasibility
- decide final legal or IP safety
- delete raw evidence files
