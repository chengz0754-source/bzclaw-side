# Candidate Pool Contract

## Scope

- This contract standardizes the intermediate candidate-sample pool and the final `60_候选样品池.csv` projection.
- The pool builder only performs deterministic:
  - sample-level dedupe
  - title-signature near-synonym grouping
  - source/provenance recording
  - status aggregation from upstream structured outputs
- The builder does not invent keywords, market judgments, final explanations, or Go/No-Go decisions.

## Current Upstream Truth On 2026-04-10

- The builder still supports the old direction-batch source mode.
- A new nightly-state source mode now consumes route-aware step states from:
  - `logs/.../latest_nightly_state.json`
- A new direct-artifact source mode now consumes explicit SellerSprite step artifacts for the current context:
  - `12_产品样本下推结果.csv`
  - `22_关键词证据词池下推结果.csv`
  - `32_市场调研下推结果.csv`
  - `42_竞品基准下推结果.csv`
  - with companion seed tables auto-resolved from the same output folders when present
- Verified `claw machine / US` nightly truths on `2026-04-09`:
  - STEP1 product entry can emit real `10/11/12`
  - STEP2 can emit real `20/21/22` but remain `HOLD`
  - STEP4 can now emit fresh real `40/41/42`
  - STEP3 is no longer a universal hard gate for every purpose
  - candidate pool can still emit real rows without fabricating full closure
- The builder is now purpose-aware:
  - `MARKET_DISCOVERY` still treats STEP3 as required
  - `PRODUCT_IDEA_VALIDATION` treats STEP3 as optional market mapping / enrichment
  - optional market mapping gaps must project as boundary statuses instead of collapsing the whole pool
- Verified `claw machine / US` direct-artifact truth on `2026-04-09`:
  - matched `12` rows exist
  - matched `22` rows exist and remain `HOLD`
  - the latest provided `32` file in repo is for another direction and must not be merged into `claw machine`
  - matched `42` rows exist
  - candidate pool must therefore emit a downgraded boundary such as `BLOCKED_BY_MARKET_SOURCE_EMPTY`, not a fake full-chain `PASS`

## Source Inputs

- Direction batch summary:
  - `logs/direction_batch/latest_run.json`
- Batch queue:
  - `outputs/selection_runs/<batch_id>/02_generated_outputs/batch_queue_status.csv`
- STEP4 runtime outputs from successful benchmark-trigger rows:
  - `41_候选产品种子池.csv`
  - `42_竞品基准下推结果.csv`
- STEP3 market metrics are read from the batch queue snapshot and the matched `32_市场调研下推结果.csv` rows.
- Nightly-state mode may also read:
  - `11_产品样本种子池.csv`
  - `12_产品样本下推结果.csv`
  - route-level step statuses from `latest_nightly_state.json`
- Direct-artifact mode may also read:
  - `11_产品样本种子池.csv`
  - `41_候选产品种子池.csv`
  - only when they are companion seed files for the provided `12` / `42` artifact folders

## Output Layers

### 1. Runtime intermediate pool

- File:
  - `outputs/selection_runs/<batch_id>/02_generated_outputs/03_候选市场与候选品初筛池.csv`
- Role:
  - intermediate candidate-sample pool
  - machine-generated provenance layer
  - not a final human judgment sheet

### 2. Final readable candidate pool

- Files:
  - `outputs/selection_runs/<batch_id>/02_generated_outputs/60_候选样品池.csv`
  - `outputs/selection_runs/<batch_id>/02_generated_outputs/60_候选样品池.md`
- Field order:
  - locked by `templates/selection_canonical_standards/99_字段数据标准总表.csv`

## 03 Role Change

- `templates/selection_csv_cn_reference/03_候选市场与候选品初筛池.csv` and `inputs/selection_run_current/03_候选市场与候选品初筛池.csv` now define an intermediate pool schema.
- `03` no longer requires:
  - final explanation
  - final human judgment
  - midstream Go/No-Go
- Manual-only fields must stay out of the `03` schema or remain blank.

## 60 Field Rules

- `方向词` records the contributing source direction.
- `核心关键词` and `长尾关键词` record contributing source keywords.
- `样品ID` is the stable sample primary key.
- `当前下推状态` is the fail-closed aggregate state of the upstream structured chain.
- Manual fields remain blank:
  - `合规`
  - `改良点`
  - `最终解释`
  - `利润核价`
  - `备注`

## Dedupe And Merge Rules

- Primary dedupe key:
  - `样品ASIN`
- Existing STEP4 dedupe evidence is preserved through:
  - `去重组ID`
- Near-synonym merge uses a deterministic title signature:
  - lowercase normalized title tokens
  - fixed stopword list
  - brand + market context
- No model-authored semantic rewrite is allowed.

## Fail-Closed Rules

- If no successful STEP4 benchmark-trigger row exists, `60` may be emitted as header-only, and the build must remain `HOLD`.
- If STEP2 is blocked, the pool may include only verified STEP3/STEP4-derived rows and must not claim full-chain readiness.
- If STEP4 is blocked but STEP1 product samples are real, the nightly-state mode may emit:
  - `PARTIAL_REAL_SAMPLE_ONLY`
- If STEP3 is `SOURCE_EMPTY` but real STEP1/STEP4 samples exist, the nightly-state mode may emit:
  - `BLOCKED_BY_MARKET_SOURCE_EMPTY`
- If the current purpose is `PRODUCT_IDEA_VALIDATION` and STEP3 broad market mapping is still pending, blocked, or source-empty, the pool may emit:
  - `MARKET_MAPPING_PENDING`
  - `PASS_WITH_MARKET_MAPPING_PENDING`
  - `PRODUCT_FEASIBLE__MARKET_ABSTRACTION_PENDING`
- Those statuses mean:
  - real product / competitor evidence exists
  - the market abstraction layer is still pending
  - SellerSprite is not yet a full business closure
- If direct-artifact mode receives a `32` file that has no rows matching the current `方向ID / 关键词 / 站点`, it must not merge other-direction market data.
  - The builder records the context miss and downgrades the pool as market-missing for the current context.
- Manual fields must never be auto-filled.
- Runtime outputs stay under ignored `outputs/` and `logs/`; they must not enter git.
