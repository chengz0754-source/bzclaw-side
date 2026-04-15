# Ruff Git Hook Repo Probe

- Timestamp: `2026-04-15T22:02:57+08:00`
- MAIN_REPO_VISIBLE = `NO`
- SIDE_REPO_VISIBLE = `YES`
- SELECTED_HOOK_TARGET = `E:\bzclaw-side`
- HOOK_SCOPE = `BZCLAW_SIDE_ONLY`
- MAIN_REPO_HOOK_STATUS = `DEFERRED_BECAUSE_MAIN_REPO_NOT_VISIBLE`

## Main repo probe

| Candidate path | Exists | Git worktree | Notes |
| --- | --- | --- | --- |
| `E:\bzclaw` | No | No | Standard main-repo candidate not present |
| `D:\bzclaw` | No | No | Standard main-repo candidate not present |
| `C:\bzclaw` | No | No | Standard main-repo candidate not present |
| `F:\bzclaw` | No | No | Standard main-repo candidate not present |

## Side repo probe

| Candidate path | Exists | Git worktree | Notes |
| --- | --- | --- | --- |
| `E:\bzclaw-side` | Yes | Yes | `origin=https://github.com/chengz0754-source/bzclaw-side.git` |
| `E:\bzclaw side` | Yes | Yes | Also points to `chengz0754-source/bzclaw-side` |
| `E:\bzclaw-exchange` | Yes | No | Current shell cwd, but not the target Git repo |

## Final selection

The true `bzclaw` main repo is not visible on this B machine under the required probe set, so hook installation was intentionally limited to the visible side repo at `E:\bzclaw-side`.
