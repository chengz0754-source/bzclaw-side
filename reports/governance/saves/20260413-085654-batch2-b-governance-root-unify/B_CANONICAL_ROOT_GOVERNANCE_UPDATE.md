# B_CANONICAL_ROOT_GOVERNANCE_UPDATE

## 1. Goal
Record the minimum governance/document changes needed after single-root migration.

## 2. Files touched
| file | why touched | result |
|---|---|---|
| `E:/bzclaw-side/A_B_HANDOFF_PROTOCOL.md` | remove old wording that treated the external repo as the active business execution owner and restate canonical root semantics | `UPDATED` |
| `E:/bzclaw-side/APPROVED_SKILL_EXECUTOR_SPEC.md` | add single-root read rule so approved-skill governance is explicitly anchored on `E:/bzclaw-side` | `UPDATED` |
| `E:/bzclaw-side/B_BUSINESS_TRACK_INVENTORY.md` | add canonical-root-first read rule and downgrade the external repo to migration/reference only | `UPDATED` |

## 3. Wording rewrites
- old dual-root wording removed:
  - `A_B_HANDOFF_PROTOCOL.md` no longer names the external repo as the active business execution owner
- external temp repo downgraded to reference-only:
  - the external `E:/选品文件夹/amazon-selection-automation` path is now stated as temporary migration/reference only where relevant
- canonical bzclaw-side wording added:
  - the touched live governance docs now anchor canonical B-side reading on `E:/bzclaw-side`
- non-claims retained:
  - no runtime-active claim
  - no publish-truth ownership upgrade
  - no formal publish claim
  - no project completion claim

## 4. Files intentionally not touched
| file | reason |
|---|---|
| `E:/bzclaw-side/reports/governance/saves/20260413-081526-batch1-b-rerun-single-shot/B_BSIDE_MONOREPO_ARCHITECTURE.md` | already the frozen canonical architecture source for this rewrite |
| `E:/bzclaw-side/reports/governance/saves/20260413-081526-batch1-b-rerun-single-shot/B_SELECTION_SKILL_MAP.md` | already states single-root and temp-reference semantics; this batch writes a post-migration follow-up report instead |
| migrated business families under `configs/`, `skills/`, `templates/`, and `reports/selection/` | this slice is governance wording only, not another migration rewrite |

## 5. Current canonical sentence
> B-side canonical root is `E:/bzclaw-side`; external `E:/选品文件夹/amazon-selection-automation` is temporary migration/reference only.

## 6. Risks
- risk_1: many other canonical-root governance docs outside this minimum slice may still preserve older dual-root historical wording.
- risk_2: runtime reference examples still legitimately point at external-root `outputs/`, `logs/`, and `playwright/` paths because those families were intentionally left unmigrated in B-B2-01.

## 7. Next step
- next_step: write the A-side consumer sync note and then, in a later governed cleanup slice, update remaining dual-root legacy docs while preserving runtime-reference-path history and current non-claims.
