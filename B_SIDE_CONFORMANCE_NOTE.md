# B-side Contract Intake / Conformance Note

## Scope

This note fixes how the current B-side repo surface maps into the A-side object family without creating a second naming system.

The goal of this round is intake alignment only:

- preserve the A-side object names already requested for B2
- explain which current B-side outputs can already map into those objects
- mark what is still missing before strict contract conformance can be claimed

This is not a business-upgrade note and not a claim that B already emits fully frozen canonical objects on disk.

## Freeze Source Used On 2026-04-11

No repo-visible A-machine A3 return artifacts were found under `E:\bzclaw-side` for:

- `A2_OBJECT_FAMILY_MATRIX.md`
- `A2_CANONICAL_OWNERSHIP_MAP.md`
- `A2_FREEZE_DECISION.md`

So this round uses the fallback package copies from:

- `C:\Users\Administrator\Downloads\BZCLAW_B_Machine_PromptPack_v3_final_20260411\BZCLAW_V3_B_机执行包_9Prompt_治理补齐版\A2_OBJECT_FAMILY_MATRIX.md`
- `C:\Users\Administrator\Downloads\BZCLAW_B_Machine_PromptPack_v3_final_20260411\BZCLAW_V3_B_机执行包_9Prompt_治理补齐版\A2_CANONICAL_OWNERSHIP_MAP.md`
- `C:\Users\Administrator\Downloads\BZCLAW_B_Machine_PromptPack_v3_final_20260411\BZCLAW_V3_B_机执行包_9Prompt_治理补齐版\A2_FREEZE_DECISION.md`

From those fallback A2 files, the following are explicitly frozen and owned:

- `DecisionDraft`
  - family: `control + shared bridge`
  - fallback canonical host: `control-contract-freeze-v1.ts`
- `ArtifactReturnEnvelope`
  - family: `shared runtime`
  - fallback canonical host: `tools/shared_contracts.py`
- `EvidencePack`
  - family: `shared runtime`
  - fallback canonical host: `tools/shared_contracts.py`

Important boundary:

- `ModelInferenceReceipt` and `ShadowRunReceipt` were requested by the B2 task and they do appear in package-level V3 materials such as `A_TO_B_DISPATCH_CONTRACT.md` and `BZCLAW_final_upgrade_plan_v3.md`.
- But those two names are not explicitly enumerated in the fallback `A2_OBJECT_FAMILY_MATRIX.md` or `A2_CANONICAL_OWNERSHIP_MAP.md`.
- Because no repo-visible A3 real return is present, this round does not silently rename them into other objects.
- B2 therefore keeps the requested names as intake targets, while marking their fallback-A2 freeze status as unresolved.

## B-side Repo Surfaces Used For Mapping

This mapping was built from repo-visible B-side truth plus the repo's declared runtime path conventions:

- `README.md`
- `configs/model.json`
- `models/README.md`
- `reports/nightly_run_operator_runbook.md`
- `reports/nightly_run_acceptance_report.md`
- `reports/candidate_pool_contract.md`
- `reports/CODEX_T02_STEP3_HANDOFF_OBJECT_SUMMARY_20260410.md`
- `reports/sellersprite_keyword_chain_contract.md`
- `reports/MARKET_EXPORT_PROOF.md`
- `reports/sellersprite_market_chain_output_index.csv`
- `scripts/`

And baseline constraints from B1:

- `B_SIDECAR_BASELINE.md`
- `B_MODEL_PROVIDER_BASELINE.md`
- `B_PATH_BASELINE_MAP.csv`

Important repo boundary:

- runtime `logs/**`, `outputs/**`, `runs/manual/**`, `playwright/screenshots/**`, and `playwright/traces/**` are intentionally local-only and ignored from git
- therefore B2 uses the repo-visible contracts, reports, and path conventions to anchor the mapping, rather than pretending those local runtime files are already in git

## Conformance Judgment By Object

### 1. `DecisionDraft`

Current closest B-side surfaces:

- route and purpose decisions under `logs/*/latest_route_decision.json`
- step and candidate-pool summaries under `logs/*/latest_run.json`
- downstream gate/result artifacts such as:
  - `outputs/selection_runs/<batch_id>/02_generated_outputs/03_候选市场与候选品初筛池.csv`
  - `outputs/selection_runs/<batch_id>/02_generated_outputs/60_候选样品池.csv`
  - `outputs/selection_runs/<batch_id>/02_generated_outputs/candidate_pool_summary.json`

Conformance judgment:

- B already emits usable draft-level status and reason-code material.
- B does not yet emit a canonical `DecisionDraft` wrapper object.
- The current surface is best treated as draft input to A-side control objects, not as A-side final approval truth.

Main missing pieces:

- stable object id / contract version
- upstream task or dispatch reference
- explicit decision scope / owner metadata
- verify linkage to evidence and return envelope
- decision state token

### 2. `EvidencePack`

Current closest B-side surfaces:

- Playwright screenshots and traces
- raw SellerSprite workbooks under `runs/manual/**`
- step logs under `logs/**/*.json` and `logs/**/*.jsonl`
- generated output indexes such as `*_output_index.csv` and `*_output_index.md`
- STEP1 -> STEP3 continuity material such as `13_step1_market_handoff.jsonl`

Conformance judgment:

- B already produces real evidence materials.
- Those materials are scattered across multiple local runtime paths.
- B does not yet emit a single canonical `EvidencePack` manifest that types, hashes, and links those items together.

Main missing pieces:

- pack id
- typed evidence item list
- capture metadata such as producer, timestamp, surface family
- hashes or checksums
- verify linkage back to `DecisionDraft` and `ArtifactReturnEnvelope`
- evidence state token

### 3. `ArtifactReturnEnvelope`

Current closest B-side surface:

- full run archive under `outputs/selection_runs/<batch_id>/`

The current B baseline already fixes the expected archive shape:

- `00_run_summary.md`
- `01_consumed_inputs/`
- `02_generated_outputs/`
- `03_logs/`

Conformance judgment:

- This is the correct current carrier for B -> A return intake.
- The archive shape is present and already documented in repo-visible truth.
- B still does not emit a canonical `ArtifactReturnEnvelope` manifest that explicitly lists returned objects, receipt refs, verify placeholders, and state.

Hard boundary:

- a directory that contains only `02_generated_outputs/` is a partial artifact package
- it is not a conformant `ArtifactReturnEnvelope`

### 4. `ModelInferenceReceipt`

Current closest B-side surface:

- provider wiring baseline in `configs/model.json`
- provider placement note in `models/README.md`
- environment probe in `scripts/survey_system.py`

Conformance judgment:

- The repo proves that B has a model/provider baseline:
  - default provider: `ollama_local`
  - default model: `qwen3:4b-instruct`
  - protocol: `openai_compatible`
- The repo does not show a stable emitted model-call receipt artifact under `logs/` or `outputs/`.
- So current B state supports provider baseline conformance only, not receipt conformance.

Main missing pieces:

- the receipt itself
- prompt or invocation reference
- output artifact linkage
- usage / timing / hash metadata
- verify linkage
- model receipt state token

### 5. `ShadowRunReceipt`

Current closest B-side surface:

- nightly dry-run reports and runbook
- `outputs/selection_runs/<batch_id>/00_run_summary.md`
- `outputs/selection_runs/<batch_id>/03_logs/nightly_acceptance_summary.json`

Conformance judgment:

- B already has a real repo-local dry-run path and a real archive-shaped dry-run package.
- That surface is the right precursor for `ShadowRunReceipt`.
- B does not yet emit a dedicated canonical receipt object that binds run mode, permission profile, upstream dispatch, comparison baseline, verification, and state.

Important boundary:

- dry-run or smoke success is not business closure
- `ShadowRunReceipt` must not be rewritten as business completion proof

## What A Can Reliably Consume After This Round

A can now read B-side output intent in one stable way:

- treat route decisions and candidate-pool status surfaces as `DecisionDraft` source material
- treat screenshots, traces, workbooks, raw JSON, output indexes, and handoff linkage files as `EvidencePack` source material
- treat full run archives as the carrier for `ArtifactReturnEnvelope`
- treat current model/provider data as baseline-only support for future `ModelInferenceReceipt`
- treat nightly dry-run summaries as the closest current precursor for `ShadowRunReceipt`, but not as a business closeout object

## What Is Still Missing Before Strict Conformance

The same missing set appears repeatedly across the current B-side surfaces:

- stable object ids and contract versions
- upstream dispatch / task / permission metadata
- explicit verify linkage between decision, evidence, and return objects
- normalized state tokens
- a first-class model-call receipt
- a first-class shadow-run receipt

## Final Intake Position

B2 is now aligned on object naming and mapping direction:

- no second naming system was introduced
- no smoke or workbook output was rewritten as business closure
- no silent remap of `ShadowRunReceipt` or `ModelInferenceReceipt` into unrelated object names was made

With `B_TO_A_OBJECT_MAPPING.csv` and `B_RETURN_SHAPE_SAMPLES.md`, A can now know exactly how current B-side outputs should enter the unified object family, and exactly which fields still need to be added for full contract conformance.
