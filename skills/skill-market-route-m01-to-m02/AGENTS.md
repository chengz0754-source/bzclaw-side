# Agent Rules

## Scope

This local skill handles only:

- `M01_raw_market_export -> M02_market_cleaned`

## Hard Boundaries

- Do not make a final selection decision.
- Do not rank shortlist winners.
- Do not enter competitor, profit, or launch judgment.
- Do not delete or overwrite raw input workbooks.
- Do not recurse into subdirectories unless the user explicitly changes the
  contract.

## Processing Rules

- Read only `Market-research*.xlsx` in the selected input directory.
- Treat row 1 as grouping metadata and row 2 as the true header row.
- Preserve broad or mixed parent paths; surface them in `path_summary`.
- Leave uncertain fields blank and log the uncertainty instead of guessing.
- Parse seller shares with strict percentage regex, not loose numeric matching.
- Emit `seller_share_sum` and `seller_share_parse_flag` for downstream gates.
- Fail one file independently without blocking other files in the same run.

## Output Rules

- Always emit the M02 intermediate package, not a final answer.
- Keep `keep_flag` at `REVIEW_PENDING` by default.
- Keep `next_action` at `BUILD_NICHE_SHORTLIST` by default.
- Record parse warnings in both `run_log` and `logs/`.
- Do not write processing results directly back into the root dropzone.
- Do not leave a successfully processed raw input in the root dropzone.
- Do not delete any raw input unless archive safety has already succeeded.
- Do not mix outputs from different runs into one flat output or log directory.
