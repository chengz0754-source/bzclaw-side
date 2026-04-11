# B Git Upload Root Cause

## Scope

This note records the root-cause diagnosis for the canonical B-side repo at
`E:\bzclaw-side`.

The target question was not business logic. The target question was why B-line
repo-owned outputs were not reliably landing on GitHub.

## Diagnostic Snapshot

Observed local Git state before repair:

- `git remote -v`
  - `origin E:\bzclaw side (fetch)`
  - `origin E:\bzclaw side (push)`
- `git branch --show-current`
  - `main`
- `git log --oneline -n 10`
  - only local commit visible then was `25c6443 init: first upload`
- `git config --get core.autocrlf`
  - `true`

Observed repo state:

- current worktree held a large staged set of repo-owned files
- forbidden runtime payloads were not the main problem
- one stray untracked zero-byte root file `市场分析` was present and excluded from
  the staged set

Ignore-rule verification:

- `playwright/auth/**`, `playwright/profiles/**`, `playwright/screenshots/**`,
  `playwright/traces/**`, `logs/**`, `outputs/**`, and `runs/**` were confirmed
  ignored by `.gitignore`
- this means the current upload failure was not primarily caused by missing
  ignore coverage for auth/profile/screenshots/traces/download outputs

## Root-Cause Classification

### 1. Script Invocation Error

Category:

- local command invocation error

Direct cause:

- the screenshot-described failures such as `pathspec 'set' did not match` and
  `pathspec 'COMMIT_MSG=项目更新' did not match` are consistent with batch-file
  lines being pasted into `cmd` or another shell line by line
- in that failure mode, `set / if / echo` fragments become extra arguments to
  `git commit`, and Git interprets them as pathspecs instead of commit-message
  logic

Judgment:

- Git itself was not broken
- the interactive execution method was wrong

### 2. Canonical Repo Remote Misconfiguration

Category:

- remote-target misconfiguration

Direct cause:

- `E:\bzclaw-side` had `origin` pointing to the old local path
  `E:\bzclaw side`
- the old local path itself pointed to the real GitHub repo
  `https://github.com/chengz0754-source/bzclaw-side.git`
- this created a misleading state where canonical B looked like it had a remote,
  but the remote was actually a local mirror hop

Judgment:

- even a successful local push in that state would not necessarily prove GitHub
  alignment

### 3. Dirty-Tree Pull/Rebase Sensitivity

Category:

- normal Git safety behavior

Direct cause:

- `git pull --rebase` is expected to stop when unstaged changes exist
- before the first repaired sync run, `scripts/archive_selection_run_io.py` and
  `scripts/run_nightly_selection_acceptance.py` still had unstaged modifications

Judgment:

- this was not an abnormal Git bug
- the sync script needed to check and stop before rebase on a dirty worktree

### 4. Network Egress Instability To GitHub

Category:

- machine network / transport instability

Direct cause:

- after `origin` was corrected to GitHub and a local commit was created, native
  `git pull --rebase origin main` and `git ls-remote origin` initially failed
- `curl.exe -I https://github.com` failed
- `Test-NetConnection github.com -Port 443` returned `TcpTestSucceeded: False`

Judgment:

- this was the blocker for native shell-based sync in the middle of repair
- it was separate from the earlier pathspec/script misuse problem
- connectivity later recovered enough to complete a normal rebase and push

## Final Diagnosis

The upload problem was a compound issue, not a single bug:

1. batch/script content was being invoked the wrong way
2. canonical `origin` was mispointed to a local mirror path
3. rebase safety would correctly stop on dirty files
4. outbound access to `github.com:443` was unstable during repair

## What It Was Not

It was not primarily:

- a broken Git install
- a broken commit engine
- a missing branch
- a missing `.gitignore` for auth/profile/screenshots/traces/download outputs
- a business-logic failure inside B5/B6/B7

## Repair Position

Current repair truth after this round:

- command-path misuse has been addressed with a reusable sync script
- `origin` has been corrected to the GitHub URL
- local commit creation works
- the required B5/B6/B7 files were first landed through a GitHub repo API
  fallback while shell sync was unstable
- after rebasing the local sync commits onto those remote landing commits,
  native `git push origin main` succeeded

Remaining risk:

- outbound connectivity to `github.com:443` was unstable during repair and may
  need recheck if a future sync stalls again
- one root stray file `市场分析` remains untracked locally and should stay out of
  future staged sets

That is the correct root-cause baseline for future B-line sync work.
