# Ads Manual Adjustment Bulk Builder

This supporting-only skill converts an approved Ads Phase1 plan into a
review-only CSV draft.

## Hard Rules

- supporting_only: true
- runtime_open_claim: false
- auto_upload: false
- requires_approval: true

## Input

- `inputs/ads_manual_adjustment/bulk_plan.example.json`

## Output

- `outputs/ads_manual_adjustment/bulk-example.csv`

## Run

```powershell
python .\scripts\ads_manual_adjustment\build_ads_bulk_file.py --input .\inputs\ads_manual_adjustment\bulk_plan.example.json --output .\outputs\ads_manual_adjustment\bulk-example.csv
```
