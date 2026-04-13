# Ads Manual Adjustment Materializer

This supporting-only skill renders operator-facing artifacts from curated Ads
Phase1 payloads.

## Hard Rules

- supporting_only: true
- runtime_open_claim: false
- auto_upload: false
- requires_approval: true

## Inputs

- `inputs/ads_manual_adjustment/context_pack_request.example.json`
- `inputs/ads_manual_adjustment/decision_payload.example.json`

## Outputs

- `reports/ads_manual_adjustment/context-pack-example.md`
- `reports/ads_manual_adjustment/context-pack-example.manifest.json`
- `reports/ads_manual_adjustment/decision-sheet-example.md`

## Run

```powershell
python .\scripts\ads_manual_adjustment\build_ads_context_pack.py --input .\inputs\ads_manual_adjustment\context_pack_request.example.json --output-md .\reports\ads_manual_adjustment\context-pack-example.md --output-manifest .\reports\ads_manual_adjustment\context-pack-example.manifest.json
python .\scripts\ads_manual_adjustment\render_ads_decision_sheet.py --input .\inputs\ads_manual_adjustment\decision_payload.example.json --output .\reports\ads_manual_adjustment\decision-sheet-example.md
```
