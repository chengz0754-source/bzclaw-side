# B7.6 Dual Repo Gitignore Rules

## Shared Rule

Both repos already enforce the same core local-only boundary in `.gitignore`:

- `.env`
- `.venv/`
- `node_modules/`
- `__pycache__/`
- `playwright/auth/**`
- `playwright/profiles/**`
- `playwright/screenshots/**`
- `playwright/traces/**`
- `logs/**`
- `outputs/**`
- `runs/**`
- `archive/**`
- `inbox/**`

This boundary is correct for B7.6 and does not need an additional ignore-file
rewrite in this turn.

## Selection Repo

Should stay in git:

- repo-owned `README.md`
- `configs/**`
- `models/**`
- `scripts/**`
- `templates/**`
- selected repo-owned reports and contracts
- approved imported `skills/**`

Should stay local-only:

- workbook downloads under `runs/**`
- runtime logs and receipts under `logs/**`
- generated business outputs under `outputs/**`
- browser auth, profiles, screenshots, traces
- `.env`, cookies, tokens, storage state

Current status on `2026-04-11` after B7.6 file creation:

- the worktree now includes repo-owned input/template changes outside `.gitignore`
- these paths are business-visible surfaces, not runtime garbage:
  - `inputs/selection_run_current/00_*`
  - `inputs/selection_run_current/01_*`
  - `inputs/selection_run_current/01A_*`
  - new repo-visible batch/template files under `inputs/` and `templates/`
- this means the selection sync script should block until the operator scopes or
  stages those business changes deliberately
- no tracked runtime payload was observed in index
- no `git rm --cached` action is currently required

## B-side Repo

Should stay in git:

- baseline docs
- contract and envelope docs
- B business track inventories and business object maps
- Hermes governance docs
- repo-owned governance reports
- b-side sync scripts
- mirrored selection-owned repo surfaces that remain intentionally repo-visible

Should stay local-only:

- runtime `logs/**`
- runtime `outputs/**`
- runtime `runs/**`
- auth/profile/screenshot/trace payloads
- `.env`, secrets, cookies, tokens

Current status on `2026-04-11`:

- current worktree contains one untracked stray root file: `市场分析`
- that file is not in git index
- therefore no `git rm --cached` action is currently required

Handling rule:

- do not use blind `git add -A` from the repo root without checking untracked
  files first
- if this stray file is not needed, archive or delete it outside git

## Mirror Boundary

Mirror scripts may copy only repo-owned tracked files.

They must never copy:

- runtime receipts
- workbook downloads
- screenshots
- traces
- storage state
- browser profiles
- local caches

## Future Cleanup Rule

If a runtime file ever enters git by mistake:

1. add or confirm the ignore rule
2. run `git rm --cached <path>` on the exact path only
3. commit the removal
4. verify `git status --short` is clean again

No blanket destructive cleanup is authorized by this protocol.
