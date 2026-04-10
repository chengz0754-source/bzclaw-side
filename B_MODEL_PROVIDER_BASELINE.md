# B 仓 Model / Provider Baseline

## 1. 固定真相源

B 仓模型与 provider wiring 以以下文件为准：

- `configs/model.json`
- `models/README.md`

如果 prompt、报告、口头描述与这两处冲突，以这两处为准；不要从别的仓、旧包镜像或想象中的编排层脑补能力。

## 2. 当前固定 provider wiring

### 2.1 默认 provider

- `default_provider = ollama_local`
- `enabled = true`
- `protocol = openai_compatible`
- `base_url = http://127.0.0.1:11434/v1`
- `api_key_env = OLLAMA_API_KEY`
- `default_model = qwen3:4b-instruct`
- `verified_entry_point = ollama list`

### 2.2 预留 cloud provider

- provider 名称：`openai_cloud`
- 当前默认状态：`enabled = false`
- 仅保留 env wiring：
  - `OPENAI_BASE_URL`
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL`

结论：

- B 仓当前已验证的 baseline 是本地 Ollama
- OpenAI cloud 只是预留切换位，不是当前默认执行面

## 3. 当前固定 policy

`configs/model.json` 已明确：

- `local_model_preferred = true`
- `provider_swap_allowed = true`
- `business_completion_claim_allowed = false`

解释口径：

- 默认优先走本地小模型
- provider 可以替换，但替换不等于默认启用
- 模型运行结果不能被写成业务闭环完成声明

## 4. 这套模型层意味着什么

它意味着：

- B 仓已经有真实的模型 wiring baseline
- B 仓可以承接 extraction、解释、辅助采集、结构化整理这类受控模型调用
- B 仓可以作为 sidecar runtime 的一部分工作

它不意味着：

- B 仓已经有成熟的多 provider orchestration 平台
- B 仓已经有统一 queue / broker / artifact bus
- B 仓当前默认就是高自治 agent
- `qwen3:4b-instruct` 是最终能力上限
- 可以把未验证的 9B、cloud、vision、embedding 能力写成既成事实

## 5. 与运行目录的固定关系

### 5.1 业务输出落点

如果模型调用生成的是本轮业务产物，默认应落在：

- `outputs/selection_runs/<batch_id>/02_generated_outputs/`

### 5.2 执行日志落点

如果模型调用生成的是 receipt、latest 状态、history 记录、失败日志或诊断信息，默认应落在：

- `logs/<namespace>/latest_*.json`
- `logs/<namespace>/*.jsonl`
- 或某个 run scope 下的 `logs/<run_scope>/<step_name>/`

### 5.3 敏感信息边界

- API key 与 provider secrets 只放环境变量或 `.env`
- 不把 secrets 写进 repo-visible 文档
- 不把 storage state、profile、trace、screenshot 当 provider proof

## 6. 后续 prompt 的默认写法

推荐写法：

- “B 仓当前默认 provider baseline 是本地 Ollama”
- “默认模型 baseline 是 `qwen3:4b-instruct`”
- “cloud provider 仅有预留 wiring，默认关闭”
- “模型层是可替换 provider baseline，不是成熟 orchestration 平台”

不推荐写法：

- “B 仓默认就是 OpenAI cloud worker”
- “B 仓已经具备完整 provider routing plane”
- “当前 4B 配置可以代表项目最终模型能力”
- “模型结果可以直接宣称业务完成”

## 7. fail-closed 规则

- 本地 provider 不可用且 cloud 仍未显式启用时，应报告 provider 不可用
- 不允许因为 provider 缺失就脑补结果
- 不允许把 smoke、截图、trace 或单次模型输出写成业务闭环 proof
