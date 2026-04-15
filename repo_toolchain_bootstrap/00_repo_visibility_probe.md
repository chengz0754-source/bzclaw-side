# Repo Visibility Probe

Probe date: 2026-04-15
Control root: `E:\bzclaw-side\repo_toolchain_bootstrap`

## Machine toolchain recheck

The machine-level toolchain is still present and executable. In this Codex session, the ambient non-interactive shell did not inherit the previously written user PATH entries, so the probe injected the known user-space tool directories into the process PATH before running the recheck.

Injected tool directories:

- `C:\Users\Administrator\AppData\Local\BZCLAWToolchain\node\current`
- `C:\Users\Administrator\AppData\Roaming\Python\Python312\Scripts`
- `C:\Users\Administrator\.local\bin`

Recheck results:

| Command | Result |
| --- | --- |
| `node -v` | `v24.14.1` |
| `pnpm -v` | `9.15.0` |
| `py -3.12 --version` | `Python 3.12.10` |
| `uv --version` | `uv 0.11.6 (65950801c 2026-04-09 x86_64-pc-windows-msvc)` |
| `ruff --version` | `ruff 0.15.10` |
| `corepack --version` | `0.34.6` |

## Repo visibility probe

Filesystem drives visible to B machine:

- `C:\`
- `D:\`
- `E:\`
- `F:\`

Network / mapped-drive status:

- `net use` returned `There are no entries in the list.`

Local direct candidates checked:

- `E:\bzclaw` -> not present
- `D:\bzclaw` -> not present
- `C:\bzclaw` -> not present
- `F:\bzclaw` -> not present

Common parent directories checked:

- `*\repos\bzclaw`
- `*\src\bzclaw`
- `*\shared\bzclaw`
- `*\workspace\bzclaw`
- `*\workspaces\bzclaw`
- `*\projects\bzclaw`
- `*\code\bzclaw`
- `*\repo\bzclaw`

Result:

- No visible repo candidate was found under those common local or mapped-drive patterns.

Top-level directories on visible drives matching `*bzclaw*`:

- `E:\bzclaw side`
- `E:\bzclaw-exchange`
- `E:\bzclaw-route-a-runner`
- `E:\bzclaw-side`

None of those directories contains all required repo workspaces:

- `agent-kernel`
- `bzclaw-console-prototype`
- `bzclaw-frontend`
- `bzclaw-test`

Targeted workspace-name search result:

- Only one hit was found: `E:\$RECYCLE.BIN\S-1-5-21-3660710328-2089016820-2379128882-500\$R2NRFQQ\agent-kernel`
- That path is inside the recycle bin and does not constitute a usable repo root

## Final decision

- `REPO_PATH_VISIBLE_ON_B_MACHINE = NO`
- `EXACT_BLOCKER = REPO_PATH_NOT_VISIBLE_FROM_B_MACHINE`

## Minimal unblock action

- Expose the repo root from A machine to B machine through a shared path or mapped drive
- Then rerun this prompt or rerun the scripts in this control directory
