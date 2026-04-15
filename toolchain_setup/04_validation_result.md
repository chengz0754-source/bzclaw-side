# B Machine Toolchain Validation Result

Validation date: 2026-04-15
Machine-level validation result: `SUCCESS`

## Command validation

| Check | Command | Result |
| --- | --- | --- |
| Node.js | `node -v` | `v24.14.1` |
| pnpm | `pnpm -v` | `9.15.0` |
| Python 3.12 | `py -3.12 --version` | `Python 3.12.10` |
| uv | `uv --version` | `uv 0.11.6 (65950801c 2026-04-09 x86_64-pc-windows-msvc)` |
| ruff | `ruff --version` | `ruff 0.15.10` |
| corepack | `corepack --version` | `0.34.6` |
| uv tool inventory | `uv tool list` | `ruff v0.15.10` |
| Playwright CLI equivalent | `pnpm.cmd dlx playwright@latest --version` | `Version 1.59.1` |

## Playwright runtime evidence

- Browser cache root: `C:\Users\Administrator\AppData\Local\ms-playwright`
- Visible cache entries:
  - `.links`
  - `.settings`
  - `chromium-1208`
  - `chromium-1217`
  - `chromium_headless_shell-1208`
  - `chromium_headless_shell-1217`
  - `ffmpeg-1011`
  - `firefox-1511`
  - `webkit-2272`
  - `winldd-1007`

## Repo-level validation

- `REPO_LEVEL_VALIDATION = DEFERRED`
- `REASON = REPO_IS_NOT_PRESENT_ON_B_MACHINE`
- No repo dependency install commands were executed because no visible repo root was present on this machine

## Residual notes

- `winget` is still not available on this machine, but it was not required after the direct-download and user-scope install path succeeded.
