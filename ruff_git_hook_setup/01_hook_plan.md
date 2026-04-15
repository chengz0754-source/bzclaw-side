# Ruff Git Hook Plan

## Selected strategy

Use a hybrid setup:

1. Add a minimal repo-level `.pre-commit-config.yaml`.
2. Install stable `pre-commit` once with `py -3.12 -m uv tool install pre-commit`.
3. Write thin Git hook wrappers at:
   - `.git\hooks\pre-commit`
   - `.git\hooks\pre-push`
4. Route both wrappers into `ruff_git_hook_setup\run_ruff_git_hook.ps1`.

## Why this strategy

- `ruff` and `uv` were not directly on the current PowerShell `PATH`, so the runner uses explicit, repeatable entrypoints.
- The repo has no existing `.pre-commit-config.yaml`, so a minimal local config was safer than assuming a prior hook framework.
- `pre-commit install` from an ephemeral `uv run --with pre-commit ...` environment would risk baking a cache-specific interpreter path into `.git\hooks`.
- The repo already contains historical Ruff violations, so `pre-push` was designed to inspect only Python files relevant to the current push payload instead of forcing an immediate all-repo cleanup.

## Effective commands

- Ruff hook entry in `.pre-commit-config.yaml`:
  - `py -3.12 -m uv run --with ruff ruff check --force-exclude`
- Hook runtime wrapper:
  - Prefer `C:\Users\Administrator\.local\bin\pre-commit.exe`
  - Fallback to `py -3.12 -m uv run --with pre-commit pre-commit`
- Pre-commit scope:
  - Staged `.py` / `.pyi` files only
- Pre-push scope:
  - Python files derived from the refs passed to the Git `pre-push` hook
- Excluded path families:
  - `node_modules`
  - `.next`
  - `playwright-report`
  - `test-results`
  - `.venv*`
  - `.pnpm-store`
