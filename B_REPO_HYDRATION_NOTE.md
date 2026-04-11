# B Repo Hydration Note

## 1. Scope

This prompt only performs canonical repo hydration and source absorb for the
Machine B sidecar repo.

It does not:

- upgrade business capability
- start B2/B3/B4 implementation
- turn B into a mature worker platform
- turn B into a truth host or formal publish host

## 2. Start State

At the start of B1.5:

- canonical path `E:\bzclaw-side` was `PATH_NOT_FOUND`
- the visible local git repo at `E:\bzclaw side` tracked only:
  - `B_SIDECAR_BASELINE.md`
  - `B_PATH_BASELINE_MAP.csv`
  - `B_MODEL_PROVIDER_BASELINE.md`
- the real execution-side repo-visible assets were still primarily in:
  - `E:\选品文件夹\amazon-selection-automation`

This meant B1 had frozen the baseline semantics, but the canonical repo path
still did not expose the actual repo-owned execution assets required by later
Machine B prompts.

## 3. Hydration Action

This round performed the following actions:

1. materialized the canonical repo path at `E:\bzclaw-side`
2. preserved the existing baseline-only git state as the canonical repo base
3. absorbed the source repo's repo-visible tracked files from
   `E:\选品文件夹\amazon-selection-automation` into `E:\bzclaw-side`
4. kept runtime-only and sensitive local state out of absorb scope
5. added this hydration note and a completeness checklist

Absorb rule:

- source of copy = source repo `git ls-files`
- not copied = untracked local runtime payloads, secrets, auth state, outputs,
  logs, traces, screenshots, cached data, downloads, `.venv`

## 4. Repo-Owned Assets Now Visible In The Canonical Repo

The canonical repo now exposes the repo-owned Machine B sidecar assets needed
for later prompts, including:

- root repo files:
  - `README.md`
  - `package.json`
  - `requirements.txt`
  - `.gitignore`
  - `.env.example`
- fixed config surfaces:
  - `configs/model.json`
  - `configs/paths.json`
  - `configs/system.json`
- model notes:
  - `models/README.md`
- execution surface:
  - `scripts/**`
- imported legacy execution code/docs:
  - `skills/**`
- repo-visible input layer:
  - `inputs/README.md`
  - `inputs/selection_run_current/**`
- repo-visible standards and templates:
  - `templates/**`
- repo-visible reports and contracts:
  - `reports/**`
- tracked placeholders for local-only runtime directories:
  - `logs/README.md`
  - `outputs/README.md`
  - `runs/.gitkeep`
  - `playwright/auth/.gitkeep`
  - `playwright/profiles/.gitkeep`
  - `playwright/screenshots/.gitkeep`
  - `playwright/traces/.gitkeep`

## 5. Content That Still Must Remain Local Only

The following categories are still local-only and must not be treated as git
truth:

- `.env`
- `.venv/`
- `node_modules/`
- real API keys, cookies, tokens, session files
- `playwright/auth/*.json` real storage states and replay payloads
- `playwright/profiles/**` real browser profile contents
- `playwright/screenshots/**` runtime screenshots
- `playwright/traces/**` trace zips
- runtime payloads under `logs/**`
- runtime payloads under `outputs/**`
- raw workbook/download payloads under `runs/manual/**`
- caches, archive folders, inbox folders, temp files

## 6. Readiness For B2 / B3 / B4

Required repo-visible must-read surfaces now exist at the canonical path:

- `E:\bzclaw-side\B_SIDECAR_BASELINE.md`
- `E:\bzclaw-side\B_PATH_BASELINE_MAP.csv`
- `E:\bzclaw-side\B_MODEL_PROVIDER_BASELINE.md`
- `E:\bzclaw-side\README.md`
- `E:\bzclaw-side\package.json`
- `E:\bzclaw-side\requirements.txt`
- `E:\bzclaw-side\configs\paths.json`
- `E:\bzclaw-side\configs\model.json`
- `E:\bzclaw-side\models\README.md`
- `E:\bzclaw-side\scripts\**`

Current B-side execution reality to keep using:

- current repo-visible execution surface = `scripts/` + imported `skills/`
- `skills_runtime/` is still not observed in the hydrated repo and must not be
  assumed as present

Readiness conclusion:

- B2/B3/B4 are now unblocked on repo visibility
- later prompts should read the hydrated canonical repo at `E:\bzclaw-side`
- later prompts must still respect the baseline that B is a lightweight,
  independent sidecar repo rather than a mature worker platform

## 7. Final Judgment

This hydration round is closed when interpreted as a canonical repo absorb
prompt:

- the canonical path now exists
- the required repo-visible sidecar assets are present
- the distinction between git-owned content and local-only runtime state is
  explicit

Therefore:

- canonical repo hydration: `COMPLETE`
- B2/B3/B4 readiness from a repo-visible baseline perspective: `YES`
