# B Market Intelligence Pack

## Scope

This pack objectizes the current B-side market-intelligence business family.

Included real business tracks:

- BT-04 STEP2 Keyword Evidence
- BT-05 STEP3 Market Report
- BT-08 STEP7 Candidate Pool
- BT-09 Step 5 SIF surface collection
- BT-10 Step 6 SIF enrichment and daytime pack

This pack does not mean:

- final market verdict
- final product verdict
- publish approval
- owner signoff
- generic adapter inventory

The goal is narrower:

- turn the existing business lanes into stable objects
- keep their evidence paths explicit
- preserve reviewable summaries for A ingest, GPT review, and owner look-sample use

## Canonical Position

Canonical repo root for prompts:

- `E:\bzclaw-side`

Observed local runtime samples still live outside the canonical repo:

- use `B_PATH_BASELINE_MAP.csv` for alias-to-local mapping
- treat the local runtime root as debug context only

Pack interpretation rules:

- repo-visible object identity first
- runtime absolute paths only as evidence refs
- auth/profile state never becomes handoff payload
- market observations stay as business intelligence, not final approval

## Included Families

### 1. Keyword Intelligence Pack

Primary scripts:

- `scripts/export_keyword_research.py`
- `scripts/export_keyword_trend.py`
- `scripts/build_keyword_evidence_pool.py`
- `scripts/run_sellersprite_keyword_export_flow.py`

Chain:

1. `MarketIntelligenceInputProfile`
2. keyword export control resolution
3. workbook export collector
4. live trend-table collector
5. raw JSON artifacts
6. canonical `20/21/22`
7. review summary
8. evidence refs

Input object:

- current context row
- route-aligned direction id / keyword / site
- keyword execution mode
- optional workbook download dir override

Middle artifacts:

- `latest_keyword_research_run.json`
- `latest_keyword_trend_run.json`
- `keyword_research_raw.json`
- `keyword_trend_raw.json`
- keyword export-flow logs

Output object:

- `20_关键词证据词池原始结果.csv`
- `21_关键词证据词池清洗结果.csv`
- `22_关键词证据词池下推结果.csv`
- `keyword_chain_output_index.csv`
- `keyword_chain_output_index.md`

Reviewable summary:

- `keyword_chain_output_index.md`

Evidence paths:

- `logs/keyword_chain/**`
- `logs/sellersprite_keyword_export_flow/**`
- `runs/manual/20_keyword_exports/**`
- `playwright/screenshots/sellersprite_auth_incidents/**` when auth is blocked

Observed sample on `2026-04-11`:

- `logs/keyword_chain/latest_keyword_research_run.json` records `PASS`
- workbook ref points to `runs/manual/20_keyword_exports/20260408_060505/KeywordHistory-mini-claw-machine-US-20260408-146021.xlsx`
- `logs/keyword_chain/latest_keyword_trend_run.json` records `PASS` with `surface_row_count=50`
- `logs/keyword_chain/latest_keyword_build_run.json` records `PASS`
- `outputs/selection_runs/20260409_step2_formal_rebuild/02_generated_outputs/` contains `20/21/22`
- observed row counts there are `21 / 19 / 19`
- gate summary is `PASS=0 FAIL=7 HOLD=12`

Important boundary:

- keyword workbook download success is only collector evidence
- keyword gate `HOLD` still means the intelligence pack is not a business verdict
- older B4 wording pointed at `runs/manual/12_keyword_exports/**`; current code truth and observed runtime truth are `runs/manual/20_keyword_exports/**`

### 2. Market Report Pack

Primary scripts:

- `scripts/export_market_report.py`
- `scripts/build_market_workbook_index.py`

Chain:

1. `MarketIntelligenceInputProfile`
2. market entry selection
3. workbook export attempt or source-empty receipt
4. keep-set workbook selection
5. canonical `30/31/32`
6. workbook index
7. review summary
8. evidence refs

Input object:

- current market controls from `01_市场入口与筛选参数.csv`
- optional STEP1 handoff URL or session bundle
- optional explicit workbook override

Middle artifacts:

- market export log receipt under `logs/market_exports/`
- selected raw workbook
- `market_workbook_index.csv`
- `market_workbook_index.md`

Output object:

- `30_市场调研原始索引.csv`
- `31_市场调研清洗结果.csv`
- `32_市场调研下推结果.csv`
- `market_cleaned.csv`
- `market_chain_output_index.csv`
- `market_chain_output_index.md`

Reviewable summary:

- `market_workbook_index.md`
- `market_chain_output_index.md`

Evidence paths:

- `logs/market_exports/**`
- `runs/manual/10_market/**`
- `playwright/screenshots/sellersprite_auth_incidents/**` when product-handoff or market auth is blocked

Observed samples on `2026-04-11`:

- `logs/market_exports/latest_run.json` records a blocked `claw machine / US` export with `failure_reason=SellerSprite market research returned no results`
- a later STEP3 canonical build exists under `outputs/selection_runs/20260411_t02_toy_parameterized_step3/02_generated_outputs/`
- selected keep-set workbook there is `runs/manual/10_market/20260411_t02_direct_asset_override/market-report-us-claw-machine-d30-new6m-sample100-head10-20260411_003456.xlsx`
- observed row counts there are `30=1`, `31=17`, `32=17`
- review summary records `PASS=0 FAIL=0 HOLD=17`

Important boundary:

- source-empty market export is still a real receipt and must stay visible
- market workbook existence is not equivalent to a final market judgment

### 3. Candidate Projection Pack

Primary script:

- `scripts/build_candidate_pool.py`

Chain:

1. `MarketIntelligenceInputProfile`
2. `UpstreamArtifactBinding`
3. structured upstream merge
4. intermediate pool `03`
5. readable candidate pool `60`
6. candidate summary
7. review summary

Input object:

- direct step artifacts `12 / 22 / 32 / 42` or nightly-state / batch sources
- purpose type and step3 policy
- optional companion seed tables

Middle artifacts:

- upstream binding refs
- `03_候选市场与候选品初筛池.csv`
- `candidate_pool_summary.json`

Output object:

- `03_候选市场与候选品初筛池.csv`
- `60_候选样品池.csv`
- `60_候选样品池.md`
- `candidate_pool_summary.json`

Reviewable summary:

- `60_候选样品池.md`

Evidence paths:

- `logs/candidate_pool/latest_run.json`
- `logs/candidate_pool/*.jsonl`
- explicit upstream step artifact refs from the same run folder

Observed sample on `2026-04-11`:

- `outputs/selection_runs/20260411_t02_toy_parameterized_step7/02_generated_outputs/` contains `03`, `60`, `60.md`, and `candidate_pool_summary.json`
- observed row counts there are `46 / 46`
- summary records `status=HOLD`
- summary `reason_code=PRODUCT_FEASIBLE__MARKET_ABSTRACTION_PENDING`
- summary `mode=direct_artifacts`
- step statuses in that run are `STEP1=PASS`, `STEP2=HOLD`, `STEP3=HOLD`, `STEP4=PASS`

Important boundary:

- candidate pool is a projection pack
- it is reviewable and ingestable as business intelligence
- it is not a final go/no-go sheet

### 4. SIF Reinforcement Pack

Primary scripts:

- `scripts/bootstrap_sif_auth.py`
- `scripts/collect_sif_detail_surface.py`
- `scripts/collect_sif_search_surface.py`
- `scripts/build_sif_enrichment_daytime_pack.py`

Chain:

1. `CandidateSampleRef`
2. optional local auth bootstrap
3. detail probe receipt
4. search probe receipt
5. aligned `50/51/52`
6. Step 5 gate `53`
7. Step 6 daytime shortlist `61`
8. review summary
9. evidence refs

Input object:

- candidate pool row or explicit `asin + keyword + country`
- repo-local SIF profile and optional storage state
- candidate pool summary and batch queue when building `53/61`

Middle artifacts:

- `latest_bootstrap_run.json`
- `latest_detail_run.json`
- `latest_search_run.json`
- `sif_detail_surface_probe.json`
- `sif_search_surface_probe.json`

Output object:

- `50_SIF流量结构补强.csv`
- `51_SIF关键词价值补强.csv`
- `52_SIF广告结构补强.csv`
- `53_SIF补强下推结果.csv`
- `61_待供应链核利清单.csv`
- `61_待供应链核利清单.md`
- `sif_enrichment_daytime_pack_summary.json`

Reviewable summary:

- `61_待供应链核利清单.md`
- `sif_enrichment_daytime_pack_summary.json`

Evidence paths:

- `logs/sif_surfaces/**`
- `logs/sif_enrichment/**`
- `playwright/profiles/sif-main/**` local-only
- `playwright/auth/sif.storage_state.json` local-only
- `playwright/traces/**` optional only

Observed samples on `2026-04-11`:

- `logs/sif_surfaces/latest_detail_run.json` records `status=HOLD`, `reason_code=SIF_AUTH_REQUIRED`, `route=reverse`, `execution_mode=persistent_profile`
- `logs/sif_surfaces/latest_search_run.json` records `status=HOLD`, `reason_code=SIF_AUTH_REQUIRED`, `route=snapshot`, `execution_mode=persistent_profile`
- those probe receipts point to `outputs/selection_runs/20260407_p10_acceptance/02_generated_outputs/50_SIF流量结构补强.csv`, `51_SIF关键词价值补强.csv`, `52_SIF广告结构补强.csv`
- `outputs/selection_runs/20260407_p09_daytime_pack/02_generated_outputs/` contains aligned `50/51/52`, `53`, `61`, and `sif_enrichment_daytime_pack_summary.json`
- observed row counts there are `50=20`, `51=20`, `52=20`, `53=20`, `61=0`
- `logs/sif_enrichment/latest_run.json` records `status=HOLD`
- the current blocked reason remains `BLOCKED_BY_SIF_OR_POOL_ALIGNMENT...SIF_AUTH_REQUIRED`

Important boundary:

- `bootstrap_sif_auth.py` is a local auth precondition, not a handoff object
- SIF outputs are real business-intelligence surfaces, but current auth truth keeps them in blocked or shadow posture

## Standard Objects

### `MarketIntelligenceInputProfile`

Run-scoped input contract shared across the pack.

Expected fields:

- `run_name`
- `direction_id`
- `keyword`
- `site`
- `purpose_type`
- `context_row_index`
- `execution_mode`
- `batch_id`

### `UpstreamArtifactBinding`

Structured refs to the step artifacts that a later pack consumes.

Typical refs:

- `step1_gate_path`
- `step2_gate_path`
- `step3_gate_path`
- `step4_gate_path`
- `candidate_pool_path`
- `candidate_pool_summary_path`

### `KeywordIntelligencePack`

The STEP2 family object composed of:

- workbook export receipt
- trend-table receipt
- raw keyword artifacts
- canonical `20/21/22`
- keyword review summary

### `MarketReportPack`

The STEP3 family object composed of:

- market export receipt
- keep-set workbook ref
- canonical `30/31/32`
- workbook and output indexes

### `CandidateProjectionPack`

The STEP7 family object composed of:

- upstream artifact binding
- `03` intermediate pool
- `60` readable pool
- candidate review summary

### `SIFReinforcementPack`

The Step 5 / Step 6 family object composed of:

- detail/search probe receipts
- aligned `50/51/52`
- step5 gate `53`
- daytime shortlist `61`
- SIF review summary

### `MarketIntelligenceEvidencePack`

Cross-family evidence envelope built from refs, not raw secret payloads.

Expected refs:

- summary JSON refs
- canonical CSV refs
- review markdown refs
- screenshot refs
- trace refs when present

### `MarketIntelligenceReviewSummary`

The reviewable owner/GPT surface.

Preferred files:

- `keyword_chain_output_index.md`
- `market_workbook_index.md`
- `market_chain_output_index.md`
- `60_候选样品池.md`
- `61_待供应链核利清单.md`

### `MarketIntelligencePack`

Run-scoped composite object that may contain one or more of:

- `KeywordIntelligencePack`
- `MarketReportPack`
- `CandidateProjectionPack`
- `SIFReinforcementPack`

Composition rule:

- presence is explicit
- absence is explicit
- blocked family receipts must still be carried

## Review Surfaces

Use these surfaces by audience:

- A ingest
  - canonical CSV refs
  - summary JSON refs
  - upstream binding refs
- GPT review
  - `keyword_chain_output_index.md`
  - `market_chain_output_index.md`
  - `60_候选样品池.md`
  - `61_待供应链核利清单.md`
- owner look-sample
  - readable `60` and `61` markdown
  - selected workbook index summary
  - key blocker reasons from receipts

## Governance Boundaries

### Runtime outputs stay local-first

Do not put runtime outputs into git.

Object refs may point to:

- `outputs/selection_runs/<batch_id>/02_generated_outputs/**`
- `runs/manual/**`
- `logs/**`

### Auth and profile materials stay local-only

Do not hand off raw contents of:

- `playwright/auth/*.json`
- `playwright/profiles/**`
- `playwright/auth/login_replays/**`
- `logs/runtime_replay_profiles/**`

Only hand off:

- redacted auth refs
- auth surface family
- replay attempted / not attempted
- blocker summary

### Reviewable summary is not verdict

These summary files are review surfaces:

- `keyword_chain_output_index.md`
- `market_chain_output_index.md`
- `60_候选样品池.md`
- `61_待供应链核利清单.md`

They are not:

- publish approval
- final owner decision
- final business closure

### Legacy summary JSON parsing can be noisy

Observed local runtime truth includes some legacy summary JSON files whose field names are not reliably parseable because of older encoding drift.

Interpretation rule:

- trust object class plus path plus canonical CSV/MD artifacts first
- treat malformed legacy JSON field names as evidence-format debt
- do not let that drift redefine the business object model

## Handoff Brief Template

```md
## B Market Intelligence Brief

- intelligence_family:
- track_scope:
- status:
- reason_code:
- input_profile_ref:
- upstream_binding_ref:
- primary_output_refs:
- review_summary_refs:
- evidence_refs:
- auth_boundary_note:
- business_boundary_note:
```

## Intake Position On 2026-04-11

- Keyword intelligence is a real business pack with artifact-proven `20/21/22`, but the gate layer can remain `HOLD`.
- Market report is a real business pack whether it ends in workbook success or source-empty blocked receipt.
- Candidate pool is a real business projection pack and should be ingested as projection, not verdict.
- SIF reinforcement is a real business pack family, but the latest visible truth is still auth-sensitive and blocked.
- The composite `MarketIntelligencePack` is now a stable B-side business object surface rather than a loose script set.
