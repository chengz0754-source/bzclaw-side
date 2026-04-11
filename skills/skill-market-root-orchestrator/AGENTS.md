# Agent Rules For Market Root Orchestrator

## Scope

- Coordinate `skill-market-route-m01-to-m02`
- Validate and select the newest approved `M02`
- Coordinate `skill-market-route-step1-to-step3`

## Hard Rules

- Do not rebuild either underlying skill
- Do not consume stale or unvalidated `M02`
- Do not continue to Step1 when `M02_QUALITY_BLOCK` is active
- Do not leave processed market raw files in the root dropzone
- Do not write outputs back into the root dropzone

## Data Rules

- Seller-share parsing must be validated before Step1
- Use manifest-approved upstream files only
- Keep orchestration decisions file-based and deterministic

## Boundary

- Do not make final selection decisions
- Do not download raw evidence
- Do not bypass Step1/Step2/Step3 config gates
