# Universal Git Sync Rule

## Single Recommended Entry Point

From the root of either supported repo, use exactly this command:

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\git_sync_repo_main.ps1" -StageAll
```

Supported repos:

- `E:\bzclaw-side`
- `E:\选品文件夹\amazon-selection-automation`

The script auto-detects the current repo root, current branch, and `origin`. It refuses to run outside a git repo and refuses to run on branches other than `main`.

## Required Behavior

The universal sync entrypoint now follows one shared flow in both repos:

1. confirm the current folder is the repo that owns the script
2. confirm the current branch is `main`
3. inspect unstaged, staged, and untracked state
4. if `-StageAll` is supplied, run `git add -A`
5. if staged changes exist, create a commit
6. try `git push origin main` first
7. only if push is rejected because remote history must be synced, run `git fetch origin main`, `git rebase origin/main`, and retry push

## When To Use `-StageAll`

Use `-StageAll` only when the entire current repo-visible diff is intentionally ready to commit.

Do use `-StageAll` when:

- you already reviewed `git status --short`
- every current repo-visible change belongs in the same sync
- you want one-step staging and sync from the repo root

Do not use `-StageAll` when:

- the repo contains unrelated dirty files
- you only want to submit part of the current diff
- you have local scratch work, mirrors, or report drafts that are not ready

In those cases, stage manually first and then run:

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\git_sync_repo_main.ps1"
```

## Old Script Policy

These older names remain only as compatibility wrappers:

- `scripts\git_sync_main.ps1`
- `scripts\git_sync_main.bat`
- `scripts\git_sync_bside_main.ps1`
- `scripts\git_sync_bside_main.bat`
- `scripts\git_sync_selection_main.ps1`
- `scripts\git_sync_selection_main.bat`

They are no longer the recommended entry point. They now print a deprecation warning and forward to `git_sync_repo_main.*`.

## Operator Rule

Do not paste `.bat` file contents line by line into `cmd` or PowerShell. Always execute the script file itself.
