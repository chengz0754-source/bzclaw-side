# B 仓 Sidecar Baseline

## 1. 这份 baseline 固化什么

本文件把 B 机仓库固定为一个独立的 sidecar repo baseline，供后续所有 B 机 prompt 复用。

- prompt 包中的规范引用路径：`E:\bzclaw-side`
- 本机在 `2026-04-11` 实际观测到的可执行仓：`E:\选品文件夹\amazon-selection-automation`
- 使用规则：后续 prompt 如果写 `B 仓` 或 `E:\bzclaw-side`，默认指向这类独立 sidecar 仓语义；如果本机别名路径不存在，则应显式注明当前实际观测路径，而不是把它并入 A 仓或脑补成别的宿主

## 2. B 仓是什么

- 一个独立的 Machine B sidecar repo
- 一个轻量但真实存在的执行仓
- 一个承接本地模型调用、Playwright 自动化、业务脚本执行、日志与运行产物的受控 runtime 工作区
- 一个通过 contract / handoff / evidence / provider boundary 与 A 仓相连的执行面

当前允许的真实表述：

- 已有目录骨架
- 已有模型 wiring
- 已有 Playwright smoke baseline
- 已有真实业务自动化脚本与 artifact 产出能力
- 已有 auth / profile / screenshot / trace 的本地侧车能力

## 3. B 仓不是什么

- 不是 A 主仓子目录
- 不是 A 仓 truth host 的延伸
- 不是 authority/current/slot40 的写入宿主
- 不是 formal publish 宿主
- 不是成熟 worker platform
- 不是 broker / queue / unified artifact bus
- 不是第二真相主机

后续 prompt 禁止出现的误写：

- “B 仓已经是成熟 worker platform”
- “B 仓可以直接写 current / authority / slot40”
- “B 仓可以 formal publish”
- “B 仓与 A 仓共享同一套 repo truth”

## 4. Repo 边界

### 4.1 repo 内应被视为 sidecar 自有基线的内容

- 根目录说明与清单文件
- `configs/`
- `scripts/`
- `models/`
- `reports/`
- `inputs/` 中的 repo-visible 当前输入层与说明文件
- `skills/` 中被复制进仓的 legacy code / config / docs
- `logs/README.md`、`outputs/README.md`、`runs/.gitkeep`、`playwright/*/.gitkeep` 这类占位或说明文件

### 4.2 repo 外或 git 外的内容

- `.venv/`
- `.env` 与真实 secrets
- `playwright/auth/` 下真实 storage state 与 replay 敏感文件
- `playwright/profiles/**`
- `playwright/screenshots/**`
- `playwright/traces/**`
- `logs/**` 的运行内容
- `outputs/**` 的运行内容
- `runs/**` 的运行内容
- raw workbook、archive、inbox、cookie、token、session 等本地产物

## 5. 固定目录骨架

- `inputs/`
  - live input 与 A -> B 手工交付输入层
- `outputs/`
  - business output 根目录；正式 run archive 主要落这里
- `logs/`
  - 执行日志、latest receipt、history jsonl、诊断包
- `reports/`
  - baseline、contract、验证、runbook、总结报告
- `runs/`
  - 手工运行、原始下载件、临时工作簿与本地证据 staging
- `playwright/`
  - 受控浏览器 sidecar 根目录
- `playwright/auth/`
  - storage state、replay registry、owner recording；敏感且本地保留
- `playwright/profiles/`
  - 持久化浏览器 profile；敏感且本地保留
- `playwright/screenshots/`
  - smoke / debug / auth incident 截图；证据面，不是业务 proof
- `playwright/traces/`
  - trace zip；证据面，不是业务 proof
- `models/`
  - provider 使用说明与模型放置约定
- `configs/`
  - `paths.json`、`model.json` 等固定 wiring 配置
- `scripts/`
  - 当前可执行的 sidecar automation entrypoints

补充约束：

- 当前观测仓存在 `skills/`，它表示 imported legacy code/config/docs
- 当前观测仓未看到独立的 `skills_runtime/`
- 因此，在 `skills_runtime/` 真正落地前，后续 prompt 应把 `scripts/` + imported `skills/` 视为当前执行面，而不是把 B 仓直接升级描述成成熟 skill runtime 平台

## 6. Run / artifact 约定

### 6.1 live input 约定

- 当前轮真实输入从 `inputs/selection_run_current/` 读取
- `00~03` 是当前 preflight 默认输入层
- `04_供应链询价与利润核算.csv` 是后置表，不应提前当作前置必填

### 6.2 正式 run archive 约定

正式业务 run archive 根目录：

- `outputs/selection_runs/<batch_id>/`

完整 run archive 必须同时包含：

- `00_run_summary.md`
- `01_consumed_inputs/`
- `02_generated_outputs/`
- `03_logs/`

解释规则：

- 只有 `02_generated_outputs/` 的目录，只能算 partial artifact package
- `run_nightly_selection_acceptance.py` 可以生成 archive-shaped dry-run package，但不等于业务闭环通过
- `archive_selection_run_io.py` 才是人工确认后的正式归档动作

### 6.3 原始下载件与证据约定

- raw SellerSprite workbook 放 `runs/manual/...`
- `playwright/screenshots/`、`playwright/traces/`、`playwright/auth/` 属于本地证据与状态层
- smoke / trace / screenshot / workbook 本身不能直接写成 business proof

### 6.4 fail-closed 读取口径

- 优先读取本机仓库中的真实输出
- 其次读取 prompt 包中的基线副本
- 两者都没有时输出 `UPSTREAM_MISSING`
- 路径不存在时输出 `PATH_NOT_FOUND`

## 7. 与 A 仓的固定关系

- A 管治理、批准、truth-adjacent event 与 formal publish 边界
- B 管执行、观察、局部证据、模型调用、浏览器自动化与 artifact 生成
- B 可以回传 observation / evidence
- B 不负责 event 最终定义
- B 不改 A 仓 repo truth

## 8. 后续 prompt 的默认写法

推荐写法：

- “B 仓是独立 sidecar repo”
- “B 仓是轻量但真实的执行仓”
- “B 仓当前已有模型 wiring、Playwright smoke、业务自动化脚本和运行产物能力”
- “B 仓不是 truth host，也不是成熟 worker platform”

不推荐写法：

- “B 仓只是附件”
- “B 仓已经是完整 worker plane / broker / queue 平台”
- “B 仓可以直接代表 A 仓 current / publish”
