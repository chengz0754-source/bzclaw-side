from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from keyword_chain_common import (
    ROOT,
    OUTPUTS_ROOT,
    ensure_within_repo,
    iso_now,
    load_csv_rows,
    parse_int_value,
    safe_float,
    timestamp_slug,
    write_csv_atomic,
    write_json_atomic,
)


CURRENT_GOAL_PATH = ROOT / "inputs" / "selection_run_current" / "00_选品运行目标与边界.csv"
CURRENT_ENTRY_PATH = ROOT / "inputs" / "selection_run_current" / "01_市场入口与筛选参数.csv"
CURRENT_COMPLIANCE_PATH = ROOT / "inputs" / "selection_run_current" / "02_账号与合规预检查.csv"
STANDARD_90_PATH = ROOT / "templates" / "selection_canonical_standards" / "90_下推参数表.csv"
STEP2_LOG_PATH = ROOT / "logs" / "keyword_chain" / "latest_keyword_build_run.json"
DEFAULT_LOG_DIR = ROOT / "logs" / "direction_batch"
REPO_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"

STEP2_GATE_FILE = "22_关键词证据词池下推结果.csv"
STEP3_GATE_FILE = "32_市场调研下推结果.csv"
STEP4_GATE_FILE = "42_竞品基准下推结果.csv"

QUEUE_FILE = "batch_queue_status.csv"
SUMMARY_JSON = "batch_run_summary.json"
SUMMARY_MD = "batch_run_summary.md"
LATEST_RUN_FILE = "latest_run.json"
RUN_HISTORY_FILE = "direction_batch_runs.jsonl"
RUN_FAILURE_FILE = "direction_batch_failures.jsonl"

QUEUE_HEADERS = [
    "batch_id",
    "recorded_at",
    "row_index",
    "运行名称",
    "方向ID",
    "方向ID来源",
    "方向词",
    "关键词",
    "stage_code",
    "item_type",
    "status",
    "reason_code",
    "source",
    "time_window",
    "data_snapshot",
    "output_artifact",
]


class DirectionBatchError(RuntimeError):
    pass


@dataclass
class DirectionContext:
    row_index: int
    run_name: str
    direction_id: str
    direction_id_source: str
    direction_keyword: str
    category_hint: str
    site: str
    days: int
    new_product_days: int
    sample_top_n: int
    head_top_n: int
    max_push_keywords: int | None
    max_candidate_samples: int | None
    goal_row: dict[str, str]
    compliance_row: dict[str, str]


@dataclass
class KeywordItem:
    keyword: str
    status: str
    reason_code: str
    source: str
    snapshot: dict[str, Any]
    from_step2_gate: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the selection-direction batch orchestrator with fail-closed upstream chaining.",
    )
    parser.add_argument("--row-indices", default=None, help="Comma-separated 01-row indices. Defaults to all data rows.")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--step2-gate-csv", default=None)
    parser.add_argument("--step3-gate-csv", default=None)
    parser.add_argument("--step4-gate-csv", default=None)
    parser.add_argument("--trigger-market-dry-run", action="store_true")
    parser.add_argument("--trigger-market-live", action="store_true")
    parser.add_argument("--trigger-benchmark-live", action="store_true")
    parser.add_argument("--trigger-benchmark-build", action="store_true")
    return parser.parse_args()


def append_jsonl(path: Path, payload: Any) -> None:
    ensure_within_repo(path, "jsonl_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def repo_path(raw_path: str | None, label: str) -> Path:
    if not raw_path:
        raise DirectionBatchError(f"Missing path for {label}.")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return ensure_within_repo(path, label)


def default_output_dir(batch_id: str) -> Path:
    return ensure_within_repo(OUTPUTS_ROOT / batch_id / "02_generated_outputs", "output_dir")


def load_dict_rows(path: Path) -> list[dict[str, str]]:
    rows = load_csv_rows(path)
    if not rows:
        return []
    headers = rows[0]
    mapped: list[dict[str, str]] = []
    for raw_row in rows[1:]:
        mapped.append({header: raw_row[idx] if idx < len(raw_row) else "" for idx, header in enumerate(headers)})
    return mapped


def latest_generated_file(file_name: str) -> Path | None:
    candidates = sorted(
        OUTPUTS_ROOT.glob(f"*/02_generated_outputs/{file_name}"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        return ensure_within_repo(candidate, file_name)
    return None


def compact_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def normalize_status(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized in {"PASS", "FAIL", "HOLD"}:
        return normalized
    if normalized == "BLOCKED":
        return "HOLD"
    if normalized in {"DRY_RUN", "CREATED"}:
        return "PASS"
    return "HOLD"


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", str(value or "").strip().lower()).strip("-")
    return cleaned or "row"


def parse_row_indices(raw_value: str | None, total_rows: int) -> list[int]:
    if total_rows <= 0:
        return []
    if not raw_value:
        return list(range(1, total_rows + 1))
    values: list[int] = []
    for token in str(raw_value).split(","):
        token = token.strip()
        if not token:
            continue
        row_index = int(token)
        if row_index <= 0 or row_index > total_rows:
            raise DirectionBatchError(f"--row-indices contains out-of-range row: {row_index}; available rows: 1..{total_rows}")
        values.append(row_index)
    if not values:
        raise DirectionBatchError("--row-indices did not contain any usable row number.")
    return values


def load_step_rules(step_code: str) -> list[dict[str, str]]:
    rows = list(csv.DictReader(STANDARD_90_PATH.read_text(encoding="utf-8-sig").splitlines()))
    filtered = [row for row in rows if row.get("step_code") == step_code and row.get("enabled") == "TRUE"]
    filtered.sort(key=lambda row: parse_int_value(row.get("tie_breaker_rank") or 999, "tie_breaker_rank"))
    return filtered


def match_value(row: dict[str, str], key: str, expected: str) -> bool:
    if not expected:
        return True
    return str(row.get(key, "")).strip().casefold() == str(expected).strip().casefold()


def match_gate_rows(rows: list[dict[str, str]], context: DirectionContext, keyword: str) -> list[dict[str, str]]:
    matched: list[dict[str, str]] = []
    for row in rows:
        direction_id = str(row.get("方向ID", "")).strip()
        if context.direction_id and direction_id and direction_id != context.direction_id:
            continue
        if not match_value(row, "运行名称", context.run_name):
            continue
        if str(row.get("站点", "")).strip() and not match_value(row, "站点", context.site):
            continue
        if not match_value(row, "关键词", keyword):
            continue
        matched.append(row)
    return matched


def infer_direction_id(entry_row: dict[str, str], step4_rows: list[dict[str, str]], step3_rows: list[dict[str, str]]) -> tuple[str, str]:
    manual = str(entry_row.get("方向ID", "")).strip()
    if manual:
        return manual, "MANUAL_INPUT"

    run_name = str(entry_row.get("运行名称", "")).strip()
    keyword = str(entry_row.get("方向词", "")).strip()
    site = str(entry_row.get("站点", "")).strip().upper()

    for row in step4_rows:
        inferred = str(row.get("方向ID", "")).strip()
        if inferred and match_value(row, "运行名称", run_name) and match_value(row, "关键词", keyword):
            return inferred, "STEP4_GATE_MATCH"
    for row in step3_rows:
        inferred = str(row.get("方向ID", "")).strip()
        if inferred and match_value(row, "运行名称", run_name) and match_value(row, "关键词", keyword) and match_value(row, "站点", site):
            return inferred, "STEP3_GATE_MATCH"
    return "", "MISSING"


def token_count(text: str) -> int:
    return len(re.findall(r"[0-9A-Za-z\u4e00-\u9fff]+", str(text or "")))


def choose_compliance_row(rows: list[dict[str, str]], run_name: str, site: str) -> dict[str, str]:
    for row in rows:
        if match_value(row, "运行名称", run_name) and match_value(row, "站点", site):
            return row
    for row in rows:
        if match_value(row, "站点", site):
            return row
    return {}


def build_context(
    row_index: int,
    goal_row: dict[str, str],
    entry_row: dict[str, str],
    compliance_rows: list[dict[str, str]],
    step4_rows: list[dict[str, str]],
    step3_rows: list[dict[str, str]],
) -> DirectionContext:
    direction_id, direction_id_source = infer_direction_id(entry_row, step4_rows, step3_rows)
    site = str(entry_row.get("站点", "")).strip().upper()
    compliance_row = choose_compliance_row(compliance_rows, str(entry_row.get("运行名称", "")).strip(), site)
    raw_push_limit = str(entry_row.get("每个方向最大下推关键词数", "")).strip()
    raw_candidate_limit = str(entry_row.get("每个方向最大候选样品数", "")).strip()
    return DirectionContext(
        row_index=row_index,
        run_name=str(entry_row.get("运行名称", "")).strip(),
        direction_id=direction_id,
        direction_id_source=direction_id_source,
        direction_keyword=str(entry_row.get("方向词", "")).strip(),
        category_hint=str(entry_row.get("类目提示", "")).strip(),
        site=site,
        days=parse_int_value(entry_row.get("时间范围_天") or 30, "时间范围_天"),
        new_product_days=parse_int_value(entry_row.get("新品定义_天") or 180, "新品定义_天"),
        sample_top_n=parse_int_value(entry_row.get("样本数前N") or 100, "样本数前N"),
        head_top_n=parse_int_value(entry_row.get("头部商品前N") or 10, "头部商品前N"),
        max_push_keywords=parse_int_value(raw_push_limit, "每个方向最大下推关键词数") if raw_push_limit else None,
        max_candidate_samples=parse_int_value(raw_candidate_limit, "每个方向最大候选样品数") if raw_candidate_limit else None,
        goal_row=goal_row,
        compliance_row=compliance_row,
    )


def evaluate_step1(context: DirectionContext, rules: list[dict[str, str]]) -> tuple[str, str, dict[str, Any]]:
    required_values = {
        "运行名称": context.run_name,
        "方向词": context.direction_keyword,
        "站点": context.site,
        "目标售价下限": context.goal_row.get("目标售价下限", ""),
        "目标售价上限": context.goal_row.get("目标售价上限", ""),
        "目标类目": context.compliance_row.get("目标类目", ""),
    }
    required_field_count = 1 if all(str(value).strip() for value in required_values.values()) else 0
    direction_tokens = token_count(context.direction_keyword)

    overall_status = "PASS"
    reason_codes: list[str] = []
    for rule in rules:
        rule_id = str(rule.get("rule_id", "")).strip()
        comparator = str(rule.get("comparator", "")).strip()
        threshold = safe_float(rule.get("threshold_value"))
        hard_fail = str(rule.get("hard_fail", "")).strip().upper() == "TRUE"
        blank_action = normalize_status(str(rule.get("blank_action", "")).strip())
        metric_value: float | None
        if rule_id == "S1_REQUIRED_FIELDS":
            metric_value = float(required_field_count)
        elif rule_id == "S1_DIRECTION_TOKEN_MIN":
            metric_value = float(direction_tokens)
        else:
            continue

        if threshold is None:
            outcome = blank_action
        elif comparator == ">=":
            outcome = "PASS" if metric_value >= threshold else ("FAIL" if hard_fail else "HOLD")
        elif comparator == "<=":
            outcome = "PASS" if metric_value <= threshold else ("FAIL" if hard_fail else "HOLD")
        else:
            outcome = blank_action

        if outcome != "PASS":
            reason_codes.append(rule_id)
            if outcome == "FAIL":
                overall_status = "FAIL"
            elif overall_status != "FAIL":
                overall_status = "HOLD"

    snapshot = {
        "required_values": required_values,
        "required_field_count": required_field_count,
        "direction_token_count": direction_tokens,
    }
    return overall_status, ("PASS" if not reason_codes else ";".join(reason_codes)), snapshot


def latest_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_gate_rows_from_optional(raw_path: str | None, file_name: str) -> tuple[Path | None, list[dict[str, str]]]:
    path = repo_path(raw_path, file_name) if raw_path else latest_generated_file(file_name)
    if not path or not path.exists():
        return None, []
    return path, load_dict_rows(path)


def queue_row(
    batch_id: str,
    context: DirectionContext,
    keyword: str,
    stage_code: str,
    item_type: str,
    status: str,
    reason_code: str,
    source: str,
    snapshot: dict[str, Any],
    output_artifact: str = "",
) -> dict[str, str]:
    return {
        "batch_id": batch_id,
        "recorded_at": iso_now(),
        "row_index": str(context.row_index),
        "运行名称": context.run_name,
        "方向ID": context.direction_id,
        "方向ID来源": context.direction_id_source,
        "方向词": context.direction_keyword,
        "关键词": keyword,
        "stage_code": stage_code,
        "item_type": item_type,
        "status": normalize_status(status),
        "reason_code": reason_code or ("PASS" if normalize_status(status) == "PASS" else ""),
        "source": source,
        "time_window": f"{context.days}d",
        "data_snapshot": compact_json(snapshot),
        "output_artifact": output_artifact,
    }


def latest_step2_state(step2_log: dict[str, Any]) -> tuple[str, str]:
    if not step2_log:
        return "HOLD", "STEP2_BUILD_LOG_MISSING"
    reason_code = str(step2_log.get("reason_code", "")).strip() or "STEP2_STATUS_UNKNOWN"
    return normalize_status(str(step2_log.get("status", "")).strip()), reason_code


def build_keyword_items(
    context: DirectionContext,
    step2_status: str,
    step2_reason: str,
    step2_gate_path: Path | None,
    step2_rows: list[dict[str, str]],
    step2_log: dict[str, Any],
) -> list[KeywordItem]:
    if step2_status != "PASS" or not step2_gate_path or not step2_rows:
        return [
            KeywordItem(
                keyword=context.direction_keyword,
                status="HOLD",
                reason_code=f"BLOCKED_BY_UPSTREAM_CHAIN__{step2_reason}",
                source=str(STEP2_LOG_PATH),
                snapshot={
                    "step2_status": step2_status,
                    "step2_reason_code": step2_reason,
                    "step2_log": step2_log,
                    "step2_gate_path": str(step2_gate_path or ""),
                },
                from_step2_gate=False,
            )
        ]

    matched = match_gate_rows(step2_rows, context, context.direction_keyword)
    if not matched:
        return [
            KeywordItem(
                keyword=context.direction_keyword,
                status="HOLD",
                reason_code="STEP2_NO_MATCHING_KEYWORDS",
                source=str(step2_gate_path),
                snapshot={"step2_gate_path": str(step2_gate_path)},
                from_step2_gate=False,
            )
        ]

    keyword_items: list[KeywordItem] = []
    for row in matched:
        keyword = str(row.get("关键词", "")).strip() or context.direction_keyword
        status = normalize_status(str(row.get("整体状态", "")).strip())
        reason_code = str(row.get("失败原因代码", "")).strip() or ("PASS" if status == "PASS" else "STEP2_STATUS_EMPTY")
        keyword_items.append(
            KeywordItem(
                keyword=keyword,
                status=status,
                reason_code=reason_code,
                source=str(step2_gate_path),
                snapshot=row,
                from_step2_gate=True,
            )
        )

    pass_items = [item for item in keyword_items if item.status == "PASS"]
    if context.max_push_keywords is not None and pass_items:
        pass_items = pass_items[: context.max_push_keywords]
        non_pass = [item for item in keyword_items if item.status != "PASS"]
        return pass_items + non_pass
    return keyword_items


def run_python(command_args: list[str], timeout_seconds: int = 600) -> subprocess.CompletedProcess[str]:
    python_executable = str(REPO_PYTHON if REPO_PYTHON.exists() else Path(sys.executable))
    return subprocess.run(
        [python_executable, *command_args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
        check=False,
    )


def row_output_dir(base_output_dir: Path, context: DirectionContext, keyword: str, stage_slug: str) -> Path:
    row_slug = f"row_{context.row_index:03d}_{slugify(keyword)}"
    return ensure_within_repo(base_output_dir / row_slug / stage_slug, "row_output_dir")


def row_log_dir(base_log_dir: Path, context: DirectionContext, keyword: str, stage_slug: str) -> Path:
    row_slug = f"row_{context.row_index:03d}_{slugify(keyword)}"
    return ensure_within_repo(base_log_dir / row_slug / stage_slug, "row_log_dir")


def market_trigger_result(
    context: DirectionContext,
    keyword: str,
    base_output_dir: Path,
    base_log_dir: Path,
    use_live_export: bool,
) -> tuple[str, str, dict[str, Any], str]:
    output_dir = row_output_dir(base_output_dir, context, keyword, "step3_market")
    log_dir = row_log_dir(base_log_dir, context, keyword, "step3_market")
    command = [
        "scripts/export_market_report.py",
        "--context-row-index",
        str(context.row_index),
        "--keyword",
        keyword,
        "--output-dir",
        str(output_dir),
        "--log-dir",
        str(log_dir),
    ]
    if not use_live_export:
        command.append("--dry-run")

    completed = run_python(command, timeout_seconds=420)
    summary_path = log_dir / "latest_run.json"
    summary = latest_json(summary_path)
    status = "PASS" if completed.returncode == 0 and normalize_status(str(summary.get("status", ""))) == "PASS" else "FAIL"
    reason_code = str(summary.get("reason_code", "")).strip() or f"MARKET_TRIGGER_EXIT_{completed.returncode}"
    snapshot = {
        "command": [sys.executable, *command],
        "exit_code": completed.returncode,
        "stdout_tail": completed.stdout[-800:],
        "stderr_tail": completed.stderr[-800:],
        "summary": summary,
    }
    artifact = str(summary_path if summary_path.exists() else output_dir)
    return status, reason_code, snapshot, artifact


def benchmark_trigger_result(
    context: DirectionContext,
    keyword_item: KeywordItem,
    base_output_dir: Path,
    base_log_dir: Path,
    build_after_export: bool,
) -> tuple[str, str, dict[str, Any], str]:
    output_dir = row_output_dir(base_output_dir, context, keyword_item.keyword, "step4_benchmark")
    log_dir = row_log_dir(base_log_dir, context, keyword_item.keyword, "step4_benchmark")
    export_command = [
        "scripts/export_benchmark_competitors.py",
        "--context-row-index",
        str(context.row_index),
        "--output-dir",
        str(output_dir),
        "--log-dir",
        str(log_dir),
    ]
    if keyword_item.from_step2_gate:
        export_command.extend(["--seed-keyword", keyword_item.keyword, "--seed-market-name", keyword_item.keyword])

    export_completed = run_python(export_command, timeout_seconds=600)
    export_summary_path = log_dir / "latest_benchmark_export_run.json"
    export_summary = latest_json(export_summary_path)
    export_status = normalize_status(str(export_summary.get("status", "")))
    if export_completed.returncode != 0 or export_status != "PASS":
        snapshot = {
            "export_command": [sys.executable, *export_command],
            "export_exit_code": export_completed.returncode,
            "export_stdout_tail": export_completed.stdout[-800:],
            "export_stderr_tail": export_completed.stderr[-800:],
            "export_summary": export_summary,
        }
        reason_code = str(export_summary.get("reason_code", "")).strip() or f"BENCHMARK_EXPORT_EXIT_{export_completed.returncode}"
        return "FAIL", reason_code, snapshot, str(export_summary_path if export_summary_path.exists() else output_dir)

    if not build_after_export:
        snapshot = {
            "export_command": [sys.executable, *export_command],
            "export_exit_code": export_completed.returncode,
            "export_summary": export_summary,
        }
        return "PASS", "PASS", snapshot, str(export_summary_path)

    if not context.direction_id:
        snapshot = {
            "export_summary": export_summary,
            "build_skipped": True,
            "direction_id_source": context.direction_id_source,
        }
        return "HOLD", "DIRECTION_ID_REQUIRED_FOR_STEP4_BUILD", snapshot, str(export_summary_path)

    build_command = [
        "scripts/build_benchmark_seed_pool.py",
        "--context-row-index",
        str(context.row_index),
        "--direction-id",
        context.direction_id,
        "--keyword",
        keyword_item.keyword,
        "--output-dir",
        str(output_dir),
        "--log-dir",
        str(log_dir),
        "--benchmark-run",
        str(export_summary_path),
    ]
    build_completed = run_python(build_command, timeout_seconds=420)
    build_summary_path = log_dir / "latest_benchmark_build_run.json"
    build_summary = latest_json(build_summary_path)
    build_status = normalize_status(str(build_summary.get("status", "")))
    snapshot = {
        "export_command": [sys.executable, *export_command],
        "export_exit_code": export_completed.returncode,
        "export_summary": export_summary,
        "build_command": [sys.executable, *build_command],
        "build_exit_code": build_completed.returncode,
        "build_stdout_tail": build_completed.stdout[-800:],
        "build_stderr_tail": build_completed.stderr[-800:],
        "build_summary": build_summary,
    }
    reason_code = str(build_summary.get("reason_code", "")).strip() or f"BENCHMARK_BUILD_EXIT_{build_completed.returncode}"
    final_status = "PASS" if build_completed.returncode == 0 and build_status == "PASS" else "FAIL"
    return final_status, reason_code, snapshot, str(build_summary_path if build_summary_path.exists() else output_dir)


def summary_markdown(summary: dict[str, Any]) -> str:
    upstream = summary["upstream"]
    counts = summary["counts"]
    return "\n".join(
        [
            "# Direction Batch Orchestrator Summary",
            "",
            f"- batch_id: `{summary['batch_id']}`",
            f"- status: `{summary['status']}`",
            f"- reason_code: `{summary['reason_code']}`",
            f"- selected_rows: `{summary['selected_rows']}`",
            f"- queue_path: `{summary['queue_path']}`",
            "",
            "## Upstream",
            "",
            f"- step2_status: `{upstream['step2_status']}`",
            f"- step2_reason_code: `{upstream['step2_reason_code']}`",
            f"- step2_gate_path: `{upstream['step2_gate_path']}`",
            f"- step3_gate_path: `{upstream['step3_gate_path']}`",
            f"- step4_gate_path: `{upstream['step4_gate_path']}`",
            "",
            "## Counts",
            "",
            f"- total_queue_rows: `{counts['total_queue_rows']}`",
            f"- pass_rows: `{counts['pass_rows']}`",
            f"- fail_rows: `{counts['fail_rows']}`",
            f"- hold_rows: `{counts['hold_rows']}`",
        ]
    ) + "\n"


def persist_batch_logs(log_dir: Path, summary: dict[str, Any]) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(log_dir / LATEST_RUN_FILE, summary)
    append_jsonl(log_dir / RUN_HISTORY_FILE, summary)
    if summary["status"] != "PASS":
        append_jsonl(log_dir / RUN_FAILURE_FILE, summary)


def main() -> int:
    args = parse_args()
    batch_id = str(args.batch_id or f"DIRECTION_BATCH_{timestamp_slug()}")
    output_dir = repo_path(args.output_dir, "output_dir") if args.output_dir else default_output_dir(batch_id)
    log_dir = repo_path(args.log_dir, "log_dir")
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    goal_rows = load_dict_rows(CURRENT_GOAL_PATH)
    entry_rows = load_dict_rows(CURRENT_ENTRY_PATH)
    compliance_rows = load_dict_rows(CURRENT_COMPLIANCE_PATH)
    if not goal_rows:
        raise DirectionBatchError(f"Current goal input is missing data rows: {CURRENT_GOAL_PATH}")
    if not entry_rows:
        raise DirectionBatchError(f"Current direction input is missing data rows: {CURRENT_ENTRY_PATH}")

    goal_row = goal_rows[0]
    selected_row_indices = parse_row_indices(args.row_indices, len(entry_rows))
    step1_rules = load_step_rules("STEP1")
    step2_log = latest_json(STEP2_LOG_PATH)
    step2_status, step2_reason = latest_step2_state(step2_log)
    step2_gate_path, step2_rows = load_gate_rows_from_optional(args.step2_gate_csv, STEP2_GATE_FILE)
    step3_gate_path, step3_rows = load_gate_rows_from_optional(args.step3_gate_csv, STEP3_GATE_FILE)
    step4_gate_path, step4_rows = load_gate_rows_from_optional(args.step4_gate_csv, STEP4_GATE_FILE)

    queue_rows: list[dict[str, str]] = []

    for row_index in selected_row_indices:
        entry_row = entry_rows[row_index - 1]
        context = build_context(row_index, goal_row, entry_row, compliance_rows, step4_rows, step3_rows)
        step1_status, step1_reason, step1_snapshot = evaluate_step1(context, step1_rules)
        queue_rows.append(
            queue_row(
                batch_id=batch_id,
                context=context,
                keyword=context.direction_keyword,
                stage_code="STEP1_DIRECTION_GATE",
                item_type="direction",
                status=step1_status,
                reason_code=step1_reason,
                source=str(STANDARD_90_PATH),
                snapshot=step1_snapshot,
            )
        )

        keyword_items = build_keyword_items(context, step2_status, step2_reason, step2_gate_path, step2_rows, step2_log)
        for keyword_item in keyword_items:
            queue_rows.append(
                queue_row(
                    batch_id=batch_id,
                    context=context,
                    keyword=keyword_item.keyword,
                    stage_code="STEP2_KEYWORD_GATE",
                    item_type="keyword",
                    status=keyword_item.status if step1_status == "PASS" else "HOLD",
                    reason_code=keyword_item.reason_code if step1_status == "PASS" else "BLOCKED_BY_PREVIOUS_STAGE__STEP1",
                    source=keyword_item.source,
                    snapshot=keyword_item.snapshot,
                )
            )

            matched_step3 = match_gate_rows(step3_rows, context, keyword_item.keyword)
            step3_snapshot = {
                "formal_upstream_status": keyword_item.status,
                "matched_step3_gate_rows": matched_step3[:3],
                "step3_gate_path": str(step3_gate_path or ""),
            }
            if step1_status != "PASS":
                step3_gate_status = "HOLD"
                step3_gate_reason = "BLOCKED_BY_PREVIOUS_STAGE__STEP1"
            elif keyword_item.status != "PASS":
                step3_gate_status = "HOLD"
                step3_gate_reason = keyword_item.reason_code
            elif matched_step3:
                step3_gate_status = normalize_status(str(matched_step3[0].get("整体状态", "")).strip())
                step3_gate_reason = str(matched_step3[0].get("失败原因代码", "")).strip() or "PASS"
            else:
                step3_gate_status = "HOLD"
                step3_gate_reason = "STEP3_GATE_NOT_FOUND"

            queue_rows.append(
                queue_row(
                    batch_id=batch_id,
                    context=context,
                    keyword=keyword_item.keyword,
                    stage_code="STEP3_MARKET_GATE",
                    item_type="keyword",
                    status=step3_gate_status,
                    reason_code=step3_gate_reason,
                    source=str(step3_gate_path or STANDARD_90_PATH),
                    snapshot=step3_snapshot,
                )
            )

            if args.trigger_market_dry_run or args.trigger_market_live:
                market_status, market_reason, market_snapshot, market_artifact = market_trigger_result(
                    context=context,
                    keyword=keyword_item.keyword,
                    base_output_dir=output_dir,
                    base_log_dir=log_dir,
                    use_live_export=bool(args.trigger_market_live),
                )
            else:
                market_status, market_reason, market_snapshot, market_artifact = (
                    "HOLD",
                    "MARKET_TRIGGER_NOT_REQUESTED",
                    {"requested": False},
                    "",
                )

            queue_rows.append(
                queue_row(
                    batch_id=batch_id,
                    context=context,
                    keyword=keyword_item.keyword,
                    stage_code="STEP3_MARKET_TRIGGER",
                    item_type="keyword",
                    status=market_status,
                    reason_code=market_reason,
                    source=str(ROOT / "scripts" / "export_market_report.py"),
                    snapshot=market_snapshot,
                    output_artifact=market_artifact,
                )
            )

            matched_step4 = match_gate_rows(step4_rows, context, keyword_item.keyword)
            step4_snapshot = {
                "formal_upstream_status": step3_gate_status,
                "matched_step4_gate_rows": matched_step4[:3],
                "step4_gate_path": str(step4_gate_path or ""),
            }
            if step1_status != "PASS":
                step4_gate_status = "HOLD"
                step4_gate_reason = "BLOCKED_BY_PREVIOUS_STAGE__STEP1"
            elif keyword_item.status != "PASS":
                step4_gate_status = "HOLD"
                step4_gate_reason = keyword_item.reason_code
            elif matched_step4:
                step4_gate_status = normalize_status(str(matched_step4[0].get("整体状态", "")).strip())
                step4_gate_reason = str(matched_step4[0].get("失败原因代码", "")).strip() or "PASS"
            else:
                step4_gate_status = "HOLD"
                step4_gate_reason = "STEP4_GATE_NOT_FOUND"

            queue_rows.append(
                queue_row(
                    batch_id=batch_id,
                    context=context,
                    keyword=keyword_item.keyword,
                    stage_code="STEP4_BENCHMARK_GATE",
                    item_type="keyword",
                    status=step4_gate_status,
                    reason_code=step4_gate_reason,
                    source=str(step4_gate_path or STANDARD_90_PATH),
                    snapshot=step4_snapshot,
                )
            )

            if args.trigger_benchmark_live:
                benchmark_status, benchmark_reason, benchmark_snapshot, benchmark_artifact = benchmark_trigger_result(
                    context=context,
                    keyword_item=keyword_item,
                    base_output_dir=output_dir,
                    base_log_dir=log_dir,
                    build_after_export=bool(args.trigger_benchmark_build),
                )
            else:
                benchmark_status, benchmark_reason, benchmark_snapshot, benchmark_artifact = (
                    "HOLD",
                    "BENCHMARK_TRIGGER_NOT_REQUESTED",
                    {"requested": False},
                    "",
                )

            queue_rows.append(
                queue_row(
                    batch_id=batch_id,
                    context=context,
                    keyword=keyword_item.keyword,
                    stage_code="STEP4_BENCHMARK_TRIGGER",
                    item_type="keyword",
                    status=benchmark_status,
                    reason_code=benchmark_reason,
                    source=str(ROOT / "scripts" / "export_benchmark_competitors.py"),
                    snapshot=benchmark_snapshot,
                    output_artifact=benchmark_artifact,
                )
            )

    queue_path = ensure_within_repo(output_dir / QUEUE_FILE, "queue_path")
    write_csv_atomic(queue_path, QUEUE_HEADERS, [[row.get(header, "") for header in QUEUE_HEADERS] for row in queue_rows])

    pass_rows = len([row for row in queue_rows if row["status"] == "PASS"])
    fail_rows = len([row for row in queue_rows if row["status"] == "FAIL"])
    hold_rows = len([row for row in queue_rows if row["status"] == "HOLD"])
    if step2_status != "PASS":
        overall_status = "HOLD"
        overall_reason = f"BLOCKED_BY_UPSTREAM_CHAIN__{step2_reason}"
    elif fail_rows:
        overall_status = "FAIL"
        overall_reason = "BATCH_QUEUE_HAS_FAIL_ROWS"
    elif hold_rows:
        overall_status = "HOLD"
        overall_reason = "BATCH_QUEUE_HAS_HOLD_ROWS"
    else:
        overall_status = "PASS"
        overall_reason = "PASS"

    summary = {
        "timestamp": iso_now(),
        "module": "direction_batch_orchestrator",
        "batch_id": batch_id,
        "status": overall_status,
        "reason_code": overall_reason,
        "selected_rows": selected_row_indices,
        "queue_path": str(queue_path),
        "output_dir": str(output_dir),
        "log_dir": str(log_dir),
        "upstream": {
            "step2_status": step2_status,
            "step2_reason_code": step2_reason,
            "step2_log_path": str(STEP2_LOG_PATH),
            "step2_gate_path": str(step2_gate_path or ""),
            "step3_gate_path": str(step3_gate_path or ""),
            "step4_gate_path": str(step4_gate_path or ""),
        },
        "counts": {
            "total_queue_rows": len(queue_rows),
            "pass_rows": pass_rows,
            "fail_rows": fail_rows,
            "hold_rows": hold_rows,
        },
        "requested_triggers": {
            "market_dry_run": bool(args.trigger_market_dry_run),
            "market_live": bool(args.trigger_market_live),
            "benchmark_live": bool(args.trigger_benchmark_live),
            "benchmark_build": bool(args.trigger_benchmark_build),
        },
    }

    write_json_atomic(output_dir / SUMMARY_JSON, summary)
    (output_dir / SUMMARY_MD).write_text(summary_markdown(summary), encoding="utf-8")
    persist_batch_logs(log_dir, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if overall_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
