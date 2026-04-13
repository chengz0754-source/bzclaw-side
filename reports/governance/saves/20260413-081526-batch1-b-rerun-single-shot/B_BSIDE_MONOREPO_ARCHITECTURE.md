# B_BSIDE_MONOREPO_ARCHITECTURE

## 0. One-line freeze
- `E:/bzclaw-side` is the frozen canonical B-side root for future batches.
- `E:/选品文件夹/amazon-selection-automation` is temporary migration/reference only and is not a second permanent canonical B-side root.

## 1. Canonical root
- The required root `E:/bzclaw-side` was visible at the start of this rerun and is the only lawful save host for this batch output.
- Current root-visible B-side surfaces already include `inputs/`, `logs/`, `models/`, `outputs/`, `playwright/`, `reports/`, `runs/`, `scripts/`, root governance markdown/csv files, and `reports/governance/saves/`.
- This means the frozen B-side architecture is anchored on a real visible repo, not on a hypothetical future folder.

## 2. Why old dual-root semantics are now obsolete
- Older B-side repo-visible docs still contain dual-root wording and explicit references to `E:/选品文件夹/amazon-selection-automation` as the business execution repo. Those references are historical repo-visible facts, not future architecture gates.
- The owner directive in this rerun bundle explicitly fixes future B-side canonical root selection to `E:/bzclaw-side` and explicitly forbids reopening the owner-choice question.
- The previous Batch1 stop happened because the old prompt family still encoded `sidecar repo + separate permanent business repo`; it did not prove that the owner decision was still open.
- Therefore future B-side prompts must stop modeling the B side as two permanent canonical repos.

## 3. Temporary external repo boundary
- `E:/选品文件夹/amazon-selection-automation` may be read only as migration/reference support while migration is incomplete.
- It is allowed to contribute current business inventory, runner paths, skill docs, templates, and historical business reports.
- It is not allowed to remain a peer canonical truth root for future B-side architecture decisions.
- It must not be merged with `E:/bzclaw-side` into a synthetic combined truth layer. Statements should stay explicit about whether they describe:
  - current canonical-root visible fact
  - temporary external reference fact
  - target-layout intent under the single-root strategy

## 4. Single-root B-side meaning
- Under this freeze, `bzclaw-side` no longer means "sidecar-only repo".
- It now means the one canonical B-side monorepo root that will host both:
  - sidecar/governance/receipt surfaces
  - selection/business skill/runtime surfaces
- This changes B-side file-hosting semantics, not project authority boundaries.
- A-host remains the control-plane and lifecycle owner.
- B remains below publish-truth ownership and may not self-declare runtime active.

## 5. Sidecar subtree meaning
- The sidecar subtree is the governance-and-seam slice already visible inside the canonical root.
- Its current center of gravity is:
  - root governance files such as `A_B_HANDOFF_PROTOCOL.md`, `APPROVED_SKILL_EXECUTOR_SPEC.md`, and `B12_RERUN_WITH_BATCH5_PACKET_NOTE.md`
  - `reports/governance/` and `reports/governance/saves/`
  - receipt/index surfaces such as `TELEMETRY_EVIDENCE_OUTPUT_INDEX.csv`
  - sidecar utility/export/sync scripts under `scripts/`
- Operationally, this subtree owns contract intake, routing clarity, receipt preservation, shadow-run/evidence handling, and A/B seam discipline.
- It does not become a business closeout owner, publish-truth owner, or replacement for real business skill inventory.

## 6. Business subtree meaning
- The business subtree is the SellerSprite/selection execution slice currently evidenced in the temporary external repo and already referenced by canonical-root governance docs.
- Its visible family today is the familiar business runtime set:
  - `configs/`
  - `inputs/`
  - `logs/`
  - `models/`
  - `outputs/`
  - `playwright/`
  - `reports/`
  - `runs/`
  - `scripts/`
  - `skills/`
  - `templates/`
- It also carries the actual business runner and skill surfaces such as:
  - `scripts/sellersprite_route_router.py`
  - `scripts/run_selection_direction_batch.py`
  - `scripts/run_t01_market_discovery.py`
  - `scripts/run_t02_product_idea_validation.py`
  - `scripts/run_t03_competitor_reverse_mining.py`
  - `scripts/run_t04_supply_chain_backsolve.py`
  - `scripts/sellersprite_nightly_orchestrator.py`
  - `scripts/run_nightly_selection_acceptance.py`
- After migration these families belong under the canonical root, but they still remain below publish truth, whole-project completion, and runtime-active claims.

## 7. Recommended target layout
- Recommended stable near-term layout under `E:/bzclaw-side` is one root with root-level business families and an explicit governance/report split:

```text
E:/bzclaw-side/
  configs/
  inputs/
  logs/
  models/
  outputs/
  playwright/
  reports/
    governance/
    selection/
  runs/
  scripts/
  skills/
  templates/
  root governance markdown/csv
```

- This layout is chosen because:
  - most runtime families already exist at the canonical root
  - the external business repo already uses the same family names
  - it minimizes path-shape churn during migration
  - it supports Step 2 directory semantics without keeping a second permanent repo
- `returns/` may remain as an auxiliary sidecar carrier until a later cleanup slice; it does not define the business subtree.

## 8. Migration boundary and temporary coexistence rule
- During migration, both visible roots may coexist, but with asymmetric roles:
  - canonical future B-side root: `E:/bzclaw-side`
  - temporary migration/reference root: `E:/选品文件夹/amazon-selection-automation`
- New freezes, save bundles, and future prompt outputs must land under the canonical root only.
- The temporary external repo may be consulted to recover business subtree content, but it must not reopen the old owner-choice gate.
- Migration should preserve business path families instead of flattening business logic into governance markdown.
- Canonical-root docs that still hardcode the external repo as the business owner should be updated or marked legacy in a later repo-visible migration slice.

## 9. Current non-claims
- No whole-project completion claim.
- No formal publish or Hub release claim.
- `DATA_ONLY__SELECTIVE_PUBLISH_ACTIVE` remains the only lawful selective publish scope.
- `product_coldstart_B02` remains `LOCAL_STABLE`, not complete.
- B is not publish truth owner.
- B may not self-declare runtime active.
- The temporary external repo is not a second permanent canonical truth root.
- Current directory presence does not prove that migration is already complete.

## 10. Later B-side prompt read order
1. Live repo-visible state under `E:/bzclaw-side`
2. `B_BSIDE_MONOREPO_ARCHITECTURE.md`
3. `B_SELECTION_SKILL_MAP.md`
4. `A_B_HANDOFF_PROTOCOL.md`
5. `APPROVED_SKILL_EXECUTOR_SPEC.md`
6. `B_BUSINESS_TRACK_INVENTORY.md`
7. `TELEMETRY_EVIDENCE_OUTPUT_INDEX.csv` and other receipt/index surfaces
8. `E:/选品文件夹/amazon-selection-automation` only if migration/reference verification is needed

## 11. Risks / open migration items
- Top-level `configs/`, `skills/`, and `templates/` are not yet visibly landed at `E:/bzclaw-side`; they are frozen as incoming target slots because the temporary business repo still carries them.
- Many canonical-root docs still preserve older dual-root wording and will need later repo-visible cleanup.
- Temporary external repo reports contain time-layer drift. When current line status conflicts with older packet-era reports, later repo-visible board/README/revalidation files should win over older snapshots.
