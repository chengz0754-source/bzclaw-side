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

Local commit created successfully:

- `5e6408e sync canonical sidecar repo assets and governance docs`

That proves the repaired sync tool can create a correct local commit from the
canonical repo without the earlier pathspec failure mode.

## Network-Layer Limitation

Native GitHub network sync from shell is still blocked by this machine's current
outbound HTTPS failure:

- `git pull --rebase origin main` failed after the local commit
- `git ls-remote origin refs/heads/main` failed
- `curl.exe -I https://github.com` failed
- `Test-NetConnection github.com -Port 443` reported `TcpTestSucceeded=False`

Because of that machine-level blocker, remote landing for the required B5/B6/B7
files was completed through the GitHub repo API fallback instead of a normal
shell `git push`.

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
- required B5/B6/B7 files have been landed on GitHub through fallback
- native shell `git push` is still blocked by current machine egress to
  `github.com:443`

That is the exact B7.5 repair position.
