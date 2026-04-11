# B Git Sync Repair Note

## Scope

This note records the B7.5 Git sync repair actions for the canonical repo
`E:\bzclaw-side`.

This round only repaired sync/governance behavior. It did not change B5/B6/B7
business semantics.

## What Was Repaired

### 1. Canonical `origin` Target

Repaired from:

- `E:\bzclaw side`

Repaired to:

- `https://github.com/chengz0754-source/bzclaw-side.git`

### 2. Stable Sync Tool

Added:

- `scripts/git_sync_main.ps1`
- `scripts/git_sync_main.bat`

The PowerShell script now:

- only runs against `E:\bzclaw-side`
- checks that the current branch is `main`
- repairs `origin` automatically if it still points to the local legacy mirror
- stops when unstaged changes exist
- warns when untracked files are outside the staged set
- allows explicit `-StageAll` when the operator really wants a full add
- falls back to commit message `项目更新` when no message is provided
- commits staged changes, then attempts `pull --rebase origin main`, then
  `push origin main`

The batch wrapper exists so the operator can run one command or one file instead
of pasting batch-file internals line by line.

### 3. Staged-Set Hygiene

This round explicitly excluded:

- root stray file `市场分析`

This round kept repo-owned staged content only:

- baseline docs
- configs
- scripts
- reports
- templates
- imported skills
- B2/B3/B4/B5/B6/B7 docs

Ignored runtime-sensitive paths were verified separately and remained out of the
commit path.

## Commit Outcome

Local sync commit was created successfully:

- initial local sync commit:
  `5e6408e sync canonical sidecar repo assets and governance docs`
- rebased final sync commit on top of remote B5/B6/B7 landing commits:
  `d0ee013 sync canonical sidecar repo assets and governance docs`
- final repair-report commit:
  `78cd34f record B7.5 git sync repair diagnostics`

That proves the repaired sync tool can create a correct local commit from the
canonical repo without the earlier pathspec failure mode.

## Network-Layer Behavior During Repair

During repair, native GitHub sync was intermittently blocked by outbound HTTPS
connectivity:

- `git pull --rebase origin main` failed after the local commit
- `git ls-remote origin refs/heads/main` failed
- `curl.exe -I https://github.com` failed
- `Test-NetConnection github.com -Port 443` reported `TcpTestSucceeded=False`

Because of that transient blocker, the required B5/B6/B7 files were first
landed through the GitHub repo API fallback. After that, the local branch was
rebased onto the remote landing commits and a native shell push completed
successfully.

## Operator Usage

Recommended usage:

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File E:\bzclaw-side\scripts\git_sync_main.ps1 -CommitMessage "项目更新"
```

Or from `cmd`:

```bat
E:\bzclaw-side\scripts\git_sync_main.bat
```

If the operator really wants a full stage:

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File E:\bzclaw-side\scripts\git_sync_main.ps1 -StageAll -CommitMessage "项目更新"
```

## Current Repair Truth

After this round:

- sync invocation is fixed
- canonical `origin` is fixed
- local commit flow works
- required B5/B6/B7 files are landed on GitHub
- native shell `git push origin main` succeeded after rebase
- the observed 443 instability remains a residual network risk, not the final
  push outcome

That is the exact B7.5 repair position.
