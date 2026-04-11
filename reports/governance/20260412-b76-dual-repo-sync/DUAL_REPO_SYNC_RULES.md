# B7.6 Dual Repo Sync Rules

## Scope

This protocol keeps two git repos separate while allowing repeatable sync:

- selection business-flow repo:
  `E:\选品文件夹\amazon-selection-automation`
- B-side governance/seam repo:
  `E:\bzclaw-side`

This is not a repo merge protocol.

## Canonical Rule

- business execution code and flow-facing repo assets are owned by the selection repo
- governance, baseline, intake, envelope, Hermes, and handoff docs are owned by
  `E:\bzclaw-side`
- if the same repo-owned file family appears in both repos, only one repo is the
  canonical owner and the other copy is an explicit mirror

## Repo-Specific Push Commands

### Selection repo

Use one of:

- `scripts\git_sync_selection_main.ps1`
- `scripts\git_sync_selection_main.bat`

Behavior:

- runs only inside `E:\选品文件夹\amazon-selection-automation`
- requires branch `main`
- requires origin
  `https://github.com/chengz0754-source/amazon-selection-automation.git`
- blocks on unstaged changes before pull/rebase
- allows empty commit message and falls back to `项目更新`
- pushes only to `origin main`

### B-side repo

Use one of:

- `scripts\git_sync_bside_main.ps1`
- `scripts\git_sync_bside_main.bat`

Behavior:

- runs only inside `E:\bzclaw-side`
- requires branch `main`
- requires origin `https://github.com/chengz0754-source/bzclaw-side.git`
- repairs the known legacy-local-origin case
  `E:\bzclaw side -> GitHub`
- blocks on unstaged changes before pull/rebase
- allows empty commit message and falls back to `项目更新`
- pushes only to `origin main`

Legacy compatibility:

- `scripts\git_sync_main.ps1`
- `scripts\git_sync_main.bat`

These now forward to the new b-side-specific script names.

## Mirror Protocol

### A. Selection-owned mirrored reference surfaces -> b-side

Canonical owner:

- `E:\选品文件夹\amazon-selection-automation`

Mirror target:

- `E:\bzclaw-side`

Mirror command:

- `scripts\export_b_repo_docs_to_bzclaw_side.ps1`

Current allowlist:

- `README.md`
- `package.json`
- `requirements.txt`
- `configs/**`
- `models/**`
- `scripts/**`
- `templates/**`
- `skills/**`

Rules:

- edit selection repo first
- run the export script second
- review the diff in `E:\bzclaw-side`
- commit and push selection repo as the owner repo
- commit and push b-side mirror copy separately
- never include runtime folders in the export

Interpretation:

- the mirrored root-level copy inside `E:\bzclaw-side` is reference-only
- it must not become a second independently evolving business-code owner

### B. B-side governance docs -> selection governance mirror

Canonical owner:

- `E:\bzclaw-side`

Mirror target:

- `E:\选品文件夹\amazon-selection-automation\reports\governance\20260412-b76-dual-repo-sync\`

Mirror command:

- `scripts\export_bside_governance_docs_to_selection_repo.ps1`

Mirrored files:

- `B_CANONICAL_FOLDER_DECISION.md`
- `DUAL_REPO_OWNERSHIP_MAP.csv`
- `DUAL_REPO_SYNC_RULES.md`
- `DUAL_REPO_GITIGNORE_RULES.md`

Rules:

- edit b-side governance docs first
- run the governance export second
- review the diff in the selection repo governance folder
- commit and push b-side first
- commit and push the selection mirror second

## No-Mirror Rule

Never mirror these surfaces between repos:

- `logs/**`
- `outputs/**`
- `runs/**`
- `playwright/auth/**`
- `playwright/profiles/**`
- `playwright/screenshots/**`
- `playwright/traces/**`
- `.env`
- cookies, tokens, storage state, workbook downloads, cache, inbox, archive

## Recommended Operator Sequence

### When changing business execution code

1. Edit the selection repo.
2. Run selection-local tests or validation as needed.
3. If the changed surface must remain repo-visible in b-side, run
   `scripts\export_b_repo_docs_to_bzclaw_side.ps1`.
4. Review diffs in both repos.
5. Push selection repo with `git_sync_selection_main`.
6. Push b-side mirror copy with `git_sync_bside_main`.

### When changing B-side governance docs

1. Edit `E:\bzclaw-side`.
2. Run `scripts\export_bside_governance_docs_to_selection_repo.ps1`.
3. Review diffs in both repos.
4. Push `E:\bzclaw-side`.
5. Push selection governance mirror.

## Closed Boundary

After this protocol:

- business continues to run in the selection repo
- B-side governance and seam docs continue to land in `E:\bzclaw-side`
- shared repo-visible surfaces have one canonical owner and one explicit mirror
- no future prompt should treat `E:\bzclaw side` as an active repo root
