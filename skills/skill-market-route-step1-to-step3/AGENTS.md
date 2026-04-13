# Agent Rules For SellerSprite Market Route Step1 To Step3

## Scope Boundary

- Only advance `M02_market_cleaned` through `K02_keyword_shortlist`
- Do not cross into SIF
- Do not make final launch or product decisions
- Do not make final profit, supply-chain, or IP rulings

## Data Boundary

- Do not invent missing raw evidence
- Do not synthesize benchmark ASIN data
- Do not synthesize keyword data
- Do not delete raw evidence files
- Do not consume stale or unvalidated M02 inputs when an explicit validated
  `--m02-file` is available

## Decision Boundary

- Step advancement must be based on file data, status fields, hard gates, window checks, quantiles, and score weights
- All thresholds must come from config
- LLM use is limited to text normalization, path labeling assistance, anomaly explanation, and keyword semantic labeling support
- LLM output must not override config gates

## File Boundary

- Do not write outputs outside this skill directory
- Do not write result files back into the root dropzone
- Do not mix different pipeline runs into one flat folder
- Do not overwrite existing outputs unless `--overwrite` is explicit

## State Boundary

- Persist statuses to tables and manifests
- If the next raw table is missing, write queue files and stop in `WAIT_*`
- Do not skip from Step1 directly to final decision states
- In `strict_include_only` path policy mode, drop non-whitelisted paths with
  `DROP__PATH_POLICY`

## Evidence Boundary

- Keep `DROP` rows in outputs with reasons
- Keep `REVIEW_BUFFER` rows visible
- Do not silently filter away data-quality failures
