# Market Root Orchestrator

This skill coordinates the local SellerSprite market-line root flow:

1. `Market-research*.xlsx` in the dropzone root
2. `skill-market-route-m01-to-m02`
3. validated latest `M02`
4. `skill-market-route-step1-to-step3`

It exists to keep the root dropzone clean, block stale or invalid M02 inputs,
and hand only validated upstream artifacts into Step1.

## Scope

This orchestrator is responsible for:

- scanning the root dropzone for market raw files
- running `skill-market-route-m01-to-m02`
- verifying the root is cleared of processed market raw files
- selecting only the latest manifest-approved and quality-valid `M02`
- running `skill-market-route-step1-to-step3` with explicit `--m02-file`
- writing one unified orchestrator manifest

It does not:

- replace either underlying skill
- make final product-selection decisions
- download SellerSprite data
- override Step1/Step2/Step3 config gates

## Run

From `E:\bzclaw_inputs\选品`:

```powershell
python .\skill-market-root-orchestrator\scripts\run_market_root_orchestrator.py --root .
```

Windows wrappers:

- `bat/run_market_root_orchestrator.bat`
- `ps1/run_market_root_orchestrator.ps1`

## Contracts

- The root is a temporary dropzone for `Market-research*.xlsx`
- Processed market raw files must not remain in the root after orchestration
- `M02` is never consumed from the root
- Downstream Step1 only receives one explicit validated `M02` file
- If the latest manifest-approved `M02` fails quality gates, orchestration stops
  at `M02_QUALITY_BLOCK`

## Key Quality Gates

- `seller_type_raw` shares must parse to `0~1`
- `seller_share_sum` must stay within tolerance
- `seller_share_parse_flag` must not contain `INVALID_PARSE`
- ratio fields must remain within `0~1`
- required path and market columns must exist

## Path Policy

To tighten Step1 path scope, edit:

- [path_policy.yaml](E:/bzclaw_inputs/选品/skill-market-route-step1-to-step3/configs/path_policy.yaml)

Set:

- `mode: advisory` for non-blocking path flags
- `mode: strict_include_only` to allow only whitelist matches into
  `PASS_TO_STEP2`
