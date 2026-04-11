# SellerSprite Research Execution Pack

## Scope

This pack objectizes the current B-side SellerSprite product research and benchmark/competitor chain.

Included business lanes:

- STEP1 Product Research
  - `scripts/export_product_research.py`
  - `scripts/build_product_seed_pool.py`
- STEP4 Benchmark / Competitor
  - `scripts/export_benchmark_competitors.py`
  - `scripts/build_benchmark_seed_pool.py`

Included support surfaces:

- auth replay governance
  - `scripts/sellersprite_auth_registry.py`
  - `scripts/sellersprite_auth_replay.py`
- workbook parsers
  - `scripts/parse_product_export_workbook.py`
  - `scripts/parse_benchmark_export_workbook.py`
- screenshot/guard support
  - `scripts/sellersprite_overlay_guard.py`

This pack does not mean:

- final product verdict
- final benchmark verdict
- SellerSprite business closure

## Current Anchors On 2026-04-11

Canonical repo root for prompts:

- `E:\bzclaw-side`

Observed local runtime sample root still holding the real samples:

- `E:\选品文件夹\amazon-selection-automation`

Normative interpretation:

- use `B_PATH_BASELINE_MAP.csv` for the canonical alias-to-local mapping
- treat the observed local runtime root as debug context only

Path rule:

- repo-relative identity first
- absolute Windows path only as debug support

Observed real sample set:

- Product collector sample
  - `logs/formal_next_slice_20260410/step1_product/latest_product_research_run.json`
  - `runs/manual/15_product_exports/20260410_next_slice_formal/Product-US-Last-30-days-209236.xlsx`
  - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/product_research_raw.json`
- Product build sample
  - `logs/formal_next_slice_20260410/step1_product_build/latest_product_build_run.json`
  - `10/11/12/13/13a/13b` under the same run folder
- Benchmark collector sample
  - `logs/formal_next_slice_20260410/step4_benchmark/latest_benchmark_export_run.json`
  - `runs/manual/20_benchmark_exports/20260410_next_slice_formal/Competitor-US-Last-30-days-209270.xlsx`
  - `outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/benchmark_competitor_raw.json`
- Benchmark build sample
  - `logs/formal_next_slice_20260410/step4_benchmark_build/latest_benchmark_build_run.json`
  - `40/41/42` and `benchmark_chain_output_index.*`

Observed sample facts:

- product collector sample recorded `status=PASS`, `execution_mode=persistent_profile`, `matched_task_name=Product-US-Last-30-days-209236`, `visible_market_entry_count=60`
- benchmark collector sample recorded `status=PASS`, `execution_mode=persistent_profile`, `matched_task_name=Competitor-US-Last-30-days-209270`, `seed_source_step=STEP1_PRODUCT_GATE`
- observed workbook sizes were `128260` and `128261` bytes
- both workbook samples had the main data sheet plus `Notes`

## Unified Chain

The current execution chain is:

1. input profile
2. page open and query
3. export trigger
4. export-log task lock
5. workbook download
6. workbook parse
7. canonical build
8. summary and evidence

### Input profile

Required profile dimensions:

- `run_name`
- `direction_id`
- `keyword`
- `site`
- `days`
- `sample_top_n`
- optional `max_candidate_samples`
- for STEP4 also:
  - `seed_source_step`
  - `seed_keyword`
  - `candidate_market_name`
  - `market_path`

Current materialization:

- current input row in `inputs/selection_run_current/01_市场入口与筛选参数.csv`
- CLI overrides
- STEP4 `seed_context`

### Page and export stage

Current live surfaces:

- `https://www.sellersprite.com/v3/product-research`
- `https://www.sellersprite.com/v3/competitor-lookup`
- `https://www.sellersprite.com/v2/export-log`

Current collector summaries already preserve:

- `execution_mode`
- `execution_warning`
- `attempted_url`
- `final_url`
- `page_title`
- `matched_task_name`
- `matched_status_value`
- `steps[]`

### Workbook stage

Current workbook contracts:

- product workbook
  - `runs/manual/15_product_exports/<run_id>/Product-*.xlsx`
- benchmark workbook
  - `runs/manual/20_benchmark_exports/<run_id>/Competitor-*.xlsx`

Current code already validates:

- file exists
- file size > 0
- suffix is workbook-compatible
- workbook is readable

### Parse stage

Current raw parse artifacts:

- `product_research_raw.json`
- `benchmark_competitor_raw.json`

These are the first machine-usable object-like outputs.

### Canonical build stage

Current product outputs:

- `10_产品样本原始结果.csv`
- `11_产品样本种子池.csv`
- `12_产品样本下推结果.csv`
- `13_step1_market_handoff.jsonl`
- `13a_step1_market_session_bundle.json`
- `13b_step1_market_probe_summary.json`

Current benchmark outputs:

- `40_竞品基准结果.csv`
- `41_候选产品种子池.csv`
- `42_竞品基准下推结果.csv`
- `benchmark_chain_output_index.csv`
- `benchmark_chain_output_index.md`

This is structured artifact proof, not final business approval.

## Standard Objects

### `ResearchExecutionInputProfile`

Purpose:

- freeze the exact query and seed context for one execution

Required fields:

- `execution_family`
- `run_name`
- `direction_id`
- `keyword`
- `site`
- `days`
- `sample_top_n`
- `context_source`
- optional `seed_source_step`
- optional `seed_keyword`
- optional `candidate_market_name`
- optional `market_path`

### `ResearchCollectorReceipt`

Purpose:

- capture live page execution truth up to workbook persistence

Current materialization:

- `latest_product_research_run.json`
- `latest_benchmark_export_run.json`

Required fields:

- `module`
- `status`
- `reason_code`
- `execution_mode`
- `attempted_url`
- `final_url`
- `matched_task_name`
- `workbook_download_path`
- `raw_artifact_path`
- `steps[]`
- auth replay metadata when applicable

### `ResearchWorkbookArtifact`

Purpose:

- preserve the workbook as the reviewable collector payload

Required fields:

- `workbook_path`
- `file_name`
- `size_bytes`
- `sheet_names`
- `source_task_name`

### `ResearchRawParseArtifact`

Purpose:

- normalize workbook contents into a machine-usable JSON artifact

Current materialization:

- `product_research_raw.json`
- `benchmark_competitor_raw.json`

Required fields:

- `module`
- `query_url`
- `workbook_path`
- `workbook_sheet_name`
- `workbook_headers`
- `context`
- `response_meta`
- `items`

### `ResearchCanonicalArtifactSet`

Purpose:

- carry the structured CSV/JSON outputs that downstream B or A can consume

Current materialization:

- product `10/11/12/13/13a/13b`
- benchmark `40/41/42` and output indexes

### `ResearchEvidencePack`

Purpose:

- group reviewable and diagnostic evidence for one execution

Current logical members:

- collector summary JSON
- build summary JSON
- workbook ref
- raw artifact ref
- screenshots
- traces when present
- auth incident refs when present
- product handoff/probe JSON when present

### `ResearchFailureRecord`

Purpose:

- classify one blocker without hiding the native `reason_code`

Current materialization:

- summary JSON plus step records
- auth incident JSON and screenshot when auth is the blocker

### `ResearchExecutionReceipt`

Purpose:

- act as the attachable top receipt for one execution pack

Current materialization is still split across:

- collector summary JSON
- build summary JSON
- workbook ref
- raw artifact ref

Attachability policy:

- `approved_execution_candidate`
  - collector PASS
  - parse PASS
  - build PASS
  - governance boundary preserved
- `shadow_candidate`
  - real evidence exists
  - latest run is still auth/export-log/path-hygiene sensitive

### `ResearchHandoffBrief`

Purpose:

- give A or another B-side surface one short deterministic ingest brief

## Governance Boundaries

### Workbook success is not final verdict

These are artifact successes only:

- workbook downloaded
- raw artifact parsed
- builder outputs written

They do not mean:

- final product approval
- final benchmark approval
- SellerSprite closure

### Auth and profile material stay local-only

Do not hand off raw contents of:

- `playwright/auth/*.json`
- `playwright/auth/login_replays/*.py`
- `playwright/auth/owner_recordings/**`
- `playwright/profiles/**`
- `logs/runtime_replay_profiles/**`

Only hand off:

- redacted refs
- auth surface family
- replay attempted / not attempted
- blocker summary
- auth screenshot ref when needed

### Evidence path drift must not become semantic drift

Current observed sample note:

- `playwright/screenshots/product_chain/` was not present under the observed old runtime root
- some product-stage screenshots were observed under `playwright/screenshots/benchmark_chain/`

Interpretation:

- this is path hygiene drift
- not semantic proof that product execution belongs to benchmark execution

### Traces are optional evidence

Current observed trace sample under the old runtime root:

- `playwright/traces/playwright-smoke.zip`

So trace presence cannot be assumed for every research execution pack.

## A/B Handoff Brief

### Standard brief template

```md
## SellerSprite Research Execution Brief

- execution_family:
- attachability:
- status:
- reason_code:
- run_name:
- direction_id:
- keyword:
- site:
- collector_summary_ref:
- build_summary_ref:
- workbook_ref:
- raw_artifact_ref:
- canonical_artifact_refs:
- key_evidence_refs:
- auth_surface_family:
- business_boundary_note:
```

### Product example

```md
## SellerSprite Research Execution Brief

- execution_family: STEP1_PRODUCT_RESEARCH
- attachability: approved_execution_candidate
- status: PASS
- reason_code: PASS
- run_name: US_ClawMachine_20260409
- direction_id: DIR_CLAW_MACHINE_001
- keyword: claw machine
- site: US
- collector_summary_ref: logs/formal_next_slice_20260410/step1_product/latest_product_research_run.json
- build_summary_ref: logs/formal_next_slice_20260410/step1_product_build/latest_product_build_run.json
- workbook_ref: runs/manual/15_product_exports/20260410_next_slice_formal/Product-US-Last-30-days-209236.xlsx
- raw_artifact_ref: outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/product_research_raw.json
- canonical_artifact_refs: 10/11/12/13/13a/13b under the same run folder
- key_evidence_refs: workbook, collector summary, build summary, handoff JSONL
- auth_surface_family:
- business_boundary_note: Artifact success only. Do not rewrite into final product verdict.
```

### Benchmark example

```md
## SellerSprite Research Execution Brief

- execution_family: STEP4_BENCHMARK_COMPETITOR
- attachability: approved_execution_candidate
- status: PASS
- reason_code: PASS
- run_name: US_ClawMachine_20260409
- direction_id: DIR_CLAW_MACHINE_001
- keyword: claw machine
- site: US
- collector_summary_ref: logs/formal_next_slice_20260410/step4_benchmark/latest_benchmark_export_run.json
- build_summary_ref: logs/formal_next_slice_20260410/step4_benchmark_build/latest_benchmark_build_run.json
- workbook_ref: runs/manual/20_benchmark_exports/20260410_next_slice_formal/Competitor-US-Last-30-days-209270.xlsx
- raw_artifact_ref: outputs/selection_runs/20260410_next_slice_formal/02_generated_outputs/benchmark_competitor_raw.json
- canonical_artifact_refs: 40/41/42 and benchmark output indexes under the same run folder
- key_evidence_refs: workbook, collector summary, build summary, benchmark output index
- auth_surface_family:
- business_boundary_note: Artifact success only. Do not rewrite into final competitor verdict.
```

## Intake Position

Current B-side truth after this objectization is:

- STEP1 Product Research can enter later wiring as a real execution-pack family
- STEP4 Benchmark / Competitor can enter later wiring as a real execution-pack family
- both may enter as:
  - `approved_execution_candidate` when collector/build are both PASS
  - `shadow_candidate` when fresh auth/export-log instability is still the latest truth

This keeps the chain objectized and evidence-ready without pretending that workbook download or build success equals final business closure.
