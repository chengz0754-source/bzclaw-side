# Universal Git Sync Fallback Commands

## Default Command

Preferred one-step command from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\git_sync_repo_main.ps1" -StageAll
```

If you already staged the exact intended changes, run without `-StageAll`:

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\git_sync_repo_main.ps1"
```

## Manual Staging Flow

Use this when the repo contains unrelated dirty files and you must stage only a subset:

```powershell
git status --short
git add <path1> <path2>
powershell -ExecutionPolicy Bypass -File ".\scripts\git_sync_repo_main.ps1" -CommitMessage "项目更新"
```

## Manual Recovery For `REBASE_REQUIRED`

If the script returns `REBASE_REQUIRED`, inspect and resolve the conflicts first:

```powershell
git status
git rebase --continue
```

If you decide to abort the conflicted rebase instead:

```powershell
git rebase --abort
```

After the worktree is clean again, rerun the universal sync script.

## Manual Recovery For `NETWORK_UNSTABLE`

When GitHub connectivity is unstable, verify the route first:

```powershell
Test-NetConnection github.com -Port 443
git ls-remote origin
```

If the network path looks healthy again, rerun:

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\git_sync_repo_main.ps1"
```

## Manual Sync Sequence

Only use these when you intentionally need to walk the git steps yourself:

```powershell
git push origin main
git fetch origin main
git rebase origin/main
git push origin main
```

This manual path is only for diagnosis or conflict handling. The normal operator path stays the universal script.

## Prohibited Operator Pattern

Do not open a `.bat` file and paste its lines one by one into `cmd` or PowerShell. That was the original failure mode and is no longer an approved workflow.
