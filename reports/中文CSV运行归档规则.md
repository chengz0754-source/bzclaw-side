# 中文 CSV 运行归档规则

## 当前 Preflight 口径

- 当前 repo-visible working inputs 以 `inputs/selection_run_current/` 中的 `00`、`01`、`03` 为准。
- `02_账号与合规预检查.csv` 仍属于人工预检表，可以暂时保持模板态，但仍属于当前输入层的一部分。
- `04_供应链询价与利润核算.csv` 是后置表，不属于 preflight 阶段的前置必填输入。
- `outputs/selection_runs/<batch_id>/02_generated_outputs/` 单独存在时，只能视为 partial artifact package，不能视为完整 run archive。

## 每次运行前

1. 只有在明确开始新一轮 run 时，才执行 `python scripts/reset_selection_input_from_templates.py`。
2. 运行前确认并填写 `inputs/selection_run_current/00~03`，不要把人工字段交给脚本或模型自动补齐。
3. SellerSprite 原始市场表统一放在 `runs/manual/10_market/`。
4. raw workbook keep-set 规则：
   - 优先保留最新的 canonical `market-report-*.xlsx`
   - 若没有 canonical 文件，则回退到最新的非诊断 `.xlsx`
5. raw workbook archive-set / diagnostic-set 规则：
   - `diag-*.xlsx`、`archive-*.xlsx` 只作为证据保留
   - 这些文件不得作为自动映射脚本的默认输入来源

## 每次运行后

1. 正式归档时，使用 `python scripts/archive_selection_run_io.py ...` 归档本轮输入、输出与日志。
2. 完整归档目录必须同时包含：
   - `00_run_summary.md`
   - `01_consumed_inputs/`
   - `02_generated_outputs/`
   - `03_logs/`
3. 如果某个时间戳目录只有 `02_generated_outputs/`，它表示一次中间映射或清洗产物，不表示完整 run 已归档完成。
4. `archive_selection_run_io.py` 执行成功后，会把本轮输入从 `inputs/selection_run_current/` 移入 `01_consumed_inputs/`。
5. 模板目录 `templates/selection_csv_cn_reference/` 不应被归档脚本改写。

## P10 Nightly Acceptance 口径

夜跑验收与正式归档必须明确区分：

1. `scripts/run_nightly_selection_acceptance.py`
   - 用途：端到端 nightly dry-run / acceptance
   - 行为：复制 `inputs/selection_run_current/` 到 `outputs/selection_runs/<batch_id>/01_consumed_inputs/`
   - 特征：生成完整的 archive-shaped package，但不清空当前输入层
   - 适用：验证主链是否 ready for nightly acceptance
2. `scripts/archive_selection_run_io.py`
   - 用途：完成一次人工确认后的正式归档
   - 行为：把当前输入移动到 `01_consumed_inputs/`
   - 特征：会清空当前输入层中的本轮业务输入
   - 适用：操作员明确要收口本轮正式 run 时

P10 当前真实结论：

- `20260407_p10_acceptance` 已证明夜跑 dry-run 可以完整落档
- 但 acceptance 结果仍是 `HOLD`
- 当前阻塞仍包括：
  - `BLOCKED_BY_UPSTREAM_CHAIN__STEP2_ALL_RAW_RUNS_BLOCKED`
  - `SIF_AUTH_REQUIRED`
  - `BLOCKED_BY_SIF_OR_POOL_ALIGNMENT`

因此，当前 repo 只能宣称：

- `ready for E2E dry-run`

不能宣称：

- `nightly autonomous acceptance passed`

## 敏感文件规则

以下文件或目录只允许本地保留，不应进入 git：

- `playwright/auth/sellersprite.storage_state.json`
- `playwright/auth/storage_state.smoke.json`
- `playwright/profiles/sellersprite-main/`
- `playwright/profiles/chromium-user-data/`
- `playwright/profiles/sif-main/`
- `runs/manual/10_market/*.xlsx`
- 任意真实 Cookie、Token、Session、storage state、trace、截图或录屏产物

## 解释边界

- 归档语义以 repo 真相优先，不以文件名想当然推断。
- 需要做业务判断的字段继续留给白天人工阶段处理。
- 所有下推仍必须由 `templates/selection_canonical_standards/99_字段数据标准总表.csv` 与 `templates/selection_canonical_standards/90_下推参数表.csv` 决定，不能让低能力模型自由发挥。
