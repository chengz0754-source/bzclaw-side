# Ruff Git Hook Validation Result

- Validation target: `E:\bzclaw-side`
- Validation status: `SUCCESS_WITH_KNOWN_REPO_DEBT`

## Existence checks

- `.git\hooks\pre-commit` exists: `YES`
- `.git\hooks\pre-push` exists: `YES`
- `ruff_git_hook_setup\run_ruff_git_hook.ps1` exists: `YES`

## Validation runs

### 1. Repo-wide framework check

- Command family:
  - `pre-commit run ruff-check --config E:\bzclaw-side\.pre-commit-config.yaml --all-files`
- Exit code: `1`
- Result:
  - Expected failure on existing repo debt, which proves Ruff is wired into the framework.
- Representative existing findings:
  - `skills\skill-market-route-step1-to-step3\scripts\run_market_route_pipeline.py` -> `E402`
  - `skills\skill-market-route-step1-to-step3\scripts\run_step1_m03.py` -> `E402`
  - `skills\skill-market-route-step1-to-step3\scripts\run_step2_benchmark.py` -> `E402`
  - `skills\skill-market-route-step1-to-step3\scripts\run_step3_keywords.py` -> `E402`, `F401`
  - `skills\skill-semantic-filter-local\scripts\run_semantic_filter.py` -> `E712`

### 2. Pre-commit manual probe

- Method:
  - Stage a temporary file under `ruff_git_hook_setup`
  - Invoke `.git\hooks\pre-commit` through Git Bash `sh.exe`
- Probe content:
  - Unused import to force Ruff `F401`
- Exit code: `1`
- Result:
  - Hook blocked the probe as expected

### 3. Pre-push manual probe

- Method:
  - Invoke `run_ruff_git_hook.ps1 -HookType pre-push -Files ruff_git_hook_setup/_ruff_hook_validation_bad.py`
- Probe content:
  - Unused import to force Ruff `F401`
- Exit code: `1`
- Result:
  - Pre-push path blocked the probe as expected

## Cleanup check

- Temporary validation probe removed: `YES`

## Exact blocker summary

- The only scope blocker is visibility of the real `bzclaw` main repo on B machine.
- Repo-wide `pre-commit run --all-files` does not pass today because `bzclaw-side` already contains historical Ruff findings.
