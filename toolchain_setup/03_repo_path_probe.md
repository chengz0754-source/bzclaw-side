# B Machine Repo Path Probe

Probe date: 2026-04-15

## Result

`REPO_PATH_VISIBLE_ON_B_MACHINE = NO`

`REPO_VALIDATION_DEFERRED_BECAUSE_REPO_IS_NOT_PRESENT_ON_B_MACHINE`

## Candidate paths checked

| Path | Exists |
| --- | --- |
| `E:\bzclaw-side` | `YES` |
| `E:\bzclaw side` | `YES` |
| `E:\bzclaw` | `NO` |
| `D:\bzclaw` | `NO` |
| `C:\bzclaw` | `NO` |
| `F:\bzclaw` | `NO` |
| `E:\repos\bzclaw` | `NO` |
| `D:\repos\bzclaw` | `NO` |
| `C:\repos\bzclaw` | `NO` |
| `F:\repos\bzclaw` | `NO` |
| `E:\src\bzclaw` | `NO` |
| `D:\src\bzclaw` | `NO` |
| `C:\src\bzclaw` | `NO` |
| `F:\src\bzclaw` | `NO` |

## Interpretation

- The machine can see sidecar directories `E:\bzclaw-side` and `E:\bzclaw side`.
- The machine cannot currently see a repo root at common local or mapped-drive candidate paths.
- Because the repo is not present on B machine, repo dependency install and repo-level validation are deferred rather than failed.
