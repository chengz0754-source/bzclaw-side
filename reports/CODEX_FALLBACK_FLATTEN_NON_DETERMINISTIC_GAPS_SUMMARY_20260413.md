# CODEX Fallback Flatten Non-Deterministic Gaps Summary (2026-04-13)

## Current Reality

- SellerSprite current-stage legal closure no longer depends on Codex for the primary judgment.
- The remaining gaps are not "Codex must decide again" gaps.
- The remaining gaps are "summary-backed evidence", "prose-backed host alignment", and "stale path metadata" gaps.

## 1. Judgments Still Not Fully Machine-Readable

- `reports/latest_sellersprite_stage_status.json` still builds `artifacts.records` from regex parsing of markdown summaries:
  - `reports/selection/CODEX_T11_T12_ARTIFACT_DEPTH_RECONCILIATION_SUMMARY_20260413.md`
  - `reports/selection/CODEX_REPO_TRUTH_REVALIDATION_AFTER_0118_SUMMARY_20260413.md`
- Current evaluator result still says:
  - `source_mode = summary_extract`
  - `actual_csv_records_found = 0`
- `reports/latest_sellersprite_owner_handoff.json` still synthesizes the next-stage candidate list from stage truth instead of a direct repo-local `60` candidate-pool host:
  - `candidate_source_mode = stage_truth_fallback`
  - `candidate_pool_csv_path = null`
- `readme_aligned` and `registry_aligned` are still judged by markdown fragment containment, not by a structured host schema.
- `why_next_stage_starts` and `next_stage_reason` are still emitted as prose strings, not coded reason enums.

## 2. Current Hosts Still Requiring Prose Reconciliation

- `README.md`
  - deterministic output host, but current validation still checks prose fragments
- `skills/skill_sellersprite_four_line_runtime_registry.md`
  - deterministic output host, but current validation still checks prose fragments
- `reports/selection/CODEX_T11_T12_ARTIFACT_DEPTH_RECONCILIATION_SUMMARY_20260413.md`
  - currently used as a regex-parsed truth carrier for `12 / 22 / 42 / 60`
- `reports/selection/CODEX_REPO_TRUTH_REVALIDATION_AFTER_0118_SUMMARY_20260413.md`
  - currently used as a fallback regex-parsed truth carrier
- `reports/selection/MASTER_PROGRESS_BOARD__20260412.csv`
  - not a prose host for closure itself, but still contains stale symbolic paths that need reconciliation:
  - all `runner_py` paths currently point to files that do not exist in repo
  - several `summary_file` paths point to `reports/`, while the current files live under `reports/selection/`

## 3. Scripts Still Missing a Deterministic Contract

- `scripts/evaluate_sellersprite_stage_status.py`
- `scripts/sellersprite_stage_closure_lib.py`
  - missing a canonical machine-readable artifact manifest for `T11/T12 x 12/22/42/60`
  - fallback still depends on parsing markdown summaries
- `scripts/generate_sellersprite_owner_handoff.py`
  - missing a canonical direct candidate-pool contract host
  - missing a standalone machine-readable owner handoff contract
  - required owner-side fields and eligibility rules are still hardcoded in script constants
- `scripts/reconcile_sellersprite_truth_hosts.py`
- `scripts/write_sellersprite_current_state.py`
  - current README / registry validation still depends on prose fragments instead of a structured host schema
- `reports/selection/MASTER_PROGRESS_BOARD__20260412.csv`
  - its `runner_py` metadata currently has no matching executable contract in repo

## 4. Smallest Next Cut

- Add one canonical machine-readable truth pack, for example:
  - `reports/selection/SELLERSPRITE_STAGE_TRUTH_PACK__20260413.json`
- That truth pack should flatten, in one place:
  - `T11/T12` artifact matrix for `12 / 22 / 42 / 60`
  - normalized current candidate-pool rows or current candidate-path rows
  - coded closure reason enums
  - coded next-stage reason enums
  - owner handoff field schema reference
  - canonical board path mapping for `runner_py` and `summary_file`
- Then patch the active scripts so that:
  - evaluator reads only structured truth pack + contract + board/debt CSV
  - handoff generator reads only structured truth pack + owner handoff contract
  - README / registry become write-only derived hosts
  - markdown summaries stop acting as live truth inputs

## 5. Can Fully Self-Running Still Be Finished in One Round?

- Yes, if the next round stays narrow:
  - create the structured truth pack
  - add one owner handoff contract JSON
  - remove markdown parsing from the active pipeline
  - clean stale board paths
- No, if the requirement is upgraded to "must ingest direct repo-local raw `12/22/42/60` CSV plus direct `60` candidate-pool CSV":
  - those raw artifact hosts are not currently visible in this repo

## Final Flattened Verdict

- Current-stage closure logic is already deterministic.
- The remaining non-deterministic layer is truth carriage, not closure adjudication.
- One more narrow round is enough if we flatten the remaining truth into a single machine-readable pack and stop parsing markdown summaries.
