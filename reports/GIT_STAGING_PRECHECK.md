# GIT STAGING PRECHECK

## Precheck command basis

- `git status --short`
- `git status --short --ignored`
- `git check-ignore -v` on selected sensitive/runtime paths

## Paths that will be allowed into staging

- Root manifests:
  - `.env.example`
  - `.gitignore`
  - `README.md`
  - `package.json`
  - `requirements.txt`
- Sidecar-owned directories:
  - `configs/`
  - `scripts/`
  - `models/README.md`
  - `inputs/README.md`
  - `logs/README.md`
  - `outputs/README.md`
  - `runs/.gitkeep`
  - `playwright/auth/.gitkeep`
  - `playwright/profiles/.gitkeep`
  - `playwright/screenshots/.gitkeep`
  - `playwright/traces/.gitkeep`
  - `reports/`
  - `skills/`

## Paths correctly ignored during precheck

- `.venv/`
- `playwright/auth/storage_state.smoke.json`
- `playwright/profiles/chromium-user-data/`
- `playwright/screenshots/playwright-smoke.png`
- `playwright/traces/playwright-smoke.zip`

## Sensitive exposure assessment

- `.env` file present in repo root: `no`
- Real auth storage state staged: `no`
- Persistent automation browser profile staged: `no`
- Runtime screenshots/traces staged: `no`
- Legacy runtime artifacts under `skills/`: `not found after cleanup`

## Precheck conclusion

- Current staging surface is reviewable and consistent with the repo boundary.
- The remaining risk is procedural only: future login bootstrap artifacts must
  stay under ignored Playwright auth/profile paths.
