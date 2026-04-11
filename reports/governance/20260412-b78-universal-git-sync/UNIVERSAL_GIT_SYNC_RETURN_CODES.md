# Universal Git Sync Return Codes

`git_sync_repo_main.ps1` emits a `RESULT_CODE=` line and exits with a stable numeric code.

| Result code | Exit code | Meaning |
| --- | ---: | --- |
| `SUCCESS` | `0` | Push completed successfully. |
| `SUCCESS_WITH_NETWORK_WARNING` | `10` | Push succeeded, but remote verification hit a network warning. |
| `NO_CHANGES` | `11` | There was nothing new to commit or push. |
| `REBASE_REQUIRED` | `12` | Push was rejected and the rebase needs manual conflict resolution. |
| `UNSTAGED_BLOCK` | `13` | Unstaged or untracked changes were found and `-StageAll` was not supplied. |
| `WRONG_REPO` | `14` | The command was not run inside the git repo that owns the script. |
| `WRONG_BRANCH` | `15` | The current branch is not `main`. |
| `NETWORK_UNSTABLE` | `16` | GitHub network access failed before a confirmed successful push. |
| `PUSH_FAILED` | `17` | Git failed for a non-network, non-rebase reason. |

## Output Contract

The script prints these identifying lines before returning:

- `Repo=<repo_name>`
- `RepoRoot=<absolute_path>`
- `Branch=<branch_name>`
- `Origin=<origin_url>`

Every terminal state also prints:

- `RESULT_CODE=<status_name>`

Follow-up detail lines may include:

- `local_head=<sha>`
- `remote_head=<sha>`
- `push_output=<git_output>`
- `fetch_output=<git_output>`
- `rebase_output=<git_output>`
- `verification_output=<git_output>`

## Network Handling Rule

If `git push origin main` already succeeded, and only the later remote verification step fails because of a `443` or similar network wobble, the run must return `SUCCESS_WITH_NETWORK_WARNING`, not a full failure.
