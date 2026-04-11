# HERMES Runtime Governance Rules For Machine B

## 1. Purpose

This document defines how Hermes lands on the current B machine runtime plane.

It is written against the canonical repo `E:\bzclaw-side` and the repo-visible
state observed on `2026-04-11`.

It does **not** assume:

- a separate Hermes runtime repo already exists on B
- B already has hook, cron, MCP, or plugin hosts
- B is a truth host
- B is a mature worker platform

## 2. Global Rules

### 2.1 Repo Truth First

- only repo-visible state counts as canonical B runtime contract
- local-only runtime material may support execution, but it is not contract truth

### 2.2 B Is A Sidecar Execution Plane

- B is an independent sidecar repo
- B is not A-side truth host
- B is not formal publish host
- B is not the owner of promotion or retirement decisions

### 2.3 Fail Closed On Missing Runtime Hosts

If the repo does not currently expose a runtime host for a Hermes component,
that component must be documented as `SHADOW` or `rule-only`, not implied to be
live.

### 2.4 No Secret Material In Git

The following stay local-only:

- `.env`
- raw API keys
- cookies
- raw `storage_state*.json`
- persistent profile contents
- live screenshots and traces
- mutable runtime logs, outputs, and run payloads

### 2.5 B Supplies Evidence, Not Final Governance Truth

B may emit:

- receipts
- manifests
- evidence packs
- auth incidents
- replay attempts
- rollback references

B may not emit:

- final promotion decisions
- final retirement decisions
- truth-host closure claims

## 3. Component Rules

### 3.1 Sessions

- Sessions are B-side runtime objects.
- Repo-visible contract is limited to session metadata, reuse checks, auth
  incident records, and redacted session-derived artifacts.
- Raw session state remains local-only under `playwright/auth/**` and
  `playwright/profiles/**`.
- Session success only proves reusable access posture for the next scoped step.
  It does not prove business closure.

### 3.2 Context Files

- Context files are B-side runtime contract objects.
- `inputs/selection_run_current/**` and run-manifest style metadata are
  canonical repo-visible context surfaces.
- Reviewable context should remain structured, stable, and ingest-ready.
- Operator scratch notes, ad hoc downloads, and ephemeral browser state are not
  canonical context files.

### 3.3 Hooks

- Hooks are governance-first objects.
- Because B currently exposes no hook runtime host, hooks are rule-only in the
  current repo-visible contract.
- Any future hook must be:
  - tied to a named entrypoint
  - bounded in scope
  - non-recursive
  - receipt-emitting
- Hooks may not become an invisible orchestration layer.

### 3.4 Cron

- Cron on B is allowed only as a limited scheduler wrapper around an existing
  named entrypoint.
- Cron may not recursively start more cron jobs, self-author new jobs, or spawn
  an autonomous skill factory.
- Cron may not imply approval, publish, or promotion.
- Until a concrete scheduler surface exists in repo-visible state, cron remains
  `SHADOW`.

### 3.5 Provider Routing

- `configs/model.json` is the canonical B provider-routing source.
- Current default provider baseline is local `ollama_local`.
- `openai_cloud` remains a reserved but disabled slot until explicitly enabled.
- Provider routing in B is a limited baseline, not a mature orchestration plane.
- Provider success or provider fallback does not authorize a business-success
  claim.

### 3.6 Credential Pools

- Credential pools are local runtime handles with strict governance boundaries.
- Repo-visible contract may include:
  - `.env.example`
  - path placeholders
  - ignore rules
  - redacted auth governance notes
  - replay manifests and incident receipts
- Repo-visible contract may not include:
  - raw secrets
  - raw cookies
  - raw storage-state payloads
  - live profile material
- Credential handling must remain explicit and operator-bounded.
- No automatic credential harvesting, discovery, or silent rotation is allowed.

### 3.7 Checkpoints And Rollback

- Every scoped B-side governance or code change should be bracketed by git
  checkpoints.
- Controlled runs must emit manifests, artifact indexes, and evidence linkage
  so rollback posture is reviewable.
- B rollback covers local execution recovery and rollback references.
- B rollback does not equal publish-grade release rollback truth.
- Promotion-grade rollback and retirement semantics remain A-side.

### 3.8 Delegation

- Delegation in B means bounded routing across named scripts or approved
  imported skill surfaces.
- Delegation must remain explicit, scoped, and receipt-backed.
- Delegation may not auto-expand into an open-ended agent tree.
- Delegated runs still owe the same:
  - manifest
  - artifact index
  - evidence pack
  - receipt posture

### 3.9 MCP

- B currently has no repo-visible MCP host, registry, or connector contract.
- Therefore MCP is governance-only in the current B landing.
- Any future B-side MCP usage must begin as an allowlisted consumer mode.
- Connector approval, registry truth, promotion, and retirement remain A-side.

### 3.10 Skills / Plugins

- `skills/**` currently lands as imported approved execution surfaces in B.
- `skills/**` does not prove B already has a complete skill-runtime platform.
- `skills_runtime/` is a documented future B landing zone, but it is absent in
  the current repo-visible state.
- `plugins/` is also absent in the current repo-visible state.
- A owns:
  - formal definitions
  - governance manifest
  - promotion
  - retirement
- B owns:
  - imported execution surfaces
  - runtime wrappers when they later become repo-visible
  - execution telemetry

## 4. Repo-Visible Contract Policy

### 4.1 Allowed Into Repo Contract

- provider baseline config
- run manifests
- artifact indexes
- evidence-pack metadata
- redacted auth/session receipts
- imported skill code and skill-local schemas/configs
- governance rules for components whose runtime host is not yet present

### 4.2 Not Allowed Into Repo Contract

- raw auth payloads
- persistent browser profile contents
- mutable runtime screenshots and traces
- download folders
- temporary logs
- ad hoc run outputs
- secrets and credential payloads

## 5. Scorebook / Promotion / Retirement Rule

Hermes landing on B may contribute evidence for:

- scorebook input
- review packets
- shadow-run comparison
- limited execution telemetry

Hermes landing on B does not grant B ownership of:

- scorebook truth
- promotion
- retirement

Those outcomes remain A-side governance decisions, even when B provides the
runtime evidence.

## 6. Current Runtime Status On 2026-04-11

Placed with real current B-side surfaces:

- sessions
- context files
- provider routing
- credential governance
- checkpoints-and-rollback
- delegation
- skills

Placed as governance-only or shadow because no runtime host is visible:

- hooks
- cron
- MCP
- plugins
- `skills_runtime/`

## 7. Landing Conclusion

Hermes is now explicit in the B repo as a runtime-governance contract.

The landing is intentionally conservative:

- it uses only repo-visible truth
- it keeps missing runtime hosts explicit
- it preserves B as a light but real sidecar repo
- it avoids turning Hermes into invisible background wording

That is the correct baseline for later B8/B9 work.
