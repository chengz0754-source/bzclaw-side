# Repo Bootstrap Plan

## Scope

Do not reinstall the already working machine-level toolchain unless a recheck shows breakage. Focus only on the deferred repo-level gap.

## Plan

1. Recheck `node`, `pnpm`, Python `3.12`, `uv`, `ruff`, and `corepack`.
2. Probe for a real repo root from B machine using:
   - direct local candidates such as `E:\bzclaw`, `D:\bzclaw`, `C:\bzclaw`, `F:\bzclaw`
   - common parent directories such as `repos`, `src`, `shared`, `workspace`, `projects`, `code`, and `repo`
   - any visible mapped-drive roots
   - a fallback targeted search for workspace directories `agent-kernel`, `bzclaw-console-prototype`, `bzclaw-frontend`, and `bzclaw-test`
3. If a repo root becomes visible:
   - read repo-root and workspace-root `AGENTS.md` files if present
   - install workspace dependencies with bounded `pnpm -C ... install --frozen-lockfile`
   - run `uv sync --frozen --group contract-sync --group dev --no-default-groups`
   - run `pnpm -C "$RepoRoot\bzclaw-console-prototype" exec playwright install`
   - run the required minimal validation commands
4. If no repo root is visible:
   - stop immediately
   - return only `REPO_PATH_NOT_VISIBLE_FROM_B_MACHINE`
   - recommend exposing the repo root via a shared path or mapped drive and rerunning

## Current outcome

The plan stopped at step 4 because no real repo root was visible from B machine during this run.
