# B_SELECTION_SKILL_MAP

## 0. One-line freeze
- This selection skill map is frozen against the single canonical B-side root `E:/bzclaw-side`.
- The external repo `E:/选品文件夹/amazon-selection-automation` is read only as migration/reference support until its business subtree is absorbed under the canonical root.

## 1. Canonical B-side root
- All future B-side selection-skill prompts should anchor path semantics, save paths, and migration planning on `E:/bzclaw-side`.
- Current canonical-root visibility already includes `inputs/`, `logs/`, `models/`, `outputs/`, `playwright/`, `reports/`, `runs/`, and `scripts/`.
- Business-only families that are not yet top-level visible at the canonical root today, especially `configs/`, `skills/`, and `templates/`, are frozen as incoming single-root target slots rather than reasons to restore a second canonical repo.

## 2. Temporary external migration repo
- `E:/选品文件夹/amazon-selection-automation` was visible in this rerun and was read as a migration/reference support root.
- The live business evidence used from that root included:
  - `README.md`
  - `reports/MASTER_PROGRESS_BOARD__20260412.csv`
  - `reports/CODEX_CLOSURE_SEMANTICS_SPLIT_SUMMARY_20260412.md`
  - `reports/CODEX_REPO_TRUTH_REVALIDATION_AFTER_0118_SUMMARY_20260413.md`
  - `reports/CODEX_NEXT_SLICE_AFTER_REPO_RETRUTH_SUMMARY_20260413.md`
  - `reports/CODEX_FALLBACK_RECONCILE_CURRENT_FILES_AND_OUTPUTS_SUMMARY_20260413.md`
  - `skills/skill_sellersprite_shared_foundation.md`
  - `skills/skill_sellersprite_four_line_runtime_registry.md`
  - `skills/skill_sellersprite_t01_market_discovery.md`
  - `skills/skill_sellersprite_t02_product_idea_validation.md`
  - `skills/skill_sellersprite_t03_competitor_reverse_mining.md`
  - `skills/skill_sellersprite_t04_supply_chain_backsolve.md`
- These reads support subtree mapping only. They do not make the external repo a second permanent truth owner for future B-side prompts.

## 3. Directory semantics

| directory | single-root meaning | current visibility note |
| --- | --- | --- |
| `configs/` | business config, path baseline, and runtime parameter host | visible in the temporary external repo; frozen as an incoming canonical-root slot |
| `inputs/` | controlled intake surface for route rows, batch inputs, packet inputs, and rerun inputs | already visible at the canonical root and also present in the temporary external repo |
| `logs/` | local observation, route-decision, auth-incident, and latest-run evidence surface | already visible at the canonical root and also present in the temporary external repo |
| `models/` | reserved model workspace and adapter surface | already visible at the canonical root and also present in the temporary external repo |
| `outputs/` | generated artifact carrier, especially `outputs/selection_runs/<batch_id>/` style bundles | already visible at the canonical root and also present in the temporary external repo |
| `playwright/` | browser execution substrate for profiles, storage state, screenshots, and traces | already visible at the canonical root and also present in the temporary external repo |
| `reports/` | review/report layer; under single-root semantics this must separate sidecar governance from business summaries | canonical root already has `reports/governance`; the business repo currently carries the selection summary/report slice |
| `runs/` | raw run evidence, manual workbooks, replay support, and timestamped execution folders | already visible at the canonical root and also present in the temporary external repo |
| `scripts/` | primary tool-runner entry layer for route routing, line execution, orchestration, and sidecar helpers | already visible at the canonical root; business line runners are still evidenced in the temporary external repo |
| `skills/` | bounded business skill-doc layer and imported skill surfaces; this is skill inventory, not governance markdown | currently visible in the temporary external repo and frozen as an incoming canonical-root slot |
| `templates/` | canonical input templates, csv references, and standards contract surface | currently visible in the temporary external repo and frozen as an incoming canonical-root slot |

## 4. Active line summary
- The active line read below follows the latest visible repo state on `2026-04-13`, especially `README.md`, `reports/MASTER_PROGRESS_BOARD__20260412.csv`, `reports/CODEX_REPO_TRUTH_REVALIDATION_AFTER_0118_SUMMARY_20260413.md`, and `reports/CODEX_FALLBACK_RECONCILE_CURRENT_FILES_AND_OUTPUTS_SUMMARY_20260413.md`.
- Older `2026-04-12` reports and dossier summaries still carry `T01_STABILITY_NOT_CONFIRMED`; that older wording is now treated as lagging packet-era context, not the active line truth.

| line | skill doc | runner | current visible truth | current note |
| --- | --- | --- | --- | --- |
| `P0 / SHARED_FOUNDATION` | `skills/skill_sellersprite_shared_foundation.md` | `scripts/run_sellersprite_shared_foundation.py` | `FLOW_NOT_CLOSED__BUSINESS_NOT_APPLICABLE` | shared STEP1 / STEP4 continuity hardening remains an open debt even after checkpoint-resume hardening |
| `T01 / MARKET_DISCOVERY` | `skills/skill_sellersprite_t01_market_discovery.md` | `scripts/run_t01_market_discovery.py` | `FLOW_CLOSED__BUSINESS_NOT_PROMOTED__STABILITY_CONFIRMED` | current blocker is now promotion/writeback, not flow formation |
| `T02 / PRODUCT_IDEA_VALIDATION` | `skills/skill_sellersprite_t02_product_idea_validation.md` | `scripts/run_t02_product_idea_validation.py` | `FLOW_CLOSED__BUSINESS_NOT_PROMOTED__REUSABLE_LINE` | reusable exact-product line is landed, but business promotion remains closed |
| `T03 / COMPETITOR_REVERSE_MINING` | `skills/skill_sellersprite_t03_competitor_reverse_mining.md` | `scripts/run_t03_competitor_reverse_mining.py` | `FLOW_CLOSED__BUSINESS_NOT_PROMOTED__REUSABLE_LINE` | requires real seed lineage from earlier outputs and stays below business promotion |
| `T04 / SUPPLY_CHAIN_BACKSOLVE` | `skills/skill_sellersprite_t04_supply_chain_backsolve.md` | `scripts/run_t04_supply_chain_backsolve.py` | `FLOW_CLOSED__BUSINESS_NOT_PROMOTED__REUSABLE_LINE` | requires real `supplier_family` input and stays below business promotion |

## 5. Current overall legal wording / split semantics
- SellerSprite overall lawful fallback wording remains `SELLERSPRITE_NOT_CLOSED`.
- The current split semantics visible in the business repo are:
  - `flow_closure_status = FLOW_CLOSED`
  - `business_promotion_status = BUSINESS_NOT_PROMOTED`
- The current split-form overall wording may therefore be written as `SELLERSPRITE_FLOW_CLOSED__BUSINESS_NOT_PROMOTED`.
- This split wording does not elevate the selection business subtree into publish truth, runtime-active truth, or whole-project completion truth.

## 6. Best future attachment points

### tool runner entry
- The best future single-root tool-runner landing zone is `E:/bzclaw-side/scripts/`.
- The clearest attachment spine is:
  - `scripts/sellersprite_route_router.py`
  - `scripts/run_selection_direction_batch.py`
  - `scripts/run_sellersprite_purpose_line.py`
  - line runners `run_t01_market_discovery.py` to `run_t04_supply_chain_backsolve.py`
  - orchestration surfaces such as `scripts/sellersprite_nightly_orchestrator.py` and `scripts/run_nightly_selection_acceptance.py`

### receipt / trace host
- The best future receipt host is the canonical-root `outputs/`, `logs/`, and `playwright/` family.
- The most stable reference points already evidenced by canonical-root docs are:
  - `outputs/selection_runs/<batch_id>/00_run_manifest.json`
  - `outputs/selection_runs/<batch_id>/00_run_summary.md`
  - `outputs/selection_runs/<batch_id>/02_generated_outputs/artifact_index.json`
  - `outputs/selection_runs/<batch_id>/03_logs/evidence_pack.json`
  - `outputs/selection_runs/<batch_id>/03_logs/shadow_run_receipt.json`
  - `logs/sellersprite_auth_incidents/**`
  - `playwright/traces/**`
  - `playwright/screenshots/**`
  - canonical-root receipt index surfaces such as `TELEMETRY_EVIDENCE_OUTPUT_INDEX.csv`

### replay / rerun host
- The best future replay/rerun host is the canonical-root `inputs/`, `runs/`, `logs/`, `playwright/`, and `templates/` family.
- The most reusable rerun anchors are:
  - `inputs/selection_run_current/**`
  - `templates/selection_input_batches/**`
  - `runs/manual/**`
  - `scripts/sellersprite_auth_replay.py`
  - `scripts/sellersprite_nightly_orchestrator.py`
  - `scripts/run_nightly_selection_acceptance.py`

## 7. Migration recommendations
- Freeze all future B-side docs and save bundles under `E:/bzclaw-side` only.
- Land `configs/`, `skills/`, and `templates/` under the canonical root first, because those are the most obvious missing business families at the root today.
- Preserve the external repo's business path families during migration instead of flattening business meaning into root governance files.
- Keep `reports/governance/` sidecar-only and land business summaries under a separate business report surface such as `reports/selection/`.
- Update canonical-root docs that still hardcode the external repo as the business owner so they read as legacy references rather than active architecture.
- Keep the temporary external repo readable but non-canonical until subtree parity is visible under the canonical root.

## 8. Non-claims
- `models/` proves workspace only, not a stable model service.
- The business skill subtree is not the project publish-truth owner.
- The temporary external repo is reference only under this strategy.
- Governance markdown at the canonical root must not be treated as business skill inventory.
- Presence of runners or skill docs does not prove runtime active, business promoted, formally published, or project completed.

## 9. Risks / next step
- The largest remaining docs risk is time-layer drift inside the temporary external repo: older `2026-04-12` stability reports still conflict with later `2026-04-13` repo-visible revalidation files.
- The largest migration risk is that canonical-root governance docs still point at the external repo as the business execution owner.
- The next concrete step is a path-preserving migration slice that lands `configs/`, `skills/`, `templates/`, and the business report surface under `E:/bzclaw-side`, then rewrites the most important root governance docs to match the single-root freeze without changing project-level truth labels.
