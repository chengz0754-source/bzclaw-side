# Skill Market Route M01 To M02

## What This Skill Does

This local skill converts SellerSprite market export workbooks from:

- `M01_raw_market_export`

into:

- `M02_market_cleaned`

It is a structure-and-cleaning stage only. It does not make a final product
decision.

## Expected Inputs

- Location: the chosen input directory only
- File pattern: `Market-research*.xlsx`
- Scan mode: non-recursive
- Each workbook is processed independently

The raw workbook is expected to contain:

- one main market data sheet
- one `Notes` sheet

On the main sheet:

- row 1 = group titles
- row 2 = actual field names
- row 3+ = data rows

## Outputs

For each run, the skill creates one unique `run_id` directory under `outputs/`.

For each input workbook in that run, the skill writes one basename into:

- `outputs/{run_id}/xlsx/`
- `outputs/{run_id}/csv/`
- `outputs/{run_id}/jsonl/`

Output file names stay in the same format:

- `M02_market_cleaned__{marketplace}__{batch_id}.xlsx`
- matching `.csv`
- matching `.jsonl`

The Excel workbook contains:

- `market_cleaned`
- `path_summary`
- `field_dictionary`
- `run_log`

## How To Run

From `E:\bzclaw_inputs\选品`:

```powershell
python .\skill-market-route-m01-to-m02\run_market_m01_to_m02.py --input-dir .
```

Optional flags:

- `--output-dir`
- `--glob`
- `--overwrite`
- `--debug`
- `--hard-delete-root-input-after-success`

Windows entrypoints:

- double-click `run_market_m01_to_m02.bat`
- or run `run_market_m01_to_m02.ps1`

The wrappers default `--input-dir` to the parent folder of this skill so they
operate on the local selection workspace instead of the skill folder itself.

## Dropzone Contract

The root folder `E:\bzclaw_inputs\选品` is a temporary input dropzone.

The runner scans only that directory level for `Market-research*.xlsx`. It does
not recurse into subdirectories and it does not use files inside the skill
folder as inputs.

## Root Cleanliness

After a file is processed, it must not remain in the root dropzone.

Default behavior:

- successful input files move to:
  - `archive/processed/{run_id}/raw_inputs/`
- failed input files move to:
  - `archive/failed/{run_id}/raw_inputs/`

This keeps the root clean without doing an irreversible hard delete by default.

The runner also never writes M02 outputs back into the root dropzone.

## Timestamped Output Contract

Each run creates a unique `run_id` like `YYYYMMDD_HHMMSS`.

All outputs, logs, manifests, and archived raw inputs for that run are grouped
under the same `run_id` tree:

- `outputs/{run_id}/...`
- `logs/{run_id}/...`
- `archive/processed/{run_id}/...`
- `archive/failed/{run_id}/...`

This prevents mixed-batch flat directories when the skill is used repeatedly.

## Run Artifacts

Each run writes:

- `outputs/{run_id}/summaries/output_index.csv`
- `logs/{run_id}/run.log`
- `logs/{run_id}/warnings.json`
- `logs/{run_id}/errors.json`
- `logs/{run_id}/run_summary__{run_id}.json`
- `archive/processed/{run_id}/manifests/run_manifest.json`

If any file fails in the run, the skill also writes:

- `archive/failed/{run_id}/manifests/run_manifest.json`

## What Gets Cleaned

- filename-derived market metadata
- market path levels
- sample counts
- seller type shares
- seller share validation fields
- seller country and share
- numeric and percentage fields
- path-level summary rows for later contraction

Seller type parsing now uses strict percentage regex extraction for:

- `FBA:\s*(\d+(?:\.\d+)?)%`
- `AMZ:\s*(\d+(?:\.\d+)?)%`
- `FBM:\s*(\d+(?:\.\d+)?)%`

The M02 output now includes:

- `seller_share_sum`
- `seller_share_parse_flag`

`seller_share_parse_flag` is:

- `OK`
- `INVALID_PARSE`
- `INVALID_SUM`

## What This Skill Does Not Do

- no final yes/no product decision
- no shortlist scoring
- no competitor judgment
- no profitability judgment
- no deletion of source files
- no automatic pruning of broad-market rows

## Optional Hard Delete

Default behavior is safe archive plus root cleanup, not hard delete.

If you explicitly need delete-style handling after archive success, use:

```powershell
python .\skill-market-route-m01-to-m02\run_market_m01_to_m02.py --input-dir . --hard-delete-root-input-after-success
```

That mode only deletes the original root input after the archive copy succeeds.
If archive fails, the source file is not deleted.

## Next Step

This skill stops at:

- `M01_raw_market_export -> M02_market_cleaned`

The standard next stage is:

- `M02_market_cleaned -> M03_niche_shortlist`

Then, for retained niches, the next collection step is to download:

- `benchmark ASIN / TOP products detail` raw tables

That later work is outside this skill.
