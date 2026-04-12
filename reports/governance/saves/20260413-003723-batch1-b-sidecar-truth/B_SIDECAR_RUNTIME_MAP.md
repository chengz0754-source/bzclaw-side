# B_SIDECAR_RUNTIME_MAP

## 1. Scope
- Batch id: `batch-1 / B machine / docs-only sidecar truth-freeze`
- Source bundle anchor: `C:\Users\Administrator\Downloads\BZCLAW_BATCH1_B_CONTEXT`
- Source package state anchor: `40__BZCLAW_PROJECT_SOURCE_MANIFEST_CURRENT_20260412.json` (`pack_version = 20260412-r79`)
- Workspace mode: `BUNDLE_AUTHORITATIVE__LOCAL_REPO_VISIBLE__NO_REMOTE_GIT__NO_INTERNET__DOCS_ONLY`
- Mandatory bundle files read:
  - `README_FIRST.md`
  - `REPO_DOSSIER/B_MACHINE_BATCH1_DOSSIER.md`
  - `REPO_DOSSIER/B_SIDE_HANDOFF_AND_EXECUTOR__fact_card.md`
  - `REPO_DOSSIER/bzclaw-side__root_visible_inventory.md`
  - `REPO_DOSSIER/AMAZON_SELECTION_AUTOMATION__fact_card.md`
  - `REPO_DOSSIER/amazon-selection-automation__root_visible_inventory.md`
  - `REPO_DOSSIER/A_CONTROL_PLANE_UNIFY_NOTE__extract.md`
  - `REPO_DOSSIER/project_map__PROJECT_MAP_CURRENT.md`
  - `PROJECT_STATUS/BZCLAW_项目进度总览_知识库治理版_20260412_v2.md`
  - `PROJECT_STATUS/39__BZCLAW_PROJECT_BACKGROUND_CURRENT_20260412.md`
  - `PROJECT_STATUS/40__BZCLAW_PROJECT_SOURCE_MANIFEST_CURRENT_20260412.json`
  - `TEMPLATES/TEMPLATE_B_SIDECAR_RUNTIME_MAP.md`
  - `TEMPLATES/TEMPLATE_B_SELECTION_SKILL_MAP.md`
- Local repo-visible files additionally read for freeze validation:
  - `E:\bzclaw-side\A_B_HANDOFF_PROTOCOL.md`
  - `E:\bzclaw-side\APPROVED_SKILL_EXECUTOR_SPEC.md`
  - `E:\bzclaw-side\B12_RERUN_WITH_BATCH5_PACKET_NOTE.md`
  - `E:\bzclaw-side\B_BUSINESS_TRACK_INVENTORY.md`
  - root listings under `E:\bzclaw-side\reports\governance` and `E:\bzclaw-side\scripts`

## 2. B-side role and boundaries
- B-machine two-layer structure:
  - sidecar/governance layer: `E:\bzclaw-side`
  - business skill layer: local visible owner repo `amazon-selection-automation` under the protocol-named selection workspace
- Canonical role sentence: `bzclaw-side` is the B-side sidecar/governance repository for a worker-style approved executor; it is not the publish-truth owner and not the A-host authority surface.
- Allowed actions:
  - receive A-to-B packet/dispatch context
  - run bounded sidecar or approved-skill execution surfaces when explicitly gated
  - assemble evidence, receipts, shadow-run bundles, and ingest-facing return objects
  - preserve local-only telemetry, auth-incident references, and governance notes
- Forbidden claims:
  - no whole-project completion claim
  - no formal publish claim
  - no business-verified or owner-approved closeout claim
  - no B-host truth-owner claim
  - B is not a publish-truth owner
  - B must not invent a second business-truth layer
  - B must not self-declare `runtime active`
  - no claim that a model runtime is landed merely because `models/` exists
  - no conversion of B-side artifacts into publish truth

## 3. Sidecar governance inputs
- `A_B_HANDOFF_PROTOCOL.md`
  - fixes A->B dispatch minimum fields, B->A return bundle expectations, and lane routing semantics
  - states that `DATA` and `B02` hosts were not observed locally on `2026-04-12`; they stay contract-intake surfaces in this round
  - records the real locally integrated example as the B-side shadow nightly bundle, not as a publish verdict
- `APPROVED_SKILL_EXECUTOR_SPEC.md`
  - fixes Machine B as a bounded `approved skill executor`
  - allowlists only four approved imported surfaces: `SK-01` to `SK-04`
  - keeps `scripts/**` as real execution lanes without auto-promoting them into approved skills
  - requires evidence/receipt style objects and fail-closed downgrades when approval provenance is unclear
- `B12_RERUN_WITH_BATCH5_PACKET_NOTE.md`
  - proves packet-first execution is a real repo-visible historical slice
  - supersedes the old A10-based B-12 result with the batch-5 rerun
  - keeps current effective B-12 status at `HOLD`
  - records `DATA = NOT_EXECUTED`, `B02 = NOT_EXECUTED`, and `ModelInferenceReceipt = NOT_EMITTED`
- `B_BUSINESS_TRACK_INVENTORY.md`
  - separates the business plane from the sidecar infrastructure plane
  - marks `scripts/` as the default live business lane and `skills/` as approved but non-default imported execution surfaces
  - keeps bootstrap/smoke/normalize/archive/temp helpers outside the business-lane truth

## 4. Sidecar visible surface map

| family | visible root/host | operational role | note |
| --- | --- | --- | --- |
| governance contracts | repo root markdown and csv hosts such as `A_B_HANDOFF_PROTOCOL.md`, `APPROVED_SKILL_EXECUTOR_SPEC.md`, `B12_RERUN_WITH_BATCH5_PACKET_NOTE.md`, `B_TO_A_OBJECT_MAPPING.csv`, `HERMES_EXECUTION_MAP_B.md` | define handoff, executor posture, return shapes, ownership, and routing | governance truth for B-side behavior; not publish truth |
| `inputs/` | `E:\bzclaw-side\inputs` | packet intake and bounded local dropzone surface | intake contract only; not a business-truth owner |
| `logs/` | `E:\bzclaw-side\logs` | telemetry, incidents, run logs, and evidence precursors | receipt-visible is local-only |
| `models/` | `E:\bzclaw-side\models` | reserved model workspace / adapter placement surface | existence alone does not prove active or stable model service |
| `outputs/` | `E:\bzclaw-side\outputs` | return-bundle and artifact carrier surface | outputs support A-host ingest and review |
| `playwright/` | `E:\bzclaw-side\playwright` | browser substrate, profiles, traces, screenshots | auth/profile materials stay local-only |
| `reports/governance/` | `E:\bzclaw-side\reports\governance` | governance saves, sync repairs, and truth-freeze notes | review surface only |
| `runs/` | `E:\bzclaw-side\runs` | timestamped local execution folders | local receipt and evidence organization |
| `scripts/` | `E:\bzclaw-side\scripts` | sidecar sync/export/governance automation | not a second business-truth layer |

## 5. A/B seam summary
- What A sends:
  - dispatch metadata such as `dispatch_id`, `lane_id`, `task_envelope_ref`, `run_mode`, `permission_profile`, `target_surface`, and expected return/verify/rollback expectations
  - packet manifests and supporting summaries for batch-driven intake
  - owner-sensitive operator notes when a lane is auth-sensitive or scope-sensitive
- What B receives:
  - contract-intake surfaces for `DATA` and `B02` when local hostlines are absent
  - executable shadow or approved surfaces such as `BT-11 / nightly acceptance` and allowlisted `SK-01..SK-04`
  - repo-visible inputs plus bounded local references
- What B returns:
  - `ArtifactReturnEnvelope`
  - `EvidencePack`
  - `ShadowRunReceipt` for shadow/dry-run slices
  - `reviewable summary`
  - telemetry/evidence indexes
  - `ModelInferenceReceipt` only when a real model call was emitted
- What B must never own:
  - A-host dispatch authority and lifecycle settlement
  - shared schema ownership from `tools/shared_contracts.py`
  - publish truth, business promotion, or final closeout verdicts
  - package-owned dispatch inflation from KB or sidecar artifacts

## 6. Operational meaning freeze
- A/B handoff operational meaning:
  - A/B exchange is now formalized rather than ad hoc.
  - B receives bounded dispatch context and returns reviewable artifacts for A-host ingest.
  - when hostlines are not locally observed, B must stay at contract-intake posture instead of inventing execution truth.
- approved skill executor operational meaning:
  - B can execute only explicitly allowlisted approved imported skill surfaces under a bounded entry gate.
  - `approved` is an execution-right posture, not a promotion-right posture.
  - high-value or high-confidence runs still remain below publish, business verdict, and authority ownership.
- B12 packet rerun operational meaning:
  - packet-first execution is a real repo-visible historical slice, not a hypothetical future design.
  - the batch-5 rerun supersedes the older A10-based slice as the current effective B-12 packet truth.
  - the resulting status remains `HOLD`, with `DATA` and `B02` still `NOT_EXECUTED` locally and no real model receipt emitted.

## 7. Risks / unresolved items
- `CONFLICT_VISIBLE`: a second local `amazon-selection-automation` checkout is visible at `E:\bzclaw side` while the sidecar handoff protocol and local visible owner repo point to `E:\选品文件夹\amazon-selection-automation`. This freeze treats the protocol-named repo as canonical and treats the current workspace copy as auxiliary visibility only.
- Raw A-host execution surfaces referenced by sidecar docs were not locally observed (`E:\bzclaw` absent in the handoff protocol note), so this map stays at contract/seam truth and does not claim cross-host execution completeness.
- Model profile status remains unconfirmed. Current sidecar examples explicitly show `ModelInferenceReceipt = NOT_EMITTED`.
- `bzclaw-side__root_visible_inventory.md` in the bundle is content-identical to the B-side fact card, so root visibility was additionally cross-checked against the live local repo listing before this document was frozen.
