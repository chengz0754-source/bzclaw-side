# CODEX SellerSprite Auth Replay Integration Summary (2026-04-09)

## Scope

This slice only covered the `amazon-selection-automation` sidecar repo.

Goals:

- integrate owner fake-login recordings into the SellerSprite auth replay flow
- let collectors try one local-only replay before fail-closed
- rerun the formal SellerSprite chain in this order:
  - STEP1 product research
  - STEP4 benchmark export
  - STEP2 keyword evidence
  - STEP3 market export
  - STEP7 candidate pool rebuild

Hard boundaries held in this slice:

- Git / repo-visible state remained the execution truth
- only Playwright page paths were used
- no unapproved API path was promoted
- sensitive auth state stayed local-only and ignored

## Git Truth At Start

Repo-level truth at start:

- `SELLERSPRITE_NIGHTLY_READY`

Business truth for `claw machine / US` at start:

- `SELLERSPRITE_NOT_CLOSED`

Chain truth at start:

- STEP1 product entry: auth-blocked on the real Product Research surface
- STEP2 keyword chain: artifact layer already reachable, business gate still `HOLD`
- STEP3 market chain: partial, route fixed to product-first for `PRODUCT_FORM`, live export still unstable
- STEP4 benchmark chain: partial, formal path depends on upstream real sample gates

## Repo Changes

Tracked repo files changed in this slice:

- `scripts/sellersprite_auth_replay.py`
- `scripts/register_owner_sellersprite_replays.py`
- `scripts/export_product_research.py`
- `scripts/export_benchmark_competitors.py`
- `scripts/export_market_report.py`
- `scripts/export_keyword_research.py`
- `scripts/export_keyword_trend.py`
- `scripts/sellersprite_nightly_orchestrator.py`
- `scripts/benchmark_chain_common.py`
- `scripts/build_market_workbook_index.py`

What changed:

- added a minimal local-only replay helper that turns owner recordings into reusable replay assets
- collectors now do:
  - detect auth surface
  - check replay registry
  - apply one replay if available
  - retry once
  - fail-closed if the retry still does not recover
- market export now supports `storage_state` execution after replay
- nightly state aggregation now records replay attempt metadata
- benchmark upstream resolution now fails with explicit repo-visible reason codes instead of raw file errors
- STEP3 workbook indexing now respects the passed `--market-dir` and no longer back-picks an old global workbook

## Local-Only Replay Assets

These assets were created or updated under ignored paths only:

- `playwright/auth/owner_recordings/<SURFACE>/recording_manifest.json`
- `playwright/auth/login_replays/*.py`
- `playwright/auth/login_replay_registry.json`
- `playwright/auth/replay_backups/*.json`
- `logs/sellersprite_auth_incidents/latest_replay_attempt.json`
- `logs/sellersprite_auth_incidents/replay_attempts.jsonl`

No owner `storage_state.json`, cookies, or tokens were added to Git.

## Replay Registry Status

Current replay registry state:

| surface_family | has_replay | verification |
| --- | --- | --- |
| `SELLERSPRITE_PRODUCT_RESEARCH_AUTH` | `true` | replay applied during STEP1 rerun |
| `SELLERSPRITE_EXPORT_LOG_AUTH` | `true` | replay asset probe applied locally |
| `SELLERSPRITE_MARKET_RESEARCH_AUTH` | `true` | replay applied during STEP3 rerun |
| `SELLERSPRITE_KEYWORD_MINER_AUTH` | `true` | replay applied during STEP2 rerun |
| `SELLERSPRITE_COMPETITOR_LOOKUP_AUTH` | `true` | alias registration prepared, not exercised in formal rerun |
| `SELLERSPRITE_LOGIN_GENERIC` | `false` | no generic replay registered |

Collector coverage in this slice:

- `export_product_research.py`
- `export_benchmark_competitors.py`
- `export_market_report.py`
- `export_keyword_research.py`
- `export_keyword_trend.py`
- `sellersprite_nightly_orchestrator.py`

## Formal Rerun Results

### STEP1 fresh `10 / 11 / 12`

Status:

- `BLOCKED`
- `reason_code = SELLERSPRITE_AUTH_REQUIRED`

Evidence:

- replay was available and was applied once
- first auth trigger was the real Product Research guest-only/export block
- retry switched to `storage_state`
- retry then opened the Product Research surface directly as a login page

Primary record:

- `logs/formal_auth_replay_20260410/step1_product/latest_product_research_run.json`
- `logs/formal_auth_replay_20260410/step1_product_build/latest_product_build_run.json`

Artifacts:

- no fresh `10_产品样本原始结果.csv`
- no fresh `11_产品样本种子池.csv`
- no fresh `12_产品样本下推结果.csv`

Truth label:

- replay integration recovered the auth handling path
- business artifact layer for STEP1 is still not restored

### STEP4 formal `40 / 41 / 42`

Status:

- `BLOCKED`
- `reason_code = STEP1_GATE_MISSING__OR__STEP3_PASS_SEED_MISSING`

Evidence:

- formal benchmark path no longer fell back to manual override
- fresh STEP1 did not produce a PASS gate/seed
- fresh STEP3 did not produce a PASS market gate/seed
- benchmark export therefore stopped before hitting the page-level competitor flow

Primary record:

- `logs/formal_auth_replay_20260410/step4_benchmark/latest_benchmark_export_run.json`
- `logs/formal_auth_replay_20260410/step4_benchmark_build/latest_benchmark_build_run.json`

Artifacts:

- no fresh `40_竞品基准结果.csv`
- no fresh `41_候选产品种子池.csv`
- no fresh `42_竞品基准下推结果.csv`

Truth label:

- route stayed formal
- replay integration for the collector is present
- this rerun was blocked by upstream formal inputs before auth replay could be exercised on STEP4 itself

### STEP2 fresh `20 / 21 / 22`

Status:

- artifact chain build: `PASS`
- business gate: `HOLD`

Evidence:

- keyword research hit the auth surface, replay was applied, and the retry recovered to a real workbook download
- keyword trend ran from the real page surface
- build step produced fresh canonical outputs

Primary record:

- `logs/formal_auth_replay_20260410/step2_keyword_research/latest_keyword_research_run.json`
- `logs/formal_auth_replay_20260410/step2_keyword_trend/latest_keyword_trend_run.json`
- `logs/formal_auth_replay_20260410/step2_keyword_build/latest_keyword_build_run.json`

Artifacts:

- `outputs/selection_runs/20260410_auth_replay_formal/02_generated_outputs/20_关键词证据词池原始结果.csv`
- `outputs/selection_runs/20260410_auth_replay_formal/02_generated_outputs/21_关键词证据词池清洗结果.csv`
- `outputs/selection_runs/20260410_auth_replay_formal/02_generated_outputs/22_关键词证据词池下推结果.csv`

Real-source classification:

- `keyword_research`: real workbook
- `keyword_trend`: real page
- `build_keyword_evidence_pool`: real structured build

Gate truth:

- `PASS = 0`
- `FAIL = 7`
- `HOLD = 12`

Truth label:

- replay integration restored the STEP2 collection chain
- STEP2 is not a business `PASS`

### STEP3 fresh `30 / 31 / 32`

Status:

- export rerun: `FAILED`
- `failure_reason_code = MARKET_TIMEOUT`

Evidence:

- first attempt hit the real `SELLERSPRITE_MARKET_RESEARCH_AUTH` surface
- replay was applied once
- retry no longer failed as auth
- retry still did not reach a workbook download and ended in `MARKET_TIMEOUT`

Primary record:

- `logs/formal_auth_replay_20260410/step3_market_export/latest_run.json`

Route truth:

- entry mode remained `product_market_analysis`
- because fresh STEP1 had no seed, this rerun used the latest already-real product seed entry to reach the market surface
- this proves the auth illusion was cleared on STEP3, but it does not count as fresh full STEP1 -> STEP3 artifact closure

Builder truth:

- `scripts/build_market_workbook_index.py` was fixed so it no longer back-picks an unrelated old workbook from the global market folder
- rerunning the builder against `runs/manual/10_market_auth_replay_formal` now fails cleanly with:
  - `No eligible .xlsx workbook was found in market_dir`

Artifacts:

- no fresh `30_市场调研原始索引.csv`
- no fresh `31_市场调研清洗结果.csv`
- no fresh `32_市场调研下推结果.csv`

Truth label:

- replay integration restored auth handling for STEP3
- the remaining blocker is a real export/runtime timeout, not a fake auth symptom

### STEP7 candidate pool rebuild

Status:

- `HOLD`
- `reason_code = NO_REAL_CANDIDATE_ROWS`

Primary record:

- `logs/formal_auth_replay_20260410/step7_candidate_pool/latest_run.json`

Artifacts:

- `outputs/selection_runs/20260410_auth_replay_formal_step7/02_generated_outputs/03_候选市场与候选品初筛池.csv`
- `outputs/selection_runs/20260410_auth_replay_formal_step7/02_generated_outputs/60_候选样品池.csv`
- `outputs/selection_runs/20260410_auth_replay_formal_step7/02_generated_outputs/60_候选样品池.md`

Artifact truth:

- the files were rebuilt from fresh direct-artifact inputs
- there were zero real source rows
- no old STEP1 or STEP4 artifacts were silently reused

Blocked reasons captured in the summary:

- `STEP3_CONTEXT_ROWS_MISSING`
- `NO_STEP1_OR_STEP4_REAL_SAMPLE_SOURCE`

Truth label:

- STEP7 fail-closed behavior is working
- STEP7 does not imply SellerSprite is closed

## Remaining Blockers

- STEP1 replay application succeeds, but the Product Research retry still lands on a login surface instead of a reusable authenticated product page.
- STEP4 formal path is still blocked by missing fresh upstream real sample gates.
- STEP3 auth illusion is cleared, but the export still times out before producing a workbook.
- STEP3 fresh builder/output cannot complete until a fresh workbook exists in the rerun market directory.
- `claw machine / US` remains business-level `SELLERSPRITE_NOT_CLOSED`.

## Exact Next Slice

The smallest next slice is:

1. repair the Product Research replay so the post-replay retry opens a usable authenticated `v3/product-research` page
2. rerun STEP1 fresh until `10 / 11 / 12` exist
3. rerun STEP4 on the formal path from the fresh STEP1 seed
4. rerun STEP3 again from a fresh product seed entry and confirm whether the outcome is a real workbook or a real `SOURCE_EMPTY` / timeout
5. rerun STEP7 from the fresh formal artifacts

Do not treat this slice as SellerSprite full closure.
