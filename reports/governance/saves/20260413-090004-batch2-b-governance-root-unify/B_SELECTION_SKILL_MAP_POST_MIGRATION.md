# B_SELECTION_SKILL_MAP_POST_MIGRATION

## 1. Freeze
- canonical B-side root remains `E:/bzclaw-side`
- external `E:/选品文件夹/amazon-selection-automation` remains temporary migration/reference only
- this rerun confirms the post-migration business families are still visibly landed at:
  - `E:/bzclaw-side/configs`
  - `E:/bzclaw-side/skills`
  - `E:/bzclaw-side/templates`
  - `E:/bzclaw-side/reports/selection`

## 2. Canonical-root business map
- `configs/`
  - canonical business config surface
  - `configs/paths.json` points to `E:\bzclaw-side`
- `skills/`
  - canonical business skill-doc and imported skill surface
- `templates/`
  - canonical input-template and standards-contract surface
- `reports/selection/`
  - canonical stable current/reference business-report surface
- `scripts/`
  - canonical tool-runner entry layer remains under the root

## 3. Current active line reading
- current source priority remains:
  - `E:/bzclaw-side/reports/selection/MASTER_PROGRESS_BOARD__20260412.csv`
  - `E:/bzclaw-side/reports/selection/CODEX_REPO_TRUTH_REVALIDATION_AFTER_0118_SUMMARY_20260413.md`
  - `E:/bzclaw-side/reports/selection/CODEX_T11_T12_ARTIFACT_DEPTH_RECONCILIATION_SUMMARY_20260413.md`
  - `E:/bzclaw-side/skills/skill_sellersprite_four_line_runtime_registry.md`
  - `E:/bzclaw-side/skills/skill_sellersprite_t01_market_discovery.md`
- current line status remains:
  - `P0` = `FLOW_NOT_CLOSED__BUSINESS_NOT_APPLICABLE`
  - residual `P0` class = `NON_BLOCKING_HARDENING_DEBT`
  - `T01` = `FLOW_CLOSED__BUSINESS_NOT_PROMOTED__STABILITY_CONFIRMED`
  - current `T01` blocker = `T01_PURE_BUSINESS_HOLD__PROMOTION_NOT_LANDED`
  - `T02` = `FLOW_CLOSED__BUSINESS_NOT_PROMOTED__REUSABLE_LINE`
  - `T03` = `FLOW_CLOSED__BUSINESS_NOT_PROMOTED__REUSABLE_LINE`
  - `T04` = `FLOW_CLOSED__BUSINESS_NOT_PROMOTED__REUSABLE_LINE`
  - `T02 / T03 / T04` remain `POST_STAGE_OPEN_DEBT`, not current-stage blockers

## 4. Current legal wording
- SellerSprite fallback wording remains `SELLERSPRITE_NOT_CLOSED`
- split semantics remain:
  - `flow_closure_status = FLOW_CLOSED`
  - `business_promotion_status = BUSINESS_NOT_PROMOTED`
- split-form overall wording may therefore be written as:
  - `SELLERSPRITE_FLOW_CLOSED__BUSINESS_NOT_PROMOTED`

## 5. Attachment points after migration
- tool-runner entry:
  - `E:/bzclaw-side/scripts`
- skill registry and line skill docs:
  - `E:/bzclaw-side/skills`
- standards/templates:
  - `E:/bzclaw-side/templates`
- stable current/reference reports:
  - `E:/bzclaw-side/reports/selection`
- receipt/trace families:
  - canonical-root path families remain `outputs/`, `logs/`, and `playwright/`
  - many currently cited historical runtime artifacts still remain external-root references in this phase

## 6. Non-claims
- no runtime-active claim
- no publish-truth ownership upgrade
- no formal publish claim
- no project completion claim
- `models/` remains workspace only, not proof of stable model service

## 7. Risks / next step
- copied business reports remain a curated current/reference slice rather than the full external report history
- some live governance examples still point at external runtime evidence paths because those runtime families were intentionally not migrated
- next step:
  - keep future B-side prompt consumption anchored on the canonical root
  - use the A-side consumer sync note to align downstream prompt reads with the single-root governance reading
