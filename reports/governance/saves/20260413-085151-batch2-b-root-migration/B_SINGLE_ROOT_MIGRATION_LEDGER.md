# B_SINGLE_ROOT_MIGRATION_LEDGER

## 1. Batch identity
- batch_id: `B-B2-01`
- canonical_root: `E:/bzclaw-side`
- temp_reference_root_visible: `YES`
- source_read_mode: `Batch2 context pack + live repo-visible roots + Batch1 B-side outputs`

## 2. Migration policy
- copy_or_move_policy: `COPY_THEN_VERIFY`
- destructive_delete_performed: `NO`
- verification_policy: `family file-count check + target path existence + hash spot checks + canonical paths.json rewrite check`
- rollback_policy: `temp repo retained unchanged; canonical-root copy can be pruned or rewritten in a later governed slice if needed`

## 3. In-scope families
| family | source_root | target_root | action | result |
|---|---|---|---|---|
| `configs/` | `E:/选品文件夹/amazon-selection-automation/configs` | `E:/bzclaw-side/configs` | copied all files, then rewrote `configs/paths.json` to canonical-root paths | `PASS` |
| `skills/` | `E:/选品文件夹/amazon-selection-automation/skills` | `E:/bzclaw-side/skills` | copied full family with path meaning preserved | `PASS` |
| `templates/` | `E:/选品文件夹/amazon-selection-automation/templates` | `E:/bzclaw-side/templates` | copied full family with path meaning preserved | `PASS` |
| `business reports/` | `E:/选品文件夹/amazon-selection-automation/reports` | `E:/bzclaw-side/reports/selection` | copied selected stable current/reference reports only | `PASS` |

## 4. Excluded families
| family | reason |
|---|---|
| `logs/` | explicitly out of scope for this batch; logs are reference only |
| `outputs/` | explicitly out of scope; raw generated artifacts must not be migrated in this slice |
| `runs/` | explicitly out of scope; raw run evidence remains temp-root local truth |
| `models/` | explicitly out of scope; workspace presence alone does not prove stable model runtime |
| `playwright/` | explicitly out of scope; contains browser state, traces, screenshots, and auth-sensitive surfaces |
| raw generated evidence | explicitly out of scope; avoid promoting runtime artifacts into canonical migration cargo |
| credentials / secrets | explicitly out of scope by rule |
| local-only downloads / caches | explicitly out of scope by rule |

## 5. Path map summary
- total_candidates: `88`
- migrated_count: `88`
- skipped_count: `0`
- blocked_count: `0`

## 6. Verification summary
- target_paths_exist: `YES`
- spot_checks:
  - `skills/skill_sellersprite_four_line_runtime_registry.md` hash matches source copy
  - `templates/selection_canonical_standards/90_下推参数表.csv` hash matches source copy
  - `reports/selection/CODEX_T11_T12_ARTIFACT_DEPTH_RECONCILIATION_SUMMARY_20260413.md` hash matches source copy
  - `configs/paths.json` now points to `E:\\bzclaw-side`
- old_temp_repo_reference_retained: `YES`
- canonical_root_inventory_updated: `YES`
  - new visible business families now include `configs/`, `skills/`, `templates/`, and `reports/selection/`

## 7. Risks
- risk_1: canonical-root governance markdown still contains older dual-root wording and still needs the later rewrite slice.
- risk_2: temp business repo remains visible and still carries a deeper historical report stack with time-layer drift; copied reports here are intentionally curated, not exhaustive.
- risk_3: `configs/system.json` and some copied business docs preserve older operational wording; this migration slice fixes path hosting first and leaves governance wording cleanup to the next batch step.

## 8. Next step
- next_step: run the minimum B-side governance rewrite slice so canonical-root docs stop naming the temp external repo as the active business owner while preserving current project-level truth boundaries.
