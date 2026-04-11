# 中文 CSV 目录与用途说明

## 固定目录

### `templates/selection_csv_cn_reference/`

- 中文 CSV 模板参考层。
- 长期保留 `00~04` 模板，用于重置、对照、审计。
- 不作为运行产物归档位置。

### `inputs/selection_run_current/`

- repo-visible 当前工作输入层。
- 当前真实前置输入是 `00_选品运行目标与边界.csv`、`01_市场入口与筛选参数.csv`、`02_账号与合规预检查.csv`。
- `03_候选市场与候选品初筛池.csv` 现在是 repo-local 中间候选样品池工作表，不再是旧版“市场表直接映射后的中途人工判断表”。
- `04_供应链询价与利润核算.csv` 仍是后置人工表。

### `runs/manual/10_market/`

- SellerSprite 市场调研原始 workbook 固定落点。
- 这里只存 raw workbook，不等同于结构化候选池。

### `outputs/selection_runs/<batch_id>/02_generated_outputs/`

- 每次运行的结构化输出层。
- STEP3 产出 `30/31/32`。
- STEP4 产出 `40/41/42`。
- P07 之后由 `python scripts/build_candidate_pool.py` 生成 runtime `03_候选市场与候选品初筛池.csv`、`60_候选样品池.csv`、`60_候选样品池.md`。

## CSV 时序

- `00_选品运行目标与边界.csv`：前置目标与边界。
- `01_市场入口与筛选参数.csv`：前置方向、站点、窗口、样本参数。
- `02_账号与合规预检查.csv`：前置人工检查表。
- `03_候选市场与候选品初筛池.csv`：中间候选样品池工作表，由 STEP3/STEP4 结构化结果汇总生成。
- `04_供应链询价与利润核算.csv`：候选样品确认后进入后置核价。
- `60_候选样品池.csv`：白天可读的候选样品池投影，人工字段保持留空。

## 目录职责边界

- 模板层、当前输入层、raw workbook 层、运行输出层不能混用。
- `scripts/map_market_report_to_candidate_pool.py` 现在只保留 market-only helper 角色，不再允许直接覆盖当前 `03`。
- `scripts/build_candidate_pool.py` 是 runtime `03` 和 `60` 的唯一标准构建脚本。
- 根目录不应长期堆放业务 CSV、Excel、临时说明文档。
