# B Side Cleanup Prune Note

## Scope

- date: `2026-04-12`
- repo: `E:\bzclaw-side`
- purpose: restore `bzclaw-side` to a low-entropy governance/seam repo after dual-repo bootstrap and batch-5 B-12 rerun

## Protected Current Truth

- current effective B-12 consumed A packet: `20260412-0631-A-B-BATCH5-FRONTEND-REFRESH-READY`
- current effective B->A packet: `20260412-0750-B-A-B12_BATCH5_INTEGRATED_RUN-READY`
- current effective B-12 state: `BT-11 = EXECUTED / HOLD`, `DATA = NOT_EXECUTED`, `B02 = NOT_EXECUTED`
- old A10-based B-12 result: `SUPERSEDED`

## Prune Actions Completed

- removed selection-owned root manifests from `bzclaw-side`:
  - `README.md`
  - `package.json`
  - `requirements.txt`
- removed legacy selection-program docs and stray non-owner files from repo root
- removed selection-owned mirror directories:
  - `configs/`
  - `templates/`
  - `skills/`
- removed mirrored selection input payloads from `inputs/selection_run_current/**`
- removed selection-owned business-flow reports from `reports/` and kept `reports/governance/**`
- pruned `scripts/` down to repo-specific B-side governance/sync entrypoints only
- removed the stray root-level file `市场分析`

## B-side Surfaces Intentionally Retained

- B-side baseline, intake, envelope, Hermes, handoff, closeout, and batch-5 rerun docs at repo root
- `reports/governance/**`
- repo-specific B-side scripts:
  - `scripts/git_sync_bside_main.ps1`
  - `scripts/git_sync_bside_main.bat`
  - `scripts/git_sync_main.ps1`
  - `scripts/git_sync_main.bat`
  - `scripts/git_sync_repo_main.ps1`
  - `scripts/git_sync_repo_main.bat`
  - `scripts/export_bside_governance_docs_to_selection_repo.ps1`
- runtime skeleton directories:
  - `logs/`
  - `outputs/`
  - `runs/`
  - `playwright/`
  - `inputs/`
  - `models/`

## Current Boundary After Prune

- `bzclaw-side` is not a second business execution repo
- selection canonical owner files are no longer kept as root-level mirrors in `bzclaw-side`
- future operator flow must use:
  - selection repo for business execution source
  - shared exchange packets for cross-machine delivery
  - `bzclaw-side` for governance, seam, handoff, and synchronization rules

## Effective Rule Change

This note supersedes the older habit of keeping selection-owned root-level mirror copies inside `bzclaw-side`.

Current rule:

- do not rehydrate selection business code, templates, configs, skills, or input batches back into `bzclaw-side`
- if a B-side governance document needs to reference selection truth, use:
  - selection repo canonical paths
  - shared exchange packet refs
  - run bundle refs

## Result

- root-level owner ambiguity has been reduced
- `bzclaw-side` is back to a governance/seam posture
- the current batch-5 B-12 result remained protected throughout the prune
