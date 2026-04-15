# B Machine Toolchain Install Plan

## Goal

Install or repair the B-machine toolchain required for BZCLAW:

- Node.js `>=24`
- `pnpm@9.15.0`
- Python `3.12`
- `uv`
- `ruff`
- Playwright runtime and browser cache

Repo-level dependency install and validation will run only if a real repo path becomes visible on B machine.

## Chosen methods

1. Keep the existing Python `3.12.10`; do not replace it because it already satisfies the requirement.
2. Install Node.js by downloading the official `latest-v24.x` Windows x64 zip from `nodejs.org` and extracting it into user space at `C:\Users\Administrator\AppData\Local\BZCLAWToolchain\node\current`.
3. Use bundled `corepack` from that Node install to activate `pnpm@9.15.0`.
4. Install `uv` into the Python 3.12 user environment with `py -3.12 -m pip install --user --upgrade uv`.
5. Install `ruff` with `uv tool install ruff@latest`.
6. Install Playwright runtime with `pnpm dlx playwright@latest install` so browser binaries are cached even when no repo is present.
7. Persist usable PATH entries at the user level for:
   - `C:\Users\Administrator\AppData\Local\BZCLAWToolchain\node\current`
   - `C:\Users\Administrator\AppData\Roaming\Python\Python312\Scripts`
   - `C:\Users\Administrator\.local\bin`
8. If PowerShell local script policy blocks tool shims, set `CurrentUser` execution policy to `RemoteSigned` because this is a user-scope unblock and does not require admin rights.
9. If Node network fetches prefer broken IPv6 routes, force `NODE_OPTIONS=--dns-result-order=ipv4first` inside the control scripts.
10. If repo stays invisible on B machine, record `REPO_VALIDATION_DEFERRED_BECAUSE_REPO_IS_NOT_PRESENT_ON_B_MACHINE` instead of treating that as a failure.

## Explicit non-goals

- No Git installation
- No business-code changes
- No authority/current/governance rewrites
- No A-line / P-line feature work
