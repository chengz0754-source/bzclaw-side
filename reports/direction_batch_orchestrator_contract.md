# Direction Batch Orchestrator Contract

## Scope

- This contract standardizes the batch-orchestration layer for direction rows in `inputs/selection_run_current/00/01/02`.
- The orchestrator does not invent keywords, market judgments, or human explanations.
- The orchestrator only performs deterministic:
  - input loading
  - state transitions
  - grouping / de-duplication / normalization
  - downstream script triggering
  - queue and summary logging

## Canonical Inputs

- Goal boundary input:
  - `inputs/selection_run_current/00_选品运行目标与边界.csv`
- Direction input:
  - `inputs/selection_run_current/01_市场入口与筛选参数.csv`
- Compliance precheck input:
  - `inputs/selection_run_current/02_账号与合规预检查.csv`
- Rule source:
  - `templates/selection_canonical_standards/90_下推参数表.csv`
- STEP2 keyword gate source:
  - latest `22_关键词证据词池下推结果.csv`
  - latest `logs/keyword_chain/latest_keyword_build_run.json`

## Fixed State Machine

- Allowed stage statuses:
  - `PASS`
  - `FAIL`
  - `HOLD`
- Formal gate sequence:
  - `STEP1_DIRECTION_GATE`
  - `STEP2_KEYWORD_GATE`
  - `STEP3_MARKET_GATE`
  - `STEP4_BENCHMARK_GATE`
- Probe / execution sequence:
  - `STEP3_MARKET_TRIGGER`
  - `STEP4_BENCHMARK_TRIGGER`

The trigger stages are probe / execution records only. They never override a blocked formal gate.

## Upstream Truth On 2026-04-07

- STEP3 market chain is repo-visible and verified.
- STEP4 benchmark chain is repo-visible and verified through STEP3 PASS seeds.
- STEP2 keyword chain code exists, but live collection is still blocked by SellerSprite auth / guest gating.
- Because of that, the orchestrator must fail closed at the batch level with:
  - `BLOCKED_BY_UPSTREAM_CHAIN__<step2_reason_code>`

Additional current truth on `2026-04-09`:

- STEP2 keyword chain now also has a verified canonical build for `claw machine / US`:
  - latest official `logs/keyword_chain/latest_keyword_build_run.json` is `PASS`
  - canonical `20/21/22` exists, with gate summary `PASS=0 / FAIL=7 / HOLD=12`
- The batch layer must therefore distinguish two different STEP2 truths:
  - `STEP2_BUILD_PASS_BUT_NO_PASS_GATE_ROWS`
  - `STEP2_RAW_OR_BUILD_BLOCKED_BY_AUTH`
- If the latest STEP2 build is `PASS` but the gate has no matching `PASS` row, the batch must still stay `HOLD` because keyword evidence is real but not promotable.
- If STEP2 raw collection later regresses behind SellerSprite auth again, the batch must fail closed with:
  - `BLOCKED_BY_UPSTREAM_CHAIN__<step2_reason_code>`

This means the orchestrator may still run downstream trigger probes, but it must not claim that the main direction pipeline is fully connected.

## Direction ID Policy

- `方向ID` remains a manual field in current input `01`.
- The orchestrator must not write back inferred values into current input files.
- For runtime-only correlation, the orchestrator may resolve a temporary `方向ID` from existing STEP3 / STEP4 artifacts and record the source as:
  - `MANUAL_INPUT`
  - `STEP4_GATE_MATCH`
  - `STEP3_GATE_MATCH`
  - `MISSING`

## Queue Output

- Canonical batch queue file:
  - `outputs/selection_runs/<batch_id>/02_generated_outputs/batch_queue_status.csv`
- Required columns:
  - `row_index`
  - `运行名称`
  - `方向ID`
  - `方向ID来源`
  - `方向词`
  - `关键词`
  - `stage_code`
  - `status`
  - `reason_code`
  - `source`
  - `time_window`
  - `data_snapshot`
  - `output_artifact`

## Batch Summary

- Canonical batch summary files:
  - `batch_run_summary.json`
  - `batch_run_summary.md`
- Batch logs:
  - `logs/direction_batch/latest_run.json`
  - `logs/direction_batch/direction_batch_runs.jsonl`
  - `logs/direction_batch/direction_batch_failures.jsonl`

## Fail-Closed Rules

- If STEP2 latest build status is not `PASS`, batch status must stay `HOLD`.
- If `22_关键词证据词池下推结果.csv` is missing or has no matching row, the orchestrator must not fabricate keyword evidence rows.
- If a downstream trigger fails for one row or one keyword, the batch must continue and record the failure in the queue.
- If `方向ID` is unavailable, the orchestrator may still export benchmark raw results, but STEP4 canonical build must stay `HOLD`.
- Runtime outputs stay local under ignored `outputs/` and `logs/`; they must not enter git.
