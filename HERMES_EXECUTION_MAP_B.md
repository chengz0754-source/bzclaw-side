# HERMES Execution Map For Machine B

## 1. Scope

This document lands Hermes as an explicit execution-governance map for the
canonical Machine B sidecar repo at `E:\bzclaw-side`.

It does **not** redefine B as:

- an A-side truth host
- a formal publish host
- a mature worker platform
- a recursive skill factory

As of `2026-04-11`, no separate Hermes repo-visible runtime host was observed on
this machine. Hermes source truth visible to this turn comes from:

- `GPT5_V2_整改任务书_20260410.md`
- the B prompt-pack governance materials
- current repo-visible B-side runtime surfaces under `E:\bzclaw-side`

Therefore, Hermes is landed here as an explicit governance and runtime-placement
map over the current B-sidecar surfaces that actually exist today.

## 2. Current B Runtime Anchors

The current B repo already exposes these concrete surfaces:

- `configs/model.json` and `models/README.md` for provider baseline
- `configs/paths.json` and `configs/system.json` for path and machine-role wiring
- `inputs/selection_run_current/**` for current intake context
- `outputs/selection_runs/<batch_id>/` and `RUN_MANIFEST_SCHEMA.json` for
  run-envelope contract
- `playwright/auth/`, `playwright/profiles/`, `playwright/screenshots/`,
  `playwright/traces/` as local runtime/evidence roots
- `scripts/bootstrap_sellersprite_auth.py`,
  `scripts/check_sellersprite_session.py`,
  `scripts/bootstrap_sif_auth.py`,
  `scripts/sellersprite_auth_replay.py` for auth/session handling
- `skills/**` for imported approved execution surfaces

The current B repo does **not** expose these runtime hosts:

- `skills_runtime/`
- `hooks/`
- `cron/`
- `mcp/`
- `plugins/`
- a dedicated repo-visible `sessions/` host

That absence is itself part of the B-side truth and must stay explicit.

## 3. Component Map

### 3.1 Sessions

- Placement: `B`
- Class: runtime object governed by local execution rules
- Repo-visible contract: `PARTIAL`
- Current posture: `LIMITED`
- Scorebook / promotion / retirement: session telemetry can feed later review,
  but B does not own promotion or retirement

Current B landing:

- reusable-session checks live in
  `scripts/check_sellersprite_session.py`
- auth bootstrap lives in `scripts/bootstrap_sellersprite_auth.py` and
  `scripts/bootstrap_sif_auth.py`
- session-derived pack fragments already appear in business outputs such as
  `13a_step1_market_session_bundle.json`

Boundary:

- raw storage-state payloads and persistent-profile contents stay local-only
- repo-visible contract covers path policy, receipts, incident records, and
  redacted session metadata only

### 3.2 Context Files

- Placement: `B`
- Class: runtime object
- Repo-visible contract: `YES`
- Current posture: `APPROVED`
- Scorebook / promotion / retirement: these files can feed A-side ingest and
  review, but they are not themselves promotion objects

Current B landing:

- run intake context: `inputs/selection_run_current/**`
- run envelope context: `outputs/selection_runs/<batch_id>/00_run_manifest.json`
- object/evidence linkage: `artifact_index.json`, `evidence_pack.json`, related
  B2/B3 baseline documents

Boundary:

- context files are allowed in repo only when they are canonical templates,
  current controlled inputs, or manifest-style metadata
- local downloads, live raw secrets, and transient operator scratch context do
  not become repo-visible context files

### 3.3 Hooks

- Placement: `A` primary, `B` secondary only when a named runtime host exists
- Class: governance rule
- Repo-visible contract: `YES`, rule-only
- Current posture: `SHADOW`
- Scorebook / promotion / retirement: A-governed only

Current B landing:

- no repo-visible hook runtime host is present under `E:\bzclaw-side`

Boundary:

- B may document hook policy, but may not pretend hook execution already exists
- any future B-side hook must be tied to named entrypoints, bounded IO, and
  explicit receipts
- hooks may not self-expand into autonomous orchestration

### 3.4 Cron

- Placement: `B` runtime rule, with A-side governance boundary
- Class: governance rule for a future runtime object
- Repo-visible contract: `YES`, rule-only
- Current posture: `SHADOW`
- Scorebook / promotion / retirement: schedule telemetry may later feed review,
  but cron never owns promotion or retirement

Current B landing:

- no repo-visible scheduler or cron host is present in the current B repo

Boundary:

- cron is not a recursive self-boot skill factory
- any future scheduled run must wrap an already approved or limited named
  entrypoint
- cron may not discover new credentials, auto-promote flows, or spawn open-ended
  delegation trees

### 3.5 Provider Routing

- Placement: `B`
- Class: governance rule plus runtime config object
- Repo-visible contract: `YES`
- Current posture: `LIMITED`
- Scorebook / promotion / retirement: provider receipts may feed scorebook-like
  review later; provider routing itself is not a promotion object

Current B landing:

- canonical source: `configs/model.json`
- current baseline: `ollama_local`
- reserved but disabled cloud slot: `openai_cloud`
- explanatory baseline: `B_MODEL_PROVIDER_BASELINE.md`

Boundary:

- B currently has provider baseline wiring, not a mature provider-routing plane
- provider swap allowed does not mean cloud is enabled by default
- provider success does not equal business completion

### 3.6 Credential Pools

- Placement: `B` for local runtime handles, `A` for cross-host governance and
  approval boundaries
- Class: runtime object plus governance rule
- Repo-visible contract: `PARTIAL`
- Current posture: `LIMITED`
- Scorebook / promotion / retirement: auth incidents and reuse checks can feed
  review, but credential pools are never promotion objects

Current B landing:

- local paths: `playwright/auth/**`, `playwright/profiles/**`, `.env`
- redacted repo-visible policy: `.env.example`, `.gitignore`,
  `amazon-selection-automation.gitignore`, auth governance notes in `README.md`
- evidence and replay control: `scripts/sellersprite_auth_registry.py`,
  `scripts/sellersprite_auth_replay.py`

Boundary:

- raw secrets, cookies, storage-state payloads, and profile material stay
  local-only
- B may use named credential slots and replay manifests, but may not auto-rotate
  or auto-harvest credentials beyond approved local procedures

### 3.7 Checkpoints And Rollback

- Placement: `B` for local execution checkpoints and rollback references, `A`
  for formal promotion and retirement truth
- Class: governance rule plus runtime object
- Repo-visible contract: `YES`
- Current posture: `LIMITED`
- Scorebook / promotion / retirement: B may emit rollback evidence and
  checkpoint references; A remains the promotion/retirement owner

Current B landing:

- prompt-pack rule: checkpoint before and after scoped work
- run-manifest and artifact policy:
  `B_OUTPUT_ENVELOPE_SPEC.md`, `RUN_MANIFEST_SCHEMA.json`
- implementation helpers: `scripts/output_envelope_common.py`,
  `scripts/archive_selection_run_io.py`

Boundary:

- B rollback is local execution rollback and evidence rollback, not formal
  business release rollback truth
- B may record rollback references and recovery state, but not declare publish
  closure or retirement state

### 3.8 Delegation

- Placement: `B` for bounded execution delegation, `A` for approval and
  governance semantics
- Class: runtime object plus governance rule
- Repo-visible contract: `PARTIAL`
- Current posture: `LIMITED`
- Scorebook / promotion / retirement: delegated-run observations can feed A-side
  review; promotion and retirement stay A-owned

Current B landing:

- current bounded delegation surface exists under
  `skills/skill-market-root-orchestrator/**`
- additional approved imported surfaces exist under `skills/**`

Boundary:

- delegation in B means routing across named scripts or approved imported skills
- B does not own unbounded agent expansion, self-authoring execution trees, or
  autonomous capability growth
- every delegated execution must still emit the same run/evidence contract

### 3.9 MCP

- Placement: `A` primary, `B` secondary only as an allowlisted consumer surface
- Class: governance rule
- Repo-visible contract: `YES`, rule-only
- Current posture: `SHADOW`
- Scorebook / promotion / retirement: A-governed only

Current B landing:

- no repo-visible MCP registry, server config, or connector contract is present
  in the current B repo

Boundary:

- B must not pretend MCP hosting already exists
- any future B-side MCP use should begin as explicit allowlisted consumption, not
  as an unbounded connector plane
- registry, approval, and retirement semantics remain A-side governance concerns

### 3.10 Skills / Plugins

- Placement: `A` owns approval, promotion, retirement, and formal definitions;
  `B` owns imported execution surfaces and future runtime wrappers
- Class: split governance surface and runtime object
- Repo-visible contract: `YES`
- Current posture: `APPROVED_IMPORTED_SURFACE` for `skills`, `SHADOW` for
  `plugins`
- Scorebook / promotion / retirement: B can emit execution telemetry; A owns
  scorebook gating, promotion, and retirement

Current B landing:

- imported approved skill surfaces already exist under `skills/**`
- prompt-pack target runtime landing zone is `E:\bzclaw-side\skills_runtime\`
- `skills_runtime/` is not yet present in the current repo
- no repo-visible plugin host is present in the current repo

Boundary:

- current `skills/**` proves imported execution surfaces exist
- current `skills/**` does not prove B has already become a full skill-runtime
  platform
- plugin governance cannot be inferred from skill presence

## 4. Repo-Visible Contract Summary

The Hermes items that already have real B-side repo-visible contract surfaces are:

- context files
- provider routing baseline
- checkpoint-and-rollback policy
- sessions metadata and auth governance, in redacted form
- bounded delegation through imported skill surfaces
- skills as imported execution surfaces

The Hermes items that are only landed here as governance placeholders, because no
runtime host is currently visible in the repo, are:

- hooks
- cron
- MCP
- plugins
- `skills_runtime/` as a future B runtime landing zone

## 5. Scorebook / Promotion / Retirement Rule

Machine B may emit:

- manifests
- receipts
- evidence packs
- auth incidents
- replay attempts
- rollback references
- delegated execution observations

Machine B may **not** own:

- final scorebook truth
- promotion decisions
- retirement decisions
- publish-grade release truth

Those governance outcomes remain A-side concerns even when B supplies the runtime
evidence.

## 6. Landing Result

Hermes is no longer treated as a background absorption note in B.

The current landing is:

- explicit
- repo-visible
- aligned to the surfaces B actually has today
- fail-closed where Hermes runtime hosts do not yet exist

This is enough for later prompts to reference Hermes in B without inventing a
second semantic system or overstating current B runtime maturity.
