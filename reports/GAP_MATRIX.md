# GAP MATRIX

| Category | Survey Before Bootstrap | State After This Run | Gap / Risk |
| --- | --- | --- | --- |
| Path / directory | `E:\选品文件夹` did not exist. No sidecar project root. | Target root and sidecar project created. Inputs, outputs, logs, reports, runs, Playwright, scripts, configs, models all fixed. | None for baseline structure. |
| Node / Playwright | No `node`, `npm`, or `pnpm` on PATH. No Playwright CLI. No Playwright browsers. | Python Playwright `1.58.0` installed in sidecar `.venv`. Chromium payload installed. Playwright smoke passed. | JS/Node toolchain still missing. If future route requires npm-based tooling, Node must be installed later. |
| Python | System Python existed. Legacy `.venv` existed, but without Playwright. | Sidecar `.venv` created and verified. Python smoke passed. | None for Python baseline. |
| Browser / profile / auth | Chrome and Edge existed, but no dedicated automation profile or sidecar auth state. | Dedicated persistent profile path created and used. Smoke storage state path created. | No real logged-in state yet. Current storage state is empty and not reusable for business login. |
| SellerSprite | Legacy scripts, logs, outputs, and historical `Market-research*.xlsx` export evidence existed under `E:\选品`. | Reuse points documented and target-side paths fixed. | No live SellerSprite login/export automation verified from the new sidecar. |
| SIF | No dedicated SIF automation script or artifact file was found. Only boundary mentions existed in legacy docs. | Scope kept explicit in configs/docs. | Still missing real SIF automation baseline and auth strategy. |
| Model call placement | Local Ollama executable and model existed, but no dedicated sidecar config slot. | `configs/model.json`, `.env.example`, and `models/README.md` now fix the model entry point. Ollama API probe passed for `qwen3:4b-instruct`. | Business-level model calls are still placeholders, not a validated selection workflow. |
| Config files | No dedicated target-side config tree. | `configs/system.json`, `configs/paths.json`, and `configs/model.json` created. | None for baseline config placement. |
| Logs / reports | Legacy logs existed only in external asset directories. No dedicated sidecar reports. | Sidecar `logs/` and `reports/` fixed. Baseline, inventory, decision, smoke, and next-action reports created. | None for baseline reporting. |
| Security / sensitive isolation | No dedicated sidecar auth path. Default Chrome profile existed and would have been risky to reuse. | `playwright/auth` and `playwright/profiles` isolated and ignored by `.gitignore`. README documents non-git policy for auth. | Real future login state will still require operator caution and must remain out of git. |
