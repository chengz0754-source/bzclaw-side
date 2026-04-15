# B Machine Toolchain Install Result

Install date: 2026-04-15
Overall toolchain result: `SUCCESS`

## Installed or repaired components

| Component | Result | Version | Install location / note |
| --- | --- | --- | --- |
| Node.js | Installed | `v24.14.1` | `C:\Users\Administrator\AppData\Local\BZCLAWToolchain\node\current` |
| pnpm | Activated via corepack | `9.15.0` | shim under the Node install above |
| Python 3.12 | Reused existing install | `Python 3.12.10` | existing machine install |
| uv | Installed in Python user scripts | `0.11.6` | `C:\Users\Administrator\AppData\Roaming\Python\Python312\Scripts\uv.exe` |
| ruff | Installed via `uv tool` | `0.15.10` | `C:\Users\Administrator\.local\bin\ruff.exe` |
| Playwright runtime | Installed | `Version 1.59.1` | browser cache under `C:\Users\Administrator\AppData\Local\ms-playwright` |

## Important repair events

1. Initial script execution failed because PowerShell local script execution was blocked by the default effective policy.
   Actual command: `& E:\bzclaw-side\toolchain_setup\install_or_repair_toolchain.ps1`
   Error summary: `running scripts is disabled on this system`
   Resolution: first reran with `powershell -ExecutionPolicy Bypass -File ...`, then set `CurrentUser` execution policy to `RemoteSigned` so local scripts and the `pnpm` PowerShell shim are usable going forward.
2. Initial `corepack prepare pnpm@9.15.0 --activate` failed even though the registry was reachable from PowerShell.
   Actual command: `corepack prepare pnpm@9.15.0 --activate`
   Error summary: Node fetch timed out on IPv6 while requesting `https://registry.npmjs.org/pnpm/-/pnpm-9.15.0.tgz`
   Reproducibility: reproducible before the fix from Node-side fetches
   Resolution: added `NODE_OPTIONS=--dns-result-order=ipv4first` to the control scripts, then reran successfully

## User-scope persistence applied

- `HKCU\Environment\Path` now includes:
  - `C:\Users\Administrator\.local\bin`
  - `C:\Users\Administrator\AppData\Roaming\Python\Python312\Scripts`
  - `C:\Users\Administrator\AppData\Local\BZCLAWToolchain\node\current`
- `CurrentUser` PowerShell execution policy set to `RemoteSigned`

## Git install status

- Not installed
- Intentionally skipped per request
