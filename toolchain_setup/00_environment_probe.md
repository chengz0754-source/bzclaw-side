# B Machine Toolchain Environment Probe

Probe date: 2026-04-15
Control root: `E:\bzclaw-side\toolchain_setup`
Working directory during setup: `E:\bzclaw side`
Normalized sidecar control directory: `E:\bzclaw-side`

## AGENTS.md scope check

- `E:\bzclaw-side\AGENTS.md`: not present
- Visible repo-root `AGENTS.md`: not present because no repo root was visible on this machine
- Smaller `AGENTS.md` files were only found under `E:\bzclaw-side\skills\...`; they are outside the `toolchain_setup` write scope for this task

## Pre-install probe result

| Item | Command | Status | Raw result |
| --- | --- | --- | --- |
| Node.js | `node -v` | Missing | `node` was not recognized |
| pnpm | `pnpm -v` | Missing | `pnpm` was not recognized |
| Python 3.12 | `py -3.12 --version` | Existing and compliant | `Python 3.12.10` |
| uv | `uv --version` | Missing | `uv` was not recognized |
| ruff | `ruff --version` | Missing | `ruff` was not recognized |
| winget | `winget --version` | Missing | `winget` was not recognized |
| Playwright CLI | `playwright --version` | Missing | `playwright` was not recognized |
| `bzclaw-side` control directory | filesystem probe | Existing | `E:\bzclaw-side` present |
| `bzclaw side` working directory | filesystem probe | Existing | `E:\bzclaw side` present |

## Immediate conclusions

- B machine already had usable Python `3.12`.
- B machine did not have usable Node, pnpm, uv, ruff, winget, or Playwright CLI at probe time.
- Repo-level validation had to be decided by a separate repo path probe instead of assuming `E:\bzclaw` exists.
