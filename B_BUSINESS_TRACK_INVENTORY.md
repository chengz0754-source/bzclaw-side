# B-side Business Track Inventory

## Scope

This note pulls the real Machine B business plane out of the sidecar infrastructure plane.

The goal is to keep two truths separate:

- B-side business tracks are the repo-visible SellerSprite / SIF / shortlist / candidate / approved-skill execution lanes that can produce business-facing artifacts.
- sidecar infrastructure is the repo-visible runtime support layer that keeps those tracks runnable, reviewable, and ingestable, but is not itself a business lane.

This note does not rewrite B as:

- A-side truth host
- formal publish host
- mature worker platform

## Current Cut

Current default B-side business plane is script-first and purpose-routed:

- default live lane: `scripts/`
- approved but non-default execution surfaces: `skills/`
- controlled ingest packaging layer: `scripts/run_nightly_selection_acceptance.py`

Current non-business sidecar infrastructure that should stay outside the business inventory:

- `scripts/bootstrap_dirs.py`
- `scripts/smoke_python.py`
- `scripts/smoke_playwright.py`
- `scripts/survey_system.py`
- `scripts/normalize_repo_business_files.py`
- `scripts/reset_selection_input_from_templates.py`
- `scripts/output_envelope_common.py`
- `scripts/archive_selection_run_io.py`
- `scripts/temp_*.py`
- `scripts/scripts.zip`

## Business Face Category Map

### 1. Business adapters

Concrete repo-visible business adapters:

- `scripts/sellersprite_route_router.py`
  - purpose-routed intake and path selection
- `scripts/run_selection_direction_batch.py`
  - batch queue and fail-closed downstream triggering
- `scripts/build_market_discovery_shortlist.py`
  - T01 shortlist projection from workbook or STEP3 gate layer
- `scripts/build_candidate_pool.py`
  - STEP7 candidate pool projection
- `scripts/build_sif_enrichment_daytime_pack.py`
  - Step 5 and Step 6 alignment onto candidate rows
- `scripts/sellersprite_nightly_orchestrator.py`
  - route-aware nightly state machine
- `scripts/run_nightly_selection_acceptance.py`
  - controlled dry-run packaging and ingest-facing archive assembly
- `scripts/map_market_report_to_candidate_pool.py`
  - legacy workbook-to-`03` adapter; repo-visible but not current default lane

### 2. Collectors

Concrete repo-visible collectors:

- `scripts/export_product_research.py`
- `scripts/export_keyword_research.py`
- `scripts/export_keyword_trend.py`
- `scripts/export_market_report.py`
- `scripts/export_benchmark_competitors.py`
- `scripts/collect_sif_detail_surface.py`
- `scripts/collect_sif_search_surface.py`

Collector wrapper note:

- `scripts/record_market_export.py` is only a thin wrapper to `export_market_report.py`; it is not a separate business track.

### 3. Observation / evidence producers

Concrete repo-visible observation and evidence producers:

- `scripts/run_sellersprite_keyword_export_flow.py`
- `scripts/record_sellersprite_keyword_export_flow.py`
- `scripts/parse_product_export_workbook.py`
- `scripts/parse_keyword_history_workbook.py`
- `scripts/parse_benchmark_export_workbook.py`
- `scripts/bootstrap_sellersprite_auth.py`
- `scripts/check_sellersprite_session.py`
- `scripts/sellersprite_auth_registry.py`
- `scripts/sellersprite_auth_replay.py`
- `scripts/register_owner_sellersprite_replays.py`
- `scripts/register_sellersprite_login_replay.py`
- `scripts/bootstrap_sif_auth.py`

These scripts matter because they create:

- workbook parse evidence
- auth replay evidence
- session truth
- blocked-surface proof
- replay metadata needed by the live collectors

They support business tracks, but they are not standalone business closure lanes.

### 4. Approved skill execution surfaces

Concrete approved skill surfaces currently imported into this repo:

- `skills/skill-market-route-m01-to-m02`
- `skills/skill-market-route-step1-to-step3`
- `skills/skill-market-root-orchestrator`
- `skills/skill-semantic-filter-local`

Important boundary:

- these skills are repo-visible and approved to execute
- they are not the current default SellerSprite/SIF script lane under `scripts/`
- they should be treated as bounded imported execution surfaces, not as proof that B has already become a full skill runtime platform

## Current Default Business Tracks

### BT-01. Purpose-routed intake adapter

- Business face: `business adapters`
- Primary entrypoints: `scripts/sellersprite_route_router.py`
- Inputs: `inputs/selection_run_current/01_选品任务路由与目的.csv`, `01A_市场发现参数.csv`, `01B_产品与竞品种子输入.csv`, `02A_SIF补强策略输入.csv`
- Outputs: `latest_route_decision.json`, `route_decisions.jsonl`
- Dependencies: current route tables, route rules in code, `benchmark_chain_common.py`
- Artifact: route decision record with purpose, sequence, step3 policy, sif policy
- Evidence: route decision logs under `logs/*/latest_route_decision.json`
- Auth requirement: `NONE_DIRECT`
- Current maturity: `ACTIVE_FORMAL_ROUTING__INPUT_BOUND`
- Current repo truth: current formal purposes are `MARKET_DISCOVERY`, `PRODUCT_IDEA_VALIDATION`, `COMPETITOR_REVERSE_MINING`, and `SUPPLY_CHAIN_BACKSOLVE`; the router is already the default path selector and does not invent a second semantic system

### BT-02. Direction batch orchestrator

- Business face: `business adapters`
- Primary entrypoints: `scripts/run_selection_direction_batch.py`
- Inputs: `00_选品运行目标与边界.csv`, `01_市场入口与筛选参数.csv`, `02_账号与合规预检查.csv`, latest `22/32/42` gate artifacts when present
- Outputs: `batch_queue_status.csv`, `batch_run_summary.json`, `batch_run_summary.md`
- Dependencies: current input tables, `templates/selection_canonical_standards/90_下推参数表.csv`, downstream STEP3 and STEP4 scripts, repo Python env
- Artifact: per-row queue state, per-stage status, per-row output artifact links
- Evidence: `logs/direction_batch/latest_run.json`, `direction_batch_runs.jsonl`, `direction_batch_failures.jsonl`
- Auth requirement: `INHERITED_SELLERSPRITE`
- Current maturity: `ACTIVE_FORMAL_ORCHESTRATION__UPSTREAM_SENSITIVE`
- Current repo truth: this is the current batch-level fail-closed adapter; it can keep running downstream probes while preserving blocked formal gate truth

### BT-03. STEP1 Product Research chain

- Business face: `collectors`
- Primary entrypoints: `scripts/export_product_research.py`, `scripts/build_product_seed_pool.py`
- Inputs: current route/context row, Product Research keyword, runtime direction context, template `90/99`
- Outputs: `10_产品样本原始结果.csv`, `11_产品样本种子池.csv`, `12_产品样本下推结果.csv`, `13_step1_market_handoff.jsonl`
- Dependencies: SellerSprite `v3/product-research`, product replay/auth context, workbook parse helpers, canonical templates
- Artifact: Product Research workbook plus `10/11/12` and product-to-market handoff JSONL
- Evidence: `runs/manual/15_product_exports/**`, product logs, screenshots/traces on incident
- Auth requirement: `SELLERSPRITE_PRODUCT_RESEARCH`
- Current maturity: `REAL_FORMAL_PATH__PASS_ARTIFACTS_PROVEN`
- Current repo truth: on `2026-04-10`, a fresh formal rerun for `claw machine / US` rebuilt real `10/11/12`; the chain now passes page-visible `市场分析URL` forward to STEP3 instead of using a fake market entry

### BT-04. STEP2 Keyword Evidence chain

- Business face: `collectors`
- Primary entrypoints: `scripts/export_keyword_research.py`, `scripts/export_keyword_trend.py`, `scripts/build_keyword_evidence_pool.py`
- Inputs: current context row, direction id, keyword miner query, repo-local storage state or persistent profile, template `90/99`
- Outputs: `20_关键词证据词池原始结果.csv`, `21_关键词证据词池清洗结果.csv`, `22_关键词证据词池下推结果.csv`, `keyword_chain_output_index.csv`, `keyword_chain_output_index.md`
- Dependencies: SellerSprite `v3/keyword-miner`, export-log flow, `run_sellersprite_keyword_export_flow.py`, canonical templates
- Artifact: `keyword_research_raw.json`, `keyword_trend_raw.json`, canonical `20/21/22`
- Evidence: `runs/manual/12_keyword_exports/**`, `logs/keyword_chain/**`, keyword export flow records
- Auth requirement: `SELLERSPRITE_KEYWORD_AUTH_REQUIRED`
- Current maturity: `CLOSED_AT_ARTIFACT_LAYER__GATE_HOLD__AUTH_SENSITIVE`
- Current repo truth: on `2026-04-09`, `claw machine / US` produced real `20/21/22`, but the gate remained `HOLD`; fresh recollection later regressed behind auth replay and should not be overstated as closed business continuity

### BT-05. STEP3 Market Research chain

- Business face: `collectors`
- Primary entrypoints: `scripts/export_market_report.py`, `scripts/build_market_workbook_index.py`
- Inputs: current `01` controls or explicit overrides, Product Research handoff `市场分析URL` for product-form routes, canonical template `90/99`
- Outputs: `market-report-*.xlsx`, `30_市场调研原始索引.csv`, `31_市场调研清洗结果.csv`, `32_市场调研下推结果.csv`, `market_workbook_index.csv`, `market_workbook_index.md`, `market_chain_output_index.csv`, `market_chain_output_index.md`
- Dependencies: SellerSprite market-research surface, workbook parsing, canonical templates, keep-set workbook policy
- Artifact: raw market workbook plus `30/31/32` gate package
- Evidence: `runs/manual/10_market/**`, `logs/market_exports/**`, STEP3 rerun summaries in `reports/`
- Auth requirement: `SELLERSPRITE_MARKET_RESEARCH`
- Current maturity: `PARTIAL__FORMAL_PATH_CORRECTED__LIVE_BLOCKERS_REMAIN`
- Current repo truth: the formal product-form path is corrected and repo-visible, but STEP3 still remains the first live SellerSprite blocker for several lanes and must stay partial rather than being declared closed

### BT-06. STEP4 Benchmark Competitor chain

- Business face: `collectors`
- Primary entrypoints: `scripts/export_benchmark_competitors.py`, `scripts/build_benchmark_seed_pool.py`
- Inputs: current route context, resolved seed from `STEP1_PRODUCT_GATE -> STEP3_MARKET_GATE -> manual override`, canonical template `90/99`
- Outputs: `benchmark_competitor_raw.json`, `40_竞品基准结果.csv`, `41_候选产品种子池.csv`, `42_竞品基准下推结果.csv`, `benchmark_chain_output_index.csv`, `benchmark_chain_output_index.md`
- Dependencies: SellerSprite `v3/competitor-lookup`, export-log polling, benchmark seed resolution, canonical templates
- Artifact: raw benchmark JSON, workbook-derived `40/41/42`, candidate seed pool
- Evidence: `runs/manual/20_benchmark_exports/**`, `logs/benchmark_chain/**`, export-log incident evidence
- Auth requirement: `SELLERSPRITE_BENCHMARK_AUTH_REQUIRED`
- Current maturity: `CLOSED_AT_CHAIN_LAYER__NIGHTLY_PARTIAL`
- Current repo truth: fresh formal reruns proved the STEP1-seeded page-download path and built real `40/41/42`, but nightly stability is still sensitive to export-log auth regression

### BT-07. T01 Market Discovery shortlist

- Business face: `business adapters`
- Primary entrypoints: `scripts/build_market_discovery_shortlist.py`
- Inputs: `01_选品任务路由与目的.csv`, `01A_市场发现参数.csv`, current batch selection input CSV, either real market workbook or STEP3 gate CSV
- Outputs: `T01_市场发现短名单.csv`, `T01_市场发现短名单.md`, `T01_市场发现短名单_summary.json`
- Dependencies: route decision, market workbook or STEP3 gate layer, selection input whitelist, category/purpose profile
- Artifact: shortlist projection with `YES / HOLD / NO`
- Evidence: `reports/CODEX_SELLERSPRITE_FOUR_FLOW_EXECUTION_SUMMARY_20260410.md`, `reports/CODEX_TOY_10_TERMS_BATCH_RUN_SUMMARY_20260411.md`, shortlist logs
- Auth requirement: `NONE_DIRECT__UPSTREAM_STEP3_INHERITED`
- Current maturity: `REAL_SHORTLIST_PROJECTION__STEP3_DEPENDENT`
- Current repo truth: real T01 runs exist for both the `2026-04-10` workbook-backed shortlist and the `2026-04-11` toy 10-term batch; both remain shortlist projection rather than full business closure

### BT-08. STEP7 Candidate Pool projection

- Business face: `business adapters`
- Primary entrypoints: `scripts/build_candidate_pool.py`
- Inputs: batch summary, batch queue, explicit `12/22/32/42` artifacts or nightly state, companion seed tables when present
- Outputs: `03_候选市场与候选品初筛池.csv`, `60_候选样品池.csv`, `60_候选样品池.md`, `candidate_pool_summary.json`
- Dependencies: STEP1/2/3/4 structured outputs, nightly state or direct-artifact mode, canonical standards
- Artifact: intermediate `03` pool and readable `60` projection
- Evidence: `reports/candidate_pool_contract.md`, candidate pool logs and summaries, nightly state references
- Auth requirement: `INHERITED`
- Current maturity: `REAL_OUTPUT__BOUNDARY_STATUS_ONLY`
- Current repo truth: STEP7 can emit real rows and downgraded boundary statuses such as `PRODUCT_FEASIBLE__MARKET_ABSTRACTION_PENDING` and `BLOCKED_BY_MARKET_SOURCE_EMPTY` without fabricating full closure

### BT-09. SIF surface collection

- Business face: `collectors`
- Primary entrypoints: `scripts/bootstrap_sif_auth.py`, `scripts/collect_sif_detail_surface.py`, `scripts/collect_sif_search_surface.py`
- Inputs: candidate pool row or explicit `asin + keyword + country`, repo-local SIF profile and optional storage state
- Outputs: `50_SIF流量结构补强.csv`, `51_SIF关键词价值补强.csv`, `52_SIF广告结构补强.csv`, `sif_detail_surface_probe.json`, `sif_search_surface_probe.json`
- Dependencies: SIF routes, `playwright/profiles/sif-main/`, `playwright/auth/sif.storage_state.json`, `scripts/sif_surface_common.py`
- Artifact: standards-aligned SIF detail/search outputs plus probe JSON
- Evidence: `logs/sif_surfaces/**`, blocked-route probe JSON, screenshots/traces if captured
- Auth requirement: `SIF_AUTH_REQUIRED`
- Current maturity: `PARTIAL_SURFACE_ONLY__AUTH_REQUIRED`
- Current repo truth: the repo already has a real shortlist-only SIF surface layer, but auth reusability is not yet verified and therefore current outputs must stay fail-closed

### BT-10. SIF enrichment and daytime pack

- Business face: `business adapters`
- Primary entrypoints: `scripts/build_sif_enrichment_daytime_pack.py`
- Inputs: `60_候选样品池.csv`, `candidate_pool_summary.json`, `50/51/52` outputs, probe JSON files, `batch_queue_status.csv`
- Outputs: `50_SIF流量结构补强.csv`, `51_SIF关键词价值补强.csv`, `52_SIF广告结构补强.csv`, `53_SIF补强下推结果.csv`, `61_待供应链核利清单.csv`, `61_待供应链核利清单.md`, `sif_enrichment_daytime_pack_summary.json`
- Dependencies: candidate-pool primary keys, SIF surface outputs, `templates/selection_canonical_standards/90_下推参数表.csv`
- Artifact: fail-closed `53` plus daytime shortlist handoff `61`
- Evidence: `reports/sif_enrichment_and_daytime_pack_contract.md`, `logs/sif_enrichment/latest_run.json`, SIF probe JSON
- Auth requirement: `INHERITED_SIF`
- Current maturity: `STRUCTURED_FAIL_CLOSED__UPSTREAM_BLOCKED`
- Current repo truth: this lane is structurally real and standards-aligned, but it must remain blocked while SIF auth and/or SIF data collection remain incomplete

### BT-11. Route-aware nightly state machine

- Business face: `business adapters`
- Primary entrypoints: `scripts/sellersprite_nightly_orchestrator.py`
- Inputs: purpose-routed context, current inputs, step collectors/builders, auth replay surfaces
- Outputs: `latest_nightly_state.json` and route-level step states
- Dependencies: purpose router, STEP1/2/3/4/7 scripts, auth replay support
- Artifact: resumable nightly state with step-level status and reason code continuity
- Evidence: nightly state logs, README status notes, route decision logs
- Auth requirement: `INHERITED_MULTI_SURFACE`
- Current maturity: `ACTIVE_FORMAL_ORCHESTRATION__UPSTREAM_SENSITIVE`
- Current repo truth: the repo-level nightly architecture is real and current, but it remains an orchestrated state layer and not a business closeout claim

### BT-12. Nightly acceptance dry-run envelope

- Business face: `observation / evidence producers`
- Primary entrypoints: `scripts/run_nightly_selection_acceptance.py`
- Inputs: current input snapshot, direction batch, candidate pool, SIF probes, enrichment builder
- Outputs: `outputs/selection_runs/<batch_id>/00_run_summary.md`, `00_run_manifest.json`, `02_generated_outputs/artifact_index.json`, `03_logs/evidence_pack.json`, `03_logs/shadow_run_receipt.json`, `03_logs/nightly_acceptance_summary.json`
- Dependencies: `scripts/output_envelope_common.py`, direction batch, candidate pool, SIF collectors, SIF enrichment
- Artifact: full archive-shaped dry-run package for ingest
- Evidence: copied current inputs, acceptance summary, evidence pack, shadow receipt
- Auth requirement: `INHERITED_MULTI_SURFACE`
- Current maturity: `REAL_EXECUTION_SURFACE__DRY_RUN_ONLY__NOT_BUSINESS_CLOSED`
- Current repo truth: this is the current controlled ingest-facing execution surface, but it stays explicitly dry-run and must not be promoted into business closure proof

## Non-default But Repo-visible Business Track

### BT-13. Legacy market workbook to `03` candidate-pool adapter

- Business face: `business adapters`
- Primary entrypoints: `scripts/map_market_report_to_candidate_pool.py`
- Inputs: market workbook, `inputs/selection_run_current/03_候选市场与候选品初筛池.csv`, current `00/01` context when available
- Outputs: updated `03_候选市场与候选品初筛池.csv`, `market_cleaned.csv`, `market_to_candidate_pool_mapping_report.json`, `market_to_candidate_pool_mapping_report.md`
- Dependencies: existing market workbook under `runs/manual/10_market/`, workbook parsing, repo-local CSV templates
- Artifact: mapped `03` pool plus mapping report
- Evidence: mapping report JSON/MD and selected workbook reference
- Auth requirement: `NONE_DIRECT__REUSES_EXISTING_MARKET_WORKBOOK`
- Current maturity: `LEGACY_LOCAL_ADAPTER__NONDEFAULT_BUT_EXECUTABLE`
- Current repo truth: this script is still repo-visible and executable, but the current default business path is the purpose-routed `STEP3 -> T01/STEP7` lane rather than direct workbook-to-`03` mapping

## Approved Skill Execution Surfaces

### SK-01. Skill market route `M01 -> M02`

- Business face: `approved skill execution surfaces`
- Primary entrypoints: `skills/skill-market-route-m01-to-m02/run_market_m01_to_m02.py`
- Inputs: dropzone `Market-research*.xlsx`
- Outputs: `M02_market_cleaned__*.xlsx`, matching CSV/JSONL, run summaries, manifests
- Dependencies: local files only, workbook parsing, skill-local archive/log structure
- Artifact: cleaned `M02` package
- Evidence: `logs/<run_id>/run.log`, warnings/errors JSON, processed/failed manifests
- Auth requirement: `NONE`
- Current maturity: `APPROVED_IMPORTED_SURFACE__BOUNDED_LOCAL_EXECUTION`
- Current repo truth: approved and repo-visible, but not the current default B-side business lane

### SK-02. Skill market route `M02 -> M03 -> M04 -> K01 -> K02`

- Business face: `approved skill execution surfaces`
- Primary entrypoints: `skills/skill-market-route-step1-to-step3/scripts/run_market_route_pipeline.py`
- Inputs: validated `M02`, `inbox/benchmark_raw/`, `inbox/keyword_raw/`
- Outputs: `M03_niche_shortlist`, `M04_benchmark_asin_scored`, `K01_keyword_pool`, `K02_keyword_shortlist`, summaries, manifests
- Dependencies: skill configs, local files, dropped raw evidence inboxes
- Artifact: bounded local market-route pipeline outputs through `K02`
- Evidence: step manifests, logs, queue status in skill workspace
- Auth requirement: `NONE_DIRECT__RAW_DROP_INBOX`
- Current maturity: `APPROVED_IMPORTED_SURFACE__BOUNDED_LOCAL_EXECUTION`
- Current repo truth: approved and executable, but it is an imported bounded pipeline that stops before SIF and final business closure

### SK-03. Skill market root orchestrator

- Business face: `approved skill execution surfaces`
- Primary entrypoints: `skills/skill-market-root-orchestrator/scripts/run_market_root_orchestrator.py`
- Inputs: dropzone `Market-research*.xlsx`, validated latest `M02`
- Outputs: unified orchestrator manifest and delegated downstream skill outputs
- Dependencies: `skill-market-route-m01-to-m02`, `skill-market-route-step1-to-step3`
- Artifact: orchestrated handoff from raw workbook root to validated `M02`
- Evidence: skill-local manifests and logs
- Auth requirement: `NONE`
- Current maturity: `APPROVED_IMPORTED_SURFACE__BOUNDED_LOCAL_EXECUTION`
- Current repo truth: approved and repo-visible, but it coordinates imported skills rather than the current default `scripts/` lane

### SK-04. Skill semantic filter local

- Business face: `approved skill execution surfaces`
- Primary entrypoints: `skills/skill-semantic-filter-local/scripts/run_semantic_filter.py`
- Inputs: latest `M03_niche_shortlist` and local Ollama runtime
- Outputs: `M03_semantic_filtered__*.xlsx`, matching CSV, semantic benchmark queue, semantic manifest, semantic run log
- Dependencies: local Ollama OpenAI-compatible endpoint, fixed model `qwen3:4b-instruct`
- Artifact: semantic denoise output and benchmark queue
- Evidence: semantic manifest and run log JSON
- Auth requirement: `OLLAMA_LOCAL_ONLY`
- Current maturity: `APPROVED_IMPORTED_SURFACE__LOCAL_MODEL_ONLY`
- Current repo truth: approved and bounded; this is the only imported skill surface that naturally maps toward a future `ModelInferenceReceipt`, but it is still not the current default B-side route

## Final Cut

Current B-side real business plane is now explicit:

- default script-first business tracks under `scripts/`
- one repo-visible non-default legacy adapter still present
- four approved imported skill execution surfaces under `skills/`

Current B-side non-business plane is also explicit:

- smoke
- bootstrap/hygiene
- repo survey
- output-envelope helper code
- archive helper code
- temp probes

That split is the baseline needed so later prompts stop treating the whole B repo as one undifferentiated sidecar shell.
