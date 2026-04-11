# Approved Skill Executor Spec

## 1. Scope

This B8 spec fixes Machine B as a bounded `approved skill executor`, not as:

- an A-side truth host
- a formal publish host
- a mature worker platform
- a self-authoring skill factory

As of `2026-04-12`, no repo-visible A-machine `A3` or `A8` return artifacts were
found under `E:\bzclaw-side`. This round therefore uses the fallback package
copies of:

- `A2_OBJECT_FAMILY_MATRIX.md`
- `A2_CANONICAL_OWNERSHIP_MAP.md`
- `A2_FREEZE_DECISION.md`
- `SCOREBOOK_SURFACE_V1.md`
- `PROOF_MEASUREMENT_LAYER_V1.md`

## 2. Fixed Position

Machine B may execute an approved skill only when all of the following are true:

- the surface is repo-visible
- the surface is explicitly allowlisted as an approved imported execution surface
- the run is bounded to a named entrypoint
- the run emits observation and evidence objects
- the run does not cross into promotion, retirement, publish, or final business
  judgment

High score weight is not high permission. A high-confidence or high-value run
still stays inside the same bounded execution rights.

## 3. Current Approved Surface Allowlist

Current repo-visible approved imported skill surfaces are:

- `SK-01`
  - `skills/skill-market-route-m01-to-m02/run_market_m01_to_m02.py`
- `SK-02`
  - `skills/skill-market-route-step1-to-step3/scripts/run_market_route_pipeline.py`
- `SK-03`
  - `skills/skill-market-root-orchestrator/scripts/run_market_root_orchestrator.py`
- `SK-04`
  - `skills/skill-semantic-filter-local/scripts/run_semantic_filter.py`

Current interpretation:

- these four are the only repo-visible skill surfaces that may claim
  `approved skill executor` posture in B
- script-first business lanes under `scripts/**` are still real execution lanes,
  but they do not become approved skills automatically
- any new skill surface remains `shadow` or `limited` until A-side approval
  semantics become repo-visible

## 4. Approved Execution Entry Gate

An approved skill run must satisfy all gates below before execution starts:

- `surface_id` is one of `SK-01` to `SK-04`
- `entrypoint_ref` resolves to a real file under `skills/**`
- `dispatch_mode = approved`
- `host_role = b_sidecar`
- `input context` is captured from repo-visible inputs or a bounded local
  dropzone
- `provider / credential` use stays inside current B governance rules
- `unauthorized capability expansion = false`

Fail-closed rule:

- if approval provenance is unclear, the run downgrades to `shadow`
- if runtime host assumptions are missing, the run downgrades to `limited`
- if secret material would need to enter git truth, the run must stop

## 5. Mandatory Object Set For Approved Runs

Approved execution does not get a special B-only naming system. It must resolve
into the existing object family.

### Required canonical objects

- `ArtifactReturnEnvelope`
  - current B carrier: `outputs/selection_runs/<batch_id>/00_run_manifest.json`
- `EvidencePack`
  - current B carrier: `outputs/selection_runs/<batch_id>/03_logs/evidence_pack.json`
- `ExecutionReceipt`
  - current B precursor: `latest_run.json`, skill-local manifest, or skill-local
    run log until a first-class shared receipt file is emitted
- `VerificationResult`
  - required as a logical closeout slot even when current B only has verify
    placeholders
- `RollbackTrace`
  - required as a logical closeout slot even when rollback was not triggered
- `SkillObservation`
  - required governance closeout anchor for each approved run

### Conditional objects

- `ModelInferenceReceipt`
  - required only when the skill performs a real model call
  - `SK-04` is the most natural current source
- `HumanReviewEntry`
  - placeholder-only on B
  - used for operator score slots, not scorebook truth
- `ShadowRunReceipt`
  - only when the approved skill is deliberately run in canary/shadow posture

## 6. Standard Approved Closeout Fields

Every approved run must be readable through one `SkillObservation` joined to the
runtime objects above.

Minimum closeout fields:

- `input_summary`
  - run name, direction id, site, batch id, input refs, entrypoint ref
- `output_summary`
  - primary outputs, row counts when available, output refs, final status
- `kpi_delta`
  - local execution deltas only, such as row count, artifact count, retry count,
    latency, auth-hit count
- `verify_status`
  - `PASS`, `HOLD`, `FAIL`, or `NOT_RUN`
- `rollback_triggered`
  - `true` or `false`
- `error_type`
  - normalized runtime failure class
- `operator_score_placeholder`
  - present but unset by default

These fields describe bounded runtime closeout only. They do not equal final
business verdict.

## 7. Verify Rule For Approved Runs

Fallback scorebook hard-gate logic applies here. An approved run should not be
treated as verify-pass unless all of the following hold:

- schema / contract pass
- deterministic check pass
- verify pass
- rollback available
- no severe side effect
- no unauthorized attempt

Current B-side rule:

- if the hard gates are not all observable, `verify_status` stays `HOLD` or
  `NOT_RUN`
- B may emit `VerificationResult` placeholders or precursor facts
- B may not turn an incomplete verify surface into publish truth

## 8. Rollback Rule For Approved Runs

Rollback on B is local runtime rollback only.

Allowed rollback examples:

- restoring a prior local storage-state slot
- discarding a seeded runtime replay profile
- restoring a previous input snapshot or known-good generated package
- linking to git checkpoint refs for the local repo

Not allowed:

- claiming publish rollback truth
- rewriting retirement or promotion state

## 9. Evidence Rule

Approved skill execution must emit evidence as references, not as secret payload
promotion.

Evidence families that may be referenced:

- workbooks under `runs/manual/**`
- screenshots under `playwright/screenshots/**`
- traces under `playwright/traces/**`
- auth incidents under `logs/sellersprite_auth_incidents/**`
- run summaries and manifests under `outputs/selection_runs/<batch_id>/`

Hard boundary:

- raw auth state
- persistent profiles
- cookies / tokens / secrets

stay local-only and do not become closeout payload.

## 10. Current B-side Judgment

After B8, Machine B is fixed as:

- an approved executor for explicit imported skill surfaces only
- a bounded evidence and observation emitter for those runs
- a host that can close out runtime facts without claiming business closure

Machine B is not fixed as:

- a skill authorizer
- a skill promoter
- a skill retirement authority
- a final business decision maker
