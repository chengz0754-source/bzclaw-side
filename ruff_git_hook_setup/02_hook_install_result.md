# Ruff Git Hook Install Result

- Install timestamp: `2026-04-15T22:02:57+08:00`
- TARGET_REPO = `E:\bzclaw-side`
- HOOK_SCOPE = `BZCLAW_SIDE_ONLY`
- INSTALL_STATUS = `SUCCESS`

## Tool recheck

- `py -3.12 --version` -> `Python 3.12.10`
- `py -3.12 -m uv --version` -> `uv 0.11.6`
- `py -3.12 -m uv run --with ruff ruff --version` -> `ruff 0.15.10`
- `C:\Users\Administrator\.local\bin\pre-commit.exe --version` -> `pre-commit 4.5.1`
- `git --version` -> `git version 2.53.0.windows.2`

## Installed / written artifacts

- Repo config:
  - `E:\bzclaw-side\.pre-commit-config.yaml`
- Control plane:
  - `E:\bzclaw-side\ruff_git_hook_setup\install_ruff_git_hooks.ps1`
  - `E:\bzclaw-side\ruff_git_hook_setup\validate_ruff_git_hooks.ps1`
  - `E:\bzclaw-side\ruff_git_hook_setup\run_ruff_git_hook.ps1`
- Live Git hooks:
  - `E:\bzclaw-side\.git\hooks\pre-commit`
  - `E:\bzclaw-side\.git\hooks\pre-push`

## Hook behavior

- `pre-commit` blocks commit when staged Python files fail Ruff.
- `pre-push` blocks push when Python files in the pushed ref set fail Ruff.
- Both hook wrappers return non-zero on Ruff failure.
- Existing sample hooks were preserved because no live custom hooks had to be overwritten.

## Main-repo status

- `HOOK_SCOPE = BZCLAW_SIDE_ONLY`
- `MAIN_REPO_HOOK_STATUS = DEFERRED_BECAUSE_MAIN_REPO_NOT_VISIBLE`
