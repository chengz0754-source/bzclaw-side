# B7.6 Canonical Folder Decision

## Scope

This note closes the duplicate-folder ambiguity between:

- `E:\bzclaw-side`
- `E:\bzclaw side`

Decision date:

- `2026-04-11`

## Evidence

### `E:\bzclaw-side`

- git top-level path resolves to `E:\bzclaw-side`
- `.git/config` points `origin` to
  `https://github.com/chengz0754-source/bzclaw-side.git`
- `.git/config` contains `[branch "main"]` tracking metadata
- local `HEAD` is `f9d17853cc6b2170046d1706e123d2934440ebfb`
- recent local-only commit beyond the duplicate path is:
  `f9d1785 finalize B7.5 remote sync report`
- tracked-file count observed in git is `231`
- working tree contains one untracked stray root file:
  `市场分析`

### `E:\bzclaw side`

- git top-level path resolves to `E:\bzclaw side`
- `.git/config` points `origin` to the same GitHub repo
- `.git/config` does not contain `[branch "main"]` tracking metadata
- local `HEAD` is `78cd34f9daffff590f9f14571c38535a3a6071ab`
- tracked-file count observed in git is also `231`
- working tree is clean
- no extra tracked source value beyond `E:\bzclaw-side` was observed

### Delta

- `E:\bzclaw-side` is one local commit ahead of `E:\bzclaw side`
- the only observed ahead delta is the finalized B7.5 follow-up report set
- no additional unique tracked source files were found in `E:\bzclaw side`

## Decision

Canonical B repo:

- `E:\bzclaw-side`

Historical / misnamed duplicate:

- `E:\bzclaw side`

Reason:

- it is the path already frozen by B1 baseline materials
- it has the newest local `HEAD`
- it carries the current branch-tracking metadata
- it is the repo root that later B prompts should target

## Deletion Recommendation

`E:\bzclaw side` should not remain an actively used sibling repo.

Recommended sequence:

1. Confirm no user-only loose files need to be copied out.
2. Optionally create a zip backup or rename it to an archive label.
3. Delete `E:\bzclaw side` after the backup check passes.

Current safety judgment:

- deleting `E:\bzclaw side` after backup should not change current git truth
- current git truth already lives in `E:\bzclaw-side` plus its GitHub remote
- future prompts should stop using `E:\bzclaw side` as an execution root
