# 当前运行输入目录说明

这里是每次正式运行前的真实输入位置：`inputs/selection_run_current/`

## 使用规则

- 运行脚本只应从这里读取当前轮的 live input。
- 当前前置阶段默认使用 `00~03`。
- `04_供应链询价与利润核算.csv` 是后置表，只在进入供应链询价阶段后再放入当前输入目录。
- 运行后，本轮输入文件会被归档到 `outputs/selection_runs/<timestamp>/01_consumed_inputs/`。

## 与 canonical 标准的关系

- `00~02` 的字段合同以 `templates/selection_canonical_standards/99_字段数据标准总表.csv` 为准。
- `03_候选市场与候选品初筛池.csv` 是 repo-local 中间候选样品池工作表，不是 external canonical field master。
- `03` 的职责已经改为中间候选池，不再要求在这里写最终判断、人工结论或 Go/No-Go。
- `04` 是 repo-local post-cost sheet，不属于 preflight 输入。

## 运行口径

- runtime `03` 和 `60` 池子应由 `python scripts/build_candidate_pool.py` 从 STEP3 / STEP4 结构化结果构建。
- 不要把 SellerSprite 原始市场表 `.xlsx` 放在这里；原始市场表应放在 `runs/manual/10_market/`。
- 如果人工字段当前没有确认值，就保持留空，不要让脚本或模型代填。

## 快速准备

- 执行 `python scripts/reset_selection_input_from_templates.py`
  - 默认复制 `00~03` 到当前输入目录。
- 执行 `python scripts/reset_selection_input_from_templates.py --include-post-cost`
  - 进入后置询价阶段时，再把 `04` 一起复制进来。
