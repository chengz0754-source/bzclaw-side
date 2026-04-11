# CODEX Toy 10 Terms Batch Run Summary (2026-04-11)

## Current Git Truth

- Project truth stays `PURPOSE_ROUTED / PLAYWRIGHT_ONLY / SELLERSPRITE_FIRST / SIF_AFTER_SHORTLIST`.
- SellerSprite business truth still stays `SELLERSPRITE_NOT_CLOSED`.
- This slice no longer uses `claw machine` as the active selection input.
- This slice only runs `T01 / MARKET_DISCOVERY` with the 10 toy terms provided by the user.

## Why This Run No Longer Uses `claw machine`

- `claw machine` remains in repo history as `T02 / PRODUCT_IDEA_VALIDATION`, but it is not the active input for this slice.
- The active batch input is `inputs/selection_run_current/01__SELECTION_INPUT__TOY_10_TERMS_BATCH__20260411.csv`.
- The active T01 route binds:
  - `类目大类 = TOY`
  - `类目子类 = TOY_GENERAL`
  - `业务目的 = MARKET_DISCOVERY`
  - `参数模板ID = TOY_GENERAL__MARKET_DISCOVERY__V1`
- The active parameter source for this slice is `templates/category_gate_profiles/02__CATEGORY_GATE_PROFILES__TOY_V1__20260411.csv`.

## Input Intake Result

- All 10 user-provided toy terms were copied into repo-visible current input and template paths.
- The batch loader consumed exactly 10 enabled rows.
- No extra terms were injected.
- No input rows were missing during shortlist projection.

Exact input terms:

1. `Squeeze Toys`
2. `Balloons`
3. `Building Sets`
4. `Stickers`
5. `Multi-Item Party Favor Packs`
6. `Board Games`
7. `Squeak Toys`
8. `Stuffed Animals & Teddy Bears`
9. `Bubble Makers`
10. `Bath Toys`

## Run Result

### STEP3 Gate Rebuild

- Workbook input: `runs/manual/10_market/20260411_toy_10_terms_batch_support/Market-research(200)SqueezeToys-US-Last-30-days (2).xlsx`
- Output dir: `outputs/selection_runs/20260411_toy_10_terms_batch_step3/02_generated_outputs`
- Real output files:
  - `30_市场调研原始索引.csv`
  - `31_市场调研清洗结果.csv`
  - `32_市场调研下推结果.csv`
- Workbook-wide gate summary: `PASS=33 / FAIL=0 / HOLD=167`

### T01 10-Term Shortlist Projection

- Output dir: `outputs/selection_runs/20260411_toy_10_terms_batch_shortlist/02_generated_outputs`
- Real output files:
  - `T01_市场发现短名单.csv`
  - `T01_市场发现短名单.md`
  - `T01_市场发现短名单_summary.json`
- Projection summary: `YES=2 / HOLD=8 / NO=0`

Per-term final status:

| term | status | reason |
| --- | --- | --- |
| `Squeeze Toys` | `YES` | `STEP3_GATE_PASS` |
| `Balloons` | `HOLD` | `S3_MIN_AVG_PRICE:HOLD;S3_MIN_NEW_PRODUCT_RATIO:HOLD` |
| `Building Sets` | `HOLD` | `S3_MAX_BRAND_CONCENTRATION:HOLD;S3_MAX_SELLER_CONCENTRATION:HOLD` |
| `Stickers` | `HOLD` | `S3_MIN_AVG_PRICE:HOLD` |
| `Multi-Item Party Favor Packs` | `YES` | `STEP3_GATE_PASS` |
| `Board Games` | `HOLD` | `S3_MIN_NEW_PRODUCT_RATIO:HOLD;S3_MAX_BRAND_CONCENTRATION:HOLD;S3_MAX_SELLER_CONCENTRATION:HOLD` |
| `Squeak Toys` | `HOLD` | `S3_MIN_AVG_PRICE:HOLD;S3_MIN_NEW_PRODUCT_RATIO:HOLD;S3_MAX_SELLER_CONCENTRATION:HOLD` |
| `Stuffed Animals & Teddy Bears` | `HOLD` | `S3_MIN_NEW_PRODUCT_RATIO:HOLD;S3_MAX_SELLER_CONCENTRATION:HOLD` |
| `Bubble Makers` | `HOLD` | `S3_MAX_SELLER_CONCENTRATION:HOLD` |
| `Bath Toys` | `HOLD` | `S3_MIN_AVG_PRICE:HOLD;S3_MAX_SELLER_CONCENTRATION:HOLD` |

## Shortlist Result

- Final shortlist terms:
  - `Squeeze Toys`
  - `Multi-Item Party Favor Packs`
- These are the only 2 exact input terms that reached `YES` under `TOY_GENERAL__MARKET_DISCOVERY__V1`.

## Current SellerSprite Status

- SellerSprite still remains `SELLERSPRITE_NOT_CLOSED`.
- This slice advanced the current MARKET_DISCOVERY batch input and shortlist logic, but it did not claim full-chain closure.

## Next Exact Slice

- Use `Squeeze Toys` and `Multi-Item Party Favor Packs` as the next 1-2 toy terms for downstream validation.
- Keep the 10-term batch input as the current MARKET_DISCOVERY truth source for this lane.
- Do not reopen `claw machine`, replay/auth, T03/T04, or SIF in the next slice unless the scope explicitly changes.
