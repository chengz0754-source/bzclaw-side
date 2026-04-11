# Amazon Selection Automation Sidecar

Independent sidecar workspace for Machine B verification, environment bootstrap,
Playwright automation, local-model calls, logs, and run artifacts.

This workspace does not modify or merge into the BZCLAW mainline. It is a
standalone baseline for the first Machine B verification round only.

## Repo boundary

This repository is intentionally narrow. The repo root is:

- `E:\选品文件夹\amazon-selection-automation`

What belongs in git:

- sidecar-owned docs and reports
- sidecar-owned configs and scripts
- imported legacy skill code/config/docs under `skills/`

What does not belong in git:

- anything under `E:\选品` outside this repo root
- `.venv/`
- runtime logs, outputs, runs, archive, inbox
- Playwright auth, persistent profiles, screenshots, traces, storage state
- `.env` and any real secrets, cookies, or tokens

Legacy assets from `E:\选品\skill-*` are imported into this repo as code-only
copies. The original directories remain external reference sources and are not
the repo boundary.

## Scope

- Site: `US`
- Primary goal: `profit_first`
- Default route mode: `purpose_router (MARKET_DISCOVERY / PRODUCT_IDEA_VALIDATION / COMPETITOR_REVERSE_MINING / SUPPLY_CHAIN_BACKSOLVE)`
- Price band: `0-100 USD`
- Budget cap: none in this phase
- MOQ cap: none in this phase
- Fulfillment boundary: `FBA only`
- Dangerous goods: `NO`
- Approval categories: `approval_category_allowed = no`
- FBM: not a formal path in this phase

## Machine split

- Machine B: model runtime, Playwright automation, SellerSprite/SIF automation,
  logs, screenshots, traces, and run artifacts.
- Machine A: forms, result review, manual confirmation, and final business
  judgment.

## Directory map

- `configs/`: fixed baseline configs
- `inputs/`: manual operator inputs and handoff files from Machine A
- `outputs/`: generated business outputs
- `logs/`: run logs
- `reports/`: verification and baseline reports
- `playwright/auth/`: storage state files, never commit sensitive auth
- `playwright/profiles/`: dedicated automation browser user data dirs
- `playwright/screenshots/`: smoke and debugging screenshots
- `playwright/traces/`: Playwright trace zips
- `scripts/`: survey, bootstrap, and smoke utilities
- `skills/`: imported legacy skill code/config/docs only
- `models/`: model adapter placement and usage notes
- `runs/`: timestamped execution folders

## Canonical Standards

- Canonical standards live in `templates/selection_canonical_standards/`.
- This directory is the only repo-internal source of truth for:
  - `00_高胜率精铺选品_6步自动化下推SOP_v1.md`
  - `01_全量CSV字段标准说明_v1.md`
  - `90_下推参数表.csv`
  - `99_字段数据标准总表.csv`
- Prompts and scripts must not read these standards from `reports/`, `inputs/`,
  or external download folders when the repo copy exists.
- `90_下推参数表.csv` and `99_字段数据标准总表.csv` are the machine-readable
  control surfaces for pushdown rules and field definitions.

## Selection CSV and Market Mapping Flow

- Canonical standards live in `templates/selection_canonical_standards/`.
- CSV templates live in `templates/selection_csv_cn_reference/`.
- Current run inputs live in `inputs/selection_run_current/`.
- The current repo-visible formal input contract is:
  - `inputs/selection_run_current/00_选品运行目标与边界.csv`
  - `inputs/selection_run_current/01_选品任务路由与目的.csv`
  - `inputs/selection_run_current/01A_市场发现参数.csv`
  - `inputs/selection_run_current/01B_产品与竞品种子输入.csv`
  - `inputs/selection_run_current/02_账号与合规预检查.csv`
  - `inputs/selection_run_current/02A_SIF补强策略输入.csv`
  - `inputs/selection_run_current/03_候选市场与候选品初筛池.csv`
- `inputs/selection_run_current/01_市场入口与筛选参数.csv` remains the runtime SellerSprite page-collector control sheet for sample size / days / top-N knobs while the new purpose tables define business intent and path switching.
- `inputs/selection_run_current/02_账号与合规预检查.csv` remains the manual compliance precheck sheet, and `04_供应链询价与利润核算.csv` remains a post-cost sheet instead of a preflight input.
- `templates/selection_csv_cn_reference/00 / 01 / 01A / 01B / 02 / 02A` are operator-facing templates
  for the purpose-routed program layer.
- `templates/selection_csv_cn_reference/03~04` are repo-local intermediate/post-cost
  worksheets. They are operationally useful, but they are not external canonical
  field masters.
- Raw SellerSprite market workbooks live in `runs/manual/10_market/`.
- Keep-set rule for raw workbooks: prefer the newest canonical `market-report-*.xlsx`; fall back to the newest non-diagnostic `.xlsx`.
- Archive/diagnostic copies such as `diag-*.xlsx` or `archive-*.xlsx` may be retained for evidence, but they must not drive automatic workbook selection.
- `03_候选市场与候选品初筛池.csv` is now the intermediate candidate-sample pool working copy and no longer requires midstream final judgment fields.
- `scripts/build_candidate_pool.py` merges structured STEP3 / STEP4 outputs into runtime `03_候选市场与候选品初筛池.csv` and `60_候选样品池.csv` artifacts under `outputs/selection_runs/<timestamp>/02_generated_outputs/`.
- `scripts/map_market_report_to_candidate_pool.py` remains a legacy market-only helper and is no longer the authoritative path for the current `03` role.
- Mapping artifacts land in `outputs/selection_runs/<timestamp>/02_generated_outputs/`.
- A folder that only contains `02_generated_outputs/` is a partial artifact package, not a full run archive.
- A full run archive under `outputs/selection_runs/<timestamp>/` must include `00_run_summary.md`, `01_consumed_inputs/`, `02_generated_outputs/`, and `03_logs/`.
- `scripts/normalize_repo_business_files.py` keeps business CSV/Excel files out of the repo root.

## Playwright profile policy

This project uses four separate layers:

1. Smoke-only browser profile
   Path: `playwright/profiles/chromium-user-data`
   This directory is reserved for smoke verification only. Do not point
   Playwright to the user's default Chrome profile.

2. SellerSprite automation profile
   Path: `playwright/profiles/sellersprite-main`
   This is the dedicated profile for SellerSprite auth refresh and workbook
   export flows.

3. Reusable logged-in state
   Path: `playwright/auth/sellersprite.storage_state.json`
   This file should only be created after a deliberate login bootstrap flow.
   Treat it as sensitive. Do not commit it to git.

4. Smoke storage state
   Path: `playwright/auth/storage_state.smoke.json`
   This is an unauthenticated baseline state for smoke verification, not a
   logged-in SellerSprite session.

## SellerSprite Auth Governance

- Auth incidents are now recorded under:
  - `logs/sellersprite_auth_incidents/latest_auth_incident.json`
  - `logs/sellersprite_auth_incidents/auth_incidents.jsonl`
  - `logs/sellersprite_auth_incidents/incidents/*.json`
- Every SellerSprite auth hit also saves reproducible evidence:
  - screenshots: `playwright/screenshots/sellersprite_auth_incidents/`
  - page snapshots: `logs/sellersprite_auth_incidents/page_snapshots/`
- Login replay coverage is tracked in:
  - `playwright/auth/login_replay_registry.json`
- Replay rules must stay fail-closed:
  - if a matching replay snippet is missing, the chain only records the incident and stops with an explicit auth reason code
  - owner should complete one fake-login recording for that surface family
  - Codex then registers the reusable replay snippet with `scripts/register_sellersprite_login_replay.py`
- The current SellerSprite modules wired into this mechanism are:
  - `scripts/export_keyword_research.py`
  - `scripts/export_keyword_trend.py`
  - `scripts/export_market_report.py`
  - `scripts/export_benchmark_competitors.py`
  - `scripts/export_product_research.py`
  - `scripts/sellersprite_nightly_orchestrator.py`

## Python-first baseline

Current bootstrap uses Python Playwright because Node.js and npm were not
available during survey. `package.json` is present to reserve the future Node
entry point, but the verified smoke path in this round is Python.

## Reuse candidates detected during survey

- Legacy selection assets root: `E:\选品`
- SellerSprite pipeline scripts and outputs under:
  - `E:\选品\skill-market-route-m01-to-m02`
  - `E:\选品\skill-market-route-step1-to-step3`
  - `E:\选品\skill-market-root-orchestrator`
  - `E:\选品\skill-semantic-filter-local`

These are treated as external reusable assets, not as this sidecar's owned
workspace.

## STEP2 Keyword Chain

- SellerSprite STEP2 keyword-chain scripts are:
  - `scripts/export_keyword_research.py`
  - `scripts/export_keyword_trend.py`
  - `scripts/build_keyword_evidence_pool.py`
- The STEP2 keyword-chain contract lives in:
  - `reports/sellersprite_keyword_chain_contract.md`
- Current repo truth on `2026-04-09`:
  - `export_keyword_research.py` can complete the v3 keyword-miner -> `我的导出` -> `KeywordHistory-*` workbook route when launched with the repo-local `storage_state` mode
  - the dedicated persistent profile currently opens `v3/keyword-miner` as `未登录 / 游客`, so that profile alone still leaves the keyword export button disabled
  - `export_keyword_trend.py` can still read the live v3 visible result table directly from the page surface
  - verified `claw machine / US` run produced `20/21/22`; current gate summary is `PASS=0 / FAIL=7 / HOLD=12`

Additional current STEP2 truth on `2026-04-09`:

- the formal STEP2 main path is now:
  `keyword_research(storage_state workbook export) + keyword_trend(v3 visible table) + build_keyword_evidence_pool`
- a later same-day re-run at `2026-04-09 04:26 +08:00` showed auth regression:
  `storage_state` redirected keyword research to login, and the persistent profile also redirected or guest-gated the keyword surfaces
- Git current must therefore preserve both truths together:
  STEP2 already has a real canonical `20/21/22` package for `claw machine`, while the current gate remains `HOLD` and fresh raw recollection currently depends on auth refresh

## STEP4 Benchmark Chain

- SellerSprite STEP4 benchmark-chain scripts are:
  - `scripts/export_benchmark_competitors.py`
  - `scripts/build_benchmark_seed_pool.py`
- The STEP4 benchmark-chain contract lives in:
  - `reports/sellersprite_benchmark_chain_contract.md`
- Current repo truth on `2026-04-10`:
  - the live benchmark page is `https://www.sellersprite.com/v3/competitor-lookup`
  - STEP4 resolves formal upstream seeds in this order: `STEP1_PRODUCT_GATE -> STEP3_MARKET_GATE -> manual override`
  - Product/benchmark replay now uses a runtime-seeded persistent context instead of reopening a guest-only replay profile dir
  - a fresh formal rerun for `claw machine / US` consumed fresh STEP1 seeds and completed the page export-log download path
  - fresh canonical artifacts now exist:
    - `40_竞品基准结果.csv`
    - `41_候选产品种子池.csv`
    - `42_竞品基准下推结果.csv`
  - the fresh STEP4 rerun stayed on the formal path and did not use manual override

## STEP1 Product Chain

- SellerSprite STEP1 product-chain scripts are:
  - `scripts/export_product_research.py`
  - `scripts/build_product_seed_pool.py`
- Current repo truth on `2026-04-10`:
  - `export_product_research.py` targets the real `https://www.sellersprite.com/v3/product-research` page instead of reusing the competitor table as a pseudo product entry
  - Product Research replay is now usable at collector runtime: the replayed context can reopen `v3/product-research`, query, select rows, hand off to `我的导出`, and download a real workbook
  - the fresh formal rerun for `claw machine / US` produced a real Product Research workbook and rebuilt fresh canonical artifacts:
    - `10_产品样本原始结果.csv`
    - `11_产品样本种子池.csv`
    - `12_产品样本下推结果.csv`
  - Product Research raw output now merges page-visible market-entry values such as `市场分析URL` into the workbook-derived rows so STEP3 can consume a formal product-market handoff

## Current SellerSprite Judgment

- Repo-level current judgment on `2026-04-09`:
  - `SELLERSPRITE_NIGHTLY_READY`
- This label means the route router, nightly state machine, downgrade statuses, and page-first collectors are now the current Git architecture.
- This label also means the project is now purpose-routed instead of forcing every input through a single universal market-first path.
- It does not mean every direction is already a full business closure.
- Current `claw machine / US` closure truth remains:
  - `SELLERSPRITE_NOT_CLOSED`

## Current SellerSprite Architecture

- Product entry:
  - `scripts/export_product_research.py`
  - `scripts/build_product_seed_pool.py`
  - real page target is `https://www.sellersprite.com/v3/product-research`
- Purpose router:
  - `scripts/sellersprite_route_router.py`
  - current formal purposes are `MARKET_DISCOVERY`, `PRODUCT_IDEA_VALIDATION`, `COMPETITOR_REVERSE_MINING`, and `SUPPLY_CHAIN_BACKSOLVE`
  - `claw machine / US` is now a formal `PRODUCT_IDEA_VALIDATION` case, not a universal market-discovery keyword
- Keyword evidence:
  - `scripts/export_keyword_research.py`
  - `scripts/export_keyword_trend.py`
  - `scripts/build_keyword_evidence_pool.py`
  - formal main path is `keyword_research(storage_state workbook export) + keyword_trend(v3 visible table) + build_keyword_evidence_pool`
- Market research:
  - `scripts/export_market_report.py`
  - `PRODUCT_FORM` words now enter STEP3 through STEP1 sample `市场分析URL`, not through a naked keyword search
- Benchmark / competitor:
  - `scripts/export_benchmark_competitors.py`
  - `scripts/build_benchmark_seed_pool.py`
  - formal seed order is `STEP1_PRODUCT_GATE -> STEP3_MARKET_GATE -> manual override`

## Current SellerSprite Status

- STEP1 Product entry: `PASS`
  - the real Product Research page now has a fresh formal workbook export for `claw machine / US`
  - fresh canonical artifacts exist for `10/11/12`
- STEP2 Keyword evidence: `CLOSED_AT_ARTIFACT_LAYER`
  - canonical `20/21/22` exist for `claw machine / US`
  - current gate remains `PASS=0 / FAIL=7 / HOLD=12`, so business status is still `HOLD`
  - fresh raw recollection is auth-sensitive and currently regressed
- STEP3 Market research: `PARTIAL`
  - for `PRODUCT_IDEA_VALIDATION`, STEP3 is now `OPTIONAL_ENRICHMENT`, not a universal hard gate
  - product-form routing is now corrected in code and verified against STEP1 sample `Market Analysis` entry
  - `SOURCE_EMPTY` no longer kills the nightly chain
  - the latest fresh rerun no longer failed on generic auth; the current reproducible blocker is `Page.goto: net::ERR_TOO_MANY_REDIRECTS` on the fresh STEP1 `市场分析URL`
  - no fresh `30/31/32` exists yet
- STEP4 Benchmark chain: `PASS`
  - the fresh formal rerun consumed fresh STEP1 seeds and completed the page-download route
  - fresh canonical artifacts exist for `40/41/42`

## Nightly Route

- New nightly routing / orchestration scripts:
  - `scripts/sellersprite_route_router.py`
  - `scripts/export_product_research.py`
  - `scripts/build_product_seed_pool.py`
  - `scripts/sellersprite_nightly_orchestrator.py`
- Current repo truth on `2026-04-10`:
  - `claw machine / US` is now routed as `PRODUCT_IDEA_VALIDATION`
  - the nightly sequence for that purpose is `STEP1_PRODUCT -> STEP4_BENCHMARK -> STEP2_KEYWORD -> STEP3_MARKET -> STEP7_CANDIDATE_POOL`
  - for `PRODUCT_IDEA_VALIDATION`, STEP3 is optional broad-market mapping and no longer a universal hard gate
  - `scripts/export_market_report.py` now resolves the first matching STEP1 product sample and opens its captured `市场分析URL` instead of treating the bare keyword as a mandatory market-discovery entry
  - the fresh `2026-04-10` rerun now proves:
    - STEP1 fresh `10/11/12` can be rebuilt from a real Product Research workbook
    - STEP4 fresh `40/41/42` can be rebuilt from fresh STEP1 formal seeds without manual override
    - STEP3 no longer fails on missing product-market binding; the current blocker is the reproducible market-entry redirect loop on the fresh STEP1 `市场分析URL`
    - STEP7 can rebuild from fresh STEP1 + STEP4 artifacts only, but it still remains `HOLD` because STEP2 business gate is `HOLD` and STEP3 has no fresh market workbook
  - the market-source-empty downgrade path is also wired: a same-day real `STEP3=SOURCE_EMPTY` state can now build `60_候选样品池.csv` with `当前下推状态=BLOCKED_BY_MARKET_SOURCE_EMPTY`

## Candidate Pool

- Candidate-pool builder script:
  - `scripts/build_candidate_pool.py`
- Candidate-pool contract:
  - `reports/candidate_pool_contract.md`
- Current repo truth on `2026-04-07`:
  - runtime `03_候选市场与候选品初筛池.csv` is an intermediate candidate-sample pool, not a manual judgment table
  - `60_候选样品池.csv` is the readable merged candidate pool projection
  - the nightly-state mode can now emit degraded but real rows from STEP1 product samples when STEP4 is blocked, and it preserves boundary statuses such as `PARTIAL_REAL_SAMPLE_ONLY` and `BLOCKED_BY_MARKET_SOURCE_EMPTY`

## SIF Surfaces

- Bootstrap script:
  - `scripts/bootstrap_sif_auth.py`
- Minimal surface collectors:
  - `scripts/collect_sif_detail_surface.py`
  - `scripts/collect_sif_search_surface.py`
- Contract:
  - `reports/sif_playwright_surface_contract.md`
- Current repo truth on `2026-04-07`:
  - isolated repo-local SIF profile path is now standardized at `playwright/profiles/sif-main/`
  - reusable SIF auth is not yet verified, so the current route probes must fail closed instead of claiming live surface success
  - detail/search probes already emit standards-aligned blocked CSV/JSON outputs that can be consumed by later Step 5 work without fabricating business metrics

## SIF Enrichment And Daytime Pack

- Builder script:
  - `scripts/build_sif_enrichment_daytime_pack.py`
- Formal shortlist-entry contract:
  - `reports/sif_shortlist_reinforcement_contract.md`
- Contract:
  - `reports/sif_enrichment_and_daytime_pack_contract.md`
- Current repo truth on `2026-04-07`:
  - SIF is a shortlist / candidate-row reinforcement layer, not a SellerSprite pre-gate
  - P09 aligns structured SIF outputs onto the runtime `60_候选样品池.csv` primary keys
  - when SIF is still auth-blocked or only partially collected, `50/51/52/53` stay standards-aligned but fail closed
  - `61_待供应链核利清单.csv` is only allowed to contain rows whose previous 5 stages are all `PASS`

## Nightly Acceptance

- Acceptance runner:
  - `scripts/run_nightly_selection_acceptance.py`
- Acceptance docs:
  - `reports/nightly_run_acceptance_report.md`
  - `reports/nightly_run_operator_runbook.md`
  - `reports/nightly_run_failure_recovery_guide.md`
- Current repo truth on `2026-04-07`:
  - the nightly runner assembles a full archive-shaped dry-run package under `outputs/selection_runs/<batch_id>/`
  - this path is non-destructive and copies current working inputs into `01_consumed_inputs/` instead of clearing them
  - the validated batch `20260407_p10_acceptance` ended in `HOLD`, not `PASS`, because STEP2 and SIF are still blocked upstream

## STEP3 Gate Update

- Current repo truth on `2026-04-11`:
  - T02 STEP3 collector is no longer auth-blocked for `claw machine / US`
  - the latest Product Research -> `Market Analysis` handoff produced a real workbook and fresh `30/31/32`
  - the current STEP3 blocker has moved from collector continuity to the gate-layer result of that workbook
  - current STEP3 gate summary is `PASS=0 / FAIL=16 / HOLD=1`
  - current STEP7 projection therefore remains `HOLD / PRODUCT_FEASIBLE__MARKET_ABSTRACTION_PENDING`
  - current business truth remains `SELLERSPRITE_NOT_CLOSED`

## STEP3 Category Parameterization

- Current repo truth on `2026-04-11`:
  - STEP3 gate rules can now read a category/purpose profile from `inputs/selection_run_current/01_选品任务路由与目的.csv`
  - the current toy profile source is `templates/category_gate_profiles/01__CATEGORY_GATE_PROFILES__TOY_V1__20260411.csv`
  - the current `claw machine / US / PRODUCT_IDEA_VALIDATION` case binds to `TOY_NOVELTY_ARCADE__IDEA_VALIDATION__V1`
  - rerunning STEP3 on the same real workbook changed the gate summary from `PASS=0 / FAIL=16 / HOLD=1` to `PASS=0 / FAIL=0 / HOLD=17`
  - STEP3 is no longer blocked by hard-fail market rules for this toy profile, but it still has no PASS rows
  - STEP7 therefore remains `HOLD / PRODUCT_FEASIBLE__MARKET_ABSTRACTION_PENDING`
  - current business truth remains `SELLERSPRITE_NOT_CLOSED`

## Toy 10 Terms Batch

- Current repo truth on `2026-04-12`:
  - the active MARKET_DISCOVERY batch input is the 10-term toy batch in `inputs/selection_run_current/01__SELECTION_INPUT__TOY_10_TERMS_BATCH__20260411.csv`, not `claw machine`
  - the active T01 route binds `TOY / TOY_GENERAL / MARKET_DISCOVERY` onto `TOY_GENERAL__MARKET_DISCOVERY__V1`
  - the active toy general profile source for this batch is `templates/category_gate_profiles/02__CATEGORY_GATE_PROFILES__TOY_V1__20260411.csv`
  - the latest fresh T01 STEP3 rebuild from the provided pack workbook produced a real gate layer with `PASS=33 / FAIL=0 / HOLD=167`
  - the 10 exact batch terms were then projected from that gate layer into a shortlist result of `YES=2 / HOLD=8 / NO=0`
  - the current recommended next terms are `Squeeze Toys` and `Multi-Item Party Favor Packs`
  - current business truth still remains `SELLERSPRITE_NOT_CLOSED`

## Shortlist Downstream Validation

- Historical repo truth from the downstream-validation slice on `2026-04-11`:
  - that slice used `inputs/selection_run_current/01__SHORTLIST_DOWNSTREAM_VALIDATION_INPUT__TOY_2_TERMS__20260411.csv`
  - the only terms in that historical slice were `Squeeze Toys` and `Multi-Item Party Favor Packs`
  - both terms were bound as `MARKET_DISCOVERY` rows with `step3_policy=REQUIRED` and consumed the existing shortlist-confirmed STEP3 PASS slices
  - the downstream structural truth from that slice remains:
    - STEP1 `Product Research` exporter is `BLOCKED / SELLERSPRITE_AUTH_REQUIRED`
    - STEP4 `Benchmark / Competitor` exporter is `BLOCKED / SELLERSPRITE_AUTH_REQUIRED` on the export-log surface even when seeded from the STEP3 PASS market row
    - STEP2 keyword-trend page collection is `PASS`, keyword-research workbook export is `BLOCKED`, and canonical `20/21/22` can still be built from trend rows only
    - STEP7 candidate-pool projection is `HOLD / NO_REAL_CANDIDATE_ROWS` because neither STEP1 nor STEP4 formed a real sample source
  - `Squeeze Toys` remains the stronger historical downstream candidate because its STEP2 gate layer is `HOLD=20 / FAIL=0`, while `Multi-Item Party Favor Packs` is `HOLD=17 / FAIL=3`
  - this section is historical context; the active input for the current slice is the 10-term toy batch above
