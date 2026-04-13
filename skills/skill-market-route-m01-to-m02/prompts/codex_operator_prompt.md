# Codex Operator Prompt

Use `skill-market-route-m01-to-m02` at
`E:\bzclaw_inputs\选品\skill-market-route-m01-to-m02` to process local
SellerSprite market export files named `Market-research*.xlsx`.

Task boundary:

- convert `M01_raw_market_export -> M02_market_cleaned`
- do not make final product judgments
- do not delete source files
- do not recurse into subdirectories unless explicitly asked

Required behavior:

- parse row 2 as headers and preserve row 1 grouping semantics
- split market path, sample counts, seller types, and seller country/share
- normalize declared percentage fields to 0 to 1 decimals
- emit workbook, csv, jsonl, `path_summary`, `field_dictionary`, `run_log`
- keep the root dropzone clean by archiving processed inputs out of the root
- create one `run_id` per execution and place outputs/logs/archive under that run
- log parse uncertainty instead of guessing

Preferred command from `E:\bzclaw_inputs\选品`:

```powershell
python .\skill-market-route-m01-to-m02\run_market_m01_to_m02.py --input-dir .
```
