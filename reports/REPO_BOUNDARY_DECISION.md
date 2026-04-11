# REPO BOUNDARY DECISION

## Decision

- Repo type: independent sidecar only
- Fixed repo root: `E:\选品文件夹\amazon-selection-automation`
- BZCLAW mainline integration in this round: `disabled`

## In-bound paths

- Root docs and manifests:
  - `README.md`
  - `.gitignore`
  - `.env.example`
  - `package.json`
  - `requirements.txt`
- Owned source and config paths:
  - `configs/`
  - `scripts/`
  - `models/`
  - `inputs/README.md`
  - `logs/README.md`
  - `outputs/README.md`
  - `runs/.gitkeep`
  - `playwright/*/.gitkeep`
  - `reports/`
- Imported legacy code/config/docs only:
  - `skills/skill-market-route-m01-to-m02/`
  - `skills/skill-market-route-step1-to-step3/`
  - `skills/skill-market-root-orchestrator/`
  - `skills/skill-semantic-filter-local/`

## Out-of-bound paths

- Any path outside `E:\选品文件夹\amazon-selection-automation`
- All legacy source roots under `E:\选品\skill-*` as original working trees
- Runtime-only paths and sensitive state:
  - `.venv/`
  - `.env`
  - `playwright/auth/storage_state*.json`
  - `playwright/profiles/**`
  - `playwright/screenshots/**`
  - `playwright/traces/**`
  - `logs/**` except `logs/README.md`
  - `outputs/**` except `outputs/README.md`
  - `runs/**` except `runs/.gitkeep`
  - any `archive/**`
  - any `inbox/**`
  - any `__pycache__/`
  - any `*.pyc`

## Boundary notes

- Legacy `skill-*` content is imported as copied source material under
  `skills/`; the original directories remain external references.
- This repo is intentionally code/config/docs-first. Runtime artifacts and
  auth-bearing paths are excluded even if they were produced by this same
  workspace.
