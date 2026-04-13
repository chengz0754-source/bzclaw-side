# 中文 CSV 模板目录说明

标准模板目录固定为：`templates/selection_csv_cn_reference/`

## 当前正式输入层

- `00_选品运行目标与边界.csv`
  - 批次级全局边界。
- `01_选品任务路由与目的.csv`
  - 每行定义一个任务的业务目的、入口类型、STEP3 policy、SIF policy。
- `01A_市场发现参数.csv`
  - 只服务 `MARKET_DISCOVERY` 或 broad market remap。
- `01B_产品与竞品种子输入.csv`
  - 服务 `PRODUCT_IDEA_VALIDATION / COMPETITOR_REVERSE_MINING / SUPPLY_CHAIN_BACKSOLVE`。
- `02_账号与合规预检查.csv`
  - 账号权限、登录态、合规边界。
- `02A_SIF补强策略输入.csv`
  - 只在 shortlist / candidate rows 之后进入 SIF 时消费。
- `03_候选市场与候选品初筛池.csv`
  - 中间候选池模板，不是最终人工判断表。
- `04_供应链询价与利润核算.csv`
  - 后置询价与利润核算表。

## 使用方式

- 每次开始新一轮之前，可运行 `python scripts/reset_selection_input_from_templates.py` 把 `00 / 01 / 01A / 01B / 02 / 02A / 03` 复制到 `inputs/selection_run_current/`。
- 若当前轮次已经进入供应链核价，再追加 `--include-post-cost` 复制 `04`。
- SellerSprite collectors 当前仍从 `inputs/selection_run_current/01_市场入口与筛选参数.csv` 读取页面运行参数。
- 新的 purpose router 则从 `01_选品任务路由与目的.csv`、`01A`、`01B`、`02A` 读取业务意图和路径切换信息。

## 重要边界

- 这些模板是 operator-facing 输入合同，不是 canonical field master。
- canonical 标准仍只认 `templates/selection_canonical_standards/`。
- SIF 不是前置主链；`02A` 只定义 shortlist 后的补强策略，不代表 live SIF mainline 已打通。
