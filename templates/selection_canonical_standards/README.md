# Selection Canonical Standards

This directory is the repo-internal source of truth for the selection system
standards package.

## Canonical files

- `00_高胜率精铺选品_6步自动化下推SOP_v1.md`
- `01_全量CSV字段标准说明_v1.md`
- `90_下推参数表.csv`
- `99_字段数据标准总表.csv`

## Consumption rules

- Prompts should cite these repo-local copies instead of external download paths.
- Scripts that need machine-readable standards should read:
  - `90_下推参数表.csv`
  - `99_字段数据标准总表.csv`
- `templates/selection_csv_cn_reference/00~02` are derived operator-facing
  templates aligned to these canonical standards.
- `templates/selection_csv_cn_reference/03~04` are repo-local worksheets and do
  not replace the canonical standard set above.
