# SIF Enrichment And Daytime Pack Contract

## Scope

- This contract covers Step 5 and Step 6 integration on top of:
  - runtime `60_候选样品池.csv`
  - structured SIF detail/search outputs
- The integration layer is deterministic and only performs:
  - primary-key alignment by `样品ID` / `样品ASIN`
  - standards-locked `50/51/52/53/61` emission
  - rule evaluation from `90_下推参数表.csv`
  - fail-closed blocking when SIF or pool alignment is incomplete
- The integration layer does not write:
  - `合规`
  - `改良点`
  - `最终解释`
  - `利润核价`
  - `最终GoNoGo`

## Repo Inputs

- Candidate pool:
  - `outputs/selection_runs/<batch_id>/02_generated_outputs/60_候选样品池.csv`
- Candidate pool summary:
  - `outputs/selection_runs/<batch_id>/02_generated_outputs/candidate_pool_summary.json`
- SIF detail surface:
  - `50_SIF流量结构补强.csv`
  - `sif_detail_surface_probe.json`
- SIF search surface:
  - `51_SIF关键词价值补强.csv`
  - `52_SIF广告结构补强.csv`
  - `sif_search_surface_probe.json`
- Direction queue:
  - `outputs/selection_runs/<batch_id>/02_generated_outputs/batch_queue_status.csv`

## Output Layers

- Step 5 aligned outputs:
  - `50_SIF流量结构补强.csv`
  - `51_SIF关键词价值补强.csv`
  - `52_SIF广告结构补强.csv`
  - `53_SIF补强下推结果.csv`
- Step 6 daytime package:
  - `61_待供应链核利清单.csv`
  - `61_待供应链核利清单.md`

## Alignment Rules

- Primary alignment keys:
  - `样品ID`
  - fallback `样品ASIN`
- If a candidate row has no matched SIF row:
  - `50/51/52` still emit a standards-aligned row
  - metrics stay blank
  - status fields stay `HOLD`
  - `53` records a fail-closed reason with prefix `BLOCKED_BY_SIF_OR_POOL_ALIGNMENT`
- If a matched SIF probe row exists but the probe itself is blocked:
  - the matched row is preserved
  - the original blocked truth such as `SIF_AUTH_REQUIRED` is propagated into `53`

## Step 5 Rule Contract

- Step 5 rules are loaded only from `templates/selection_canonical_standards/90_下推参数表.csv`.
- Current required rules:
  - `S5_MIN_NATURAL_TRAFFIC_SHARE`
  - `S5_MAX_AD_TRAFFIC_SHARE`
  - `S5_MIN_HIGH_VALUE_KEYWORD_COUNT`
  - `S5_MAX_MEDIAN_SUGGESTED_BID`
  - `S5_PIT_STABILITY_REQUIRED`
- Rules are only hard-evaluated when the required metric is present.
- If the metric is blank because the SIF surface itself is blocked or missing:
  - the integration stays `HOLD`
  - it does not fabricate a business PASS
  - it does not overwrite the blocked truth with fake metric failures

## Step 6 Rule Contract

- Step 6 entry uses only `S6_MIN_PASS_STEPS` from `90_下推参数表.csv`.
- `61_待供应链核利清单.csv` only receives rows whose previous 5 stages are all `PASS`.
- If Step 5 is blocked or upstream queue stages are not all `PASS`, `61` may be header-only.

## Current Repo Truth On 2026-04-07

- P07 candidate pool is structured and readable, but still `HOLD` because the formal chain is blocked by Step 2.
- P08 SIF surfaces are structured, but both detail and search probes are currently `HOLD` with `SIF_AUTH_REQUIRED`.
- Therefore P09 must currently fail closed:
  - aligned `50/51/52` are allowed
  - `53` must stay blocked
  - `61` may legitimately be empty

## Runtime Script

- Builder:
  - `scripts/build_sif_enrichment_daytime_pack.py`
- Runtime logs:
  - `logs/sif_enrichment/latest_run.json`

## Safety Rules

- No runtime artifact enters git.
- No manual-only field is auto-filled.
- No model-authored business explanation is added.
- If the pool and SIF surfaces cannot be aligned, the status remains:
  - `BLOCKED_BY_SIF_OR_POOL_ALIGNMENT`
