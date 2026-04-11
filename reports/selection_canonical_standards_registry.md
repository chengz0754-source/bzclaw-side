# Selection Canonical Standards Registry

## Upstream gate

- P01 closure verified at `reports/selection_folder_preflight_closure.md`
- Current upstream status: `READY_FOR_FORMAL_IMPLEMENTATION`
- This registry is valid only because the repo already passed the P01 preflight gate.

## Canonical source-of-truth rule

- Repo-internal canonical standards live only in `templates/selection_canonical_standards/`.
- When the repo copy exists, prompts and scripts must not treat download-folder copies or report excerpts as the source of truth.
- Machine-readable standard control surfaces are:
  - `templates/selection_canonical_standards/90_下推参数表.csv`
  - `templates/selection_canonical_standards/99_字段数据标准总表.csv`

## Registry

| registry_id | layer | artifact | repo_path | canonical | scripts_may_read_directly | derived_from | role |
| --- | --- | --- | --- | --- | --- | --- | --- |
| STD_00 | canonical_standard | SOP | `templates/selection_canonical_standards/00_高胜率精铺选品_6步自动化下推SOP_v1.md` | YES | NO | external P02 package | Human-readable process contract |
| STD_01 | canonical_standard | field_spec_doc | `templates/selection_canonical_standards/01_全量CSV字段标准说明_v1.md` | YES | NO | external P02 package | Human-readable field contract |
| STD_90 | canonical_standard | pushdown_parameter_table | `templates/selection_canonical_standards/90_下推参数表.csv` | YES | YES | external P02 package | Machine-readable rule and threshold source |
| STD_99 | canonical_standard | field_data_master | `templates/selection_canonical_standards/99_字段数据标准总表.csv` | YES | YES | external P02 package | Machine-readable field master |
| TPL_00 | template_layer | current_run_goal_template | `templates/selection_csv_cn_reference/00_选品运行目标与边界.csv` | DERIVED | LIMITED | `STD_01` + `STD_99` | Operator-facing template |
| TPL_01 | template_layer | market_entry_template | `templates/selection_csv_cn_reference/01_市场入口与筛选参数.csv` | DERIVED | LIMITED | `STD_01` + `STD_99` | Operator-facing template |
| TPL_02 | template_layer | compliance_precheck_template | `templates/selection_csv_cn_reference/02_账号与合规预检查.csv` | DERIVED | LIMITED | `STD_01` + `STD_99` | Operator-facing template |
| TPL_03 | template_layer | intermediate_candidate_pool_template | `templates/selection_csv_cn_reference/03_候选市场与候选品初筛池.csv` | NO | LIMITED | repo-local workflow contract | Intermediate candidate-sample worksheet before manual day-phase |
| TPL_04 | template_layer | post_cost_template | `templates/selection_csv_cn_reference/04_供应链询价与利润核算.csv` | NO | LIMITED | repo-local workflow contract | Post-cost manual worksheet |
| CUR_00 | current_input | live_working_copy | `inputs/selection_run_current/00_选品运行目标与边界.csv` | RUN_SCOPED | YES | `TPL_00` | Current working input |
| CUR_01 | current_input | live_working_copy | `inputs/selection_run_current/01_市场入口与筛选参数.csv` | RUN_SCOPED | YES | `TPL_01` | Current working input |
| CUR_02 | current_input | live_working_copy | `inputs/selection_run_current/02_账号与合规预检查.csv` | RUN_SCOPED | YES | `TPL_02` | Current working input |
| CUR_03 | current_input | live_working_copy | `inputs/selection_run_current/03_候选市场与候选品初筛池.csv` | RUN_SCOPED | YES | `TPL_03` + candidate-pool runtime sync if needed | Current intermediate candidate-pool working copy |

## Template and current-input responsibilities

- `00~02`
  - follow the canonical field contract from `STD_01` + `STD_99`
  - template layer is for reset / copy / reference
  - current-input layer is for the live run only
- `03`
  - remains repo-local because the external field master does not define it
  - is now the intermediate candidate-sample pool instead of the old midstream manual-judgment bridge
  - must not require final judgment, final explanation, or Go/No-Go at this stage
- `04`
  - remains repo-local and post-cost only
  - must not be treated as a preflight blocker or a pushdown control table

## Canonical usage rules

- For thresholds and pushdown gates, read `STD_90`.
- For field names, required flags, fill modes, and manual / auto boundaries, read `STD_99`.
- Do not let models invent fields or thresholds outside `STD_90` + `STD_99`.
- Manual-only fields stay blank until the daytime operator phase.
