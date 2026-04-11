# BOOTSTRAP DECISION

## Decision

- Selected mode: `VERIFY_AND_BOOTSTRAP`

## Why Not VERIFY_ONLY

- The required target workspace did not exist before this run.
- No dedicated sidecar config/env/report skeleton existed under the required
  root.
- No Playwright runtime was ready before bootstrap.

## Why Not FULL_BOOTSTRAP

- Machine B already had meaningful reusable selection assets outside the target
  root:
  - SellerSprite-related scripts
  - historical export workbooks
  - logs and outputs
  - a legacy Python environment
  - local Ollama entry with an installed model

## Bootstrap Scope Executed

- Created the dedicated sidecar workspace under `E:\选品文件夹`
- Added baseline docs, configs, and ignore rules
- Fixed input/output/log/report/model/playwright paths
- Created an isolated `.venv`
- Installed minimal Python dependencies for the sidecar
- Installed Playwright Chromium payload
- Ran Python smoke
- Ran Playwright smoke
- Probed local Ollama API entry

## Explicit Non-Claims

- No claim of full selection-chain completion
- No claim of SellerSprite live export automation completion
- No claim of SIF automation completion
- No claim of authenticated login state readiness
- No modification of BZCLAW mainline state
