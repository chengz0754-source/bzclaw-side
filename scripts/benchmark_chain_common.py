from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from keyword_chain_common import (
    OUTPUTS_ROOT,
    PROFILE_DIR,
    REPLAY_PROFILE_DIR,
    ROOT,
    append_jsonl,
    bool_cn,
    ensure_within_repo,
    format_number,
    iso_now,
    load_csv_rows,
    parse_int_value,
    preferred_sellersprite_profile_dir,
    profile_has_content,
    safe_float,
    timestamp_slug,
    write_csv_atomic,
    write_json_atomic,
)


BENCHMARK_LOG_DIR = ROOT / "logs" / "benchmark_chain"
STANDARD_90_PATH = ROOT / "templates" / "selection_canonical_standards" / "90_下推参数表.csv"
STANDARD_99_PATH = ROOT / "templates" / "selection_canonical_standards" / "99_字段数据标准总表.csv"
CURRENT_GOAL_PATH = ROOT / "inputs" / "selection_run_current" / "00_选品运行目标与边界.csv"
CURRENT_ENTRY_PATH = ROOT / "inputs" / "selection_run_current" / "01_市场入口与筛选参数.csv"
STEP2_GATE_FILE = "22_关键词证据词池下推结果.csv"
STEP1_RAW_FILE = "10_产品样本原始结果.csv"
STEP1_SEED_FILE = "11_产品样本种子池.csv"
STEP1_GATE_FILE = "12_产品样本下推结果.csv"
STEP3_CLEANED_FILE = "31_市场调研清洗结果.csv"
STEP3_GATE_FILE = "32_市场调研下推结果.csv"
STEP4_RAW_FILE = "40_竞品基准结果.csv"
STEP4_SEED_FILE = "41_候选产品种子池.csv"
STEP4_GATE_FILE = "42_竞品基准下推结果.csv"
BENCHMARK_RAW_ARTIFACT = "benchmark_competitor_raw.json"
OUTPUT_INDEX_CSV = "benchmark_chain_output_index.csv"
OUTPUT_INDEX_MD = "benchmark_chain_output_index.md"


class BenchmarkChainError(RuntimeError):
    def __init__(self, message: str, reason_code: str = "BENCHMARK_CHAIN_ERROR") -> None:
        super().__init__(message)
        self.reason_code = reason_code


@dataclass
class BenchmarkContext:
    run_name: str
    direction_id: str
    keyword: str
    category_hint: str
    site: str
    days: int
    sample_top_n: int
    max_candidate_samples: int | None
    context_row_index: int
    context_source: str


@dataclass
class SeedContext:
    source_step: str
    source_gate_path: str
    source_cleaned_path: str
    seed_keyword: str
    candidate_market_name: str
    market_path: str
    upstream_batch_id: str
    upstream_status: str


def current_context_map(row_index: int) -> dict[str, str]:
    if row_index <= 0:
        raise BenchmarkChainError("--context-row-index must be >= 1.", "INVALID_CONTEXT_INDEX")
    if not CURRENT_GOAL_PATH.exists():
        raise BenchmarkChainError(f"Current goal CSV is missing: {CURRENT_GOAL_PATH}", "CURRENT_GOAL_MISSING")
    if not CURRENT_ENTRY_PATH.exists():
        raise BenchmarkChainError(f"Current entry CSV is missing: {CURRENT_ENTRY_PATH}", "CURRENT_ENTRY_MISSING")

    goal_rows = load_csv_rows(CURRENT_GOAL_PATH)
    entry_rows = load_csv_rows(CURRENT_ENTRY_PATH)
    if len(goal_rows) < 2:
        raise BenchmarkChainError(f"Current goal CSV has no data row: {CURRENT_GOAL_PATH}", "CURRENT_GOAL_EMPTY")
    if len(entry_rows) <= row_index:
        raise BenchmarkChainError(
            f"--context-row-index {row_index} is out of range for {CURRENT_ENTRY_PATH}; available rows: {max(len(entry_rows) - 1, 0)}",
            "CURRENT_ENTRY_OUT_OF_RANGE",
        )

    goal_map = {header: goal_rows[1][idx] if idx < len(goal_rows[1]) else "" for idx, header in enumerate(goal_rows[0])}
    entry_map = {header: entry_rows[row_index][idx] if idx < len(entry_rows[row_index]) else "" for idx, header in enumerate(entry_rows[0])}
    return {
        "goal_run_name": goal_map.get("运行名称", "").strip(),
        "entry_run_name": entry_map.get("运行名称", "").strip(),
        "direction_id": entry_map.get("方向ID", "").strip(),
        "keyword": entry_map.get("方向词", "").strip(),
        "category_hint": entry_map.get("类目提示", "").strip(),
        "site": entry_map.get("站点", "").strip().upper(),
        "days": entry_map.get("时间范围_天", "").strip(),
        "sample_top_n": entry_map.get("样本数前N", "").strip(),
        "max_candidate_samples": entry_map.get("每个方向最大候选样品数", "").strip(),
    }


def resolve_context_from_namespace(namespace: Any, require_direction_id: bool = False) -> BenchmarkContext:
    row_index = int(getattr(namespace, "context_row_index", 1))
    current = current_context_map(row_index)
    run_name = str(getattr(namespace, "run_name", "") or current.get("entry_run_name") or current.get("goal_run_name") or "").strip()
    direction_id = str(getattr(namespace, "direction_id", "") or current.get("direction_id") or "").strip()
    keyword = str(getattr(namespace, "keyword", "") or current.get("keyword") or "").strip()
    category_hint = str(getattr(namespace, "category_hint", "") or current.get("category_hint") or "").strip()
    site = str(getattr(namespace, "site", "") or current.get("site") or "").strip().upper()
    days = parse_int_value(getattr(namespace, "days", None) if getattr(namespace, "days", None) is not None else current.get("days") or 30, "时间范围_天")
    sample_top_n = parse_int_value(
        getattr(namespace, "sample_top_n", None) if getattr(namespace, "sample_top_n", None) is not None else current.get("sample_top_n") or 100,
        "样本数前N",
    )
    raw_max_candidate_samples = getattr(namespace, "max_candidate_samples", None)
    if raw_max_candidate_samples is None:
        raw_max_candidate_samples = current.get("max_candidate_samples") or ""
    max_candidate_samples = (
        parse_int_value(raw_max_candidate_samples, "每个方向最大候选样品数") if str(raw_max_candidate_samples).strip() else None
    )

    missing: list[str] = []
    if not run_name:
        missing.append("运行名称")
    if not keyword:
        missing.append("方向词")
    if not site:
        missing.append("站点")
    if require_direction_id and not direction_id:
        missing.append("方向ID")
    if missing:
        raise BenchmarkChainError(
            "Missing required current-input context: " + ", ".join(missing) + ". Fill inputs/selection_run_current/01 manually or pass explicit CLI overrides.",
            "MISSING_REQUIRED_CONTEXT",
        )

    return BenchmarkContext(
        run_name=run_name,
        direction_id=direction_id,
        keyword=keyword,
        category_hint=category_hint,
        site=site,
        days=days,
        sample_top_n=sample_top_n,
        max_candidate_samples=max_candidate_samples,
        context_row_index=row_index,
        context_source=f"inputs/selection_run_current/01 row {row_index}",
    )


def default_output_dir() -> Path:
    return ensure_within_repo(OUTPUTS_ROOT / timestamp_slug() / "02_generated_outputs", "output_dir")


def output_dir_from_namespace(namespace: Any) -> Path:
    raw_output_dir = getattr(namespace, "output_dir", None)
    if raw_output_dir:
        output_dir = Path(raw_output_dir).expanduser()
        if not output_dir.is_absolute():
            output_dir = ROOT / output_dir
        return ensure_within_repo(output_dir, "output_dir")
    return default_output_dir()


def log_dir_from_namespace(namespace: Any) -> Path:
    raw_log_dir = getattr(namespace, "log_dir", None) or str(BENCHMARK_LOG_DIR)
    log_dir = Path(raw_log_dir).expanduser()
    if not log_dir.is_absolute():
        log_dir = ROOT / log_dir
    return ensure_within_repo(log_dir, "log_dir")


def load_field_order(file_name: str) -> list[str]:
    rows = list(csv.DictReader(STANDARD_99_PATH.read_text(encoding="utf-8-sig").splitlines()))
    return [row["field_name"] for row in rows if row["file_name"] == file_name]


def load_step4_rules() -> list[dict[str, str]]:
    rows = list(csv.DictReader(STANDARD_90_PATH.read_text(encoding="utf-8-sig").splitlines()))
    filtered = [row for row in rows if row.get("step_code") == "STEP4" and row.get("enabled") == "TRUE"]
    filtered.sort(key=lambda row: parse_int_value(row.get("tie_breaker_rank") or 999, "tie_breaker_rank"))
    return filtered


def persist_run_summary(log_dir: Path, latest_file_name: str, history_file_name: str, summary: dict[str, Any]) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    latest_path = log_dir / latest_file_name
    history_path = log_dir / history_file_name
    write_json_atomic(latest_path, summary)
    append_jsonl(history_path, summary)
    if summary.get("status") != "PASS":
        append_jsonl(log_dir / "benchmark_failures.jsonl", summary)


def load_csv_dict_rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()))


def latest_generated_files(file_name: str) -> list[Path]:
    candidates = sorted(
        ensure_within_repo(OUTPUTS_ROOT, "outputs_root").glob(f"*/02_generated_outputs/{file_name}"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return [ensure_within_repo(path, file_name) for path in candidates]


def match_context_value(row: dict[str, str], key: str, expected: str) -> bool:
    if not expected:
        return True
    return str(row.get(key, "")).strip().casefold() == expected.strip().casefold()


def match_context_any(row: dict[str, str], keys: tuple[str, ...], expected: str) -> bool:
    if not expected:
        return True
    normalized_expected = expected.strip().casefold()
    for key in keys:
        value = str(row.get(key, "")).strip()
        if value and value.casefold() == normalized_expected:
            return True
    return False


def resolve_seed_from_step1(context: BenchmarkContext, gate_path_override: str | None = None, seed_path_override: str | None = None) -> SeedContext:
    candidate_gate_paths = [ensure_within_repo(Path(gate_path_override), "step1_gate_csv")] if gate_path_override else latest_generated_files(STEP1_GATE_FILE)
    if not candidate_gate_paths:
        raise BenchmarkChainError(
            "No STEP1 product gate output was found under outputs/selection_runs/. Run the product-entry chain first or pass --product-gate-csv explicitly.",
            "STEP1_GATE_MISSING",
        )

    if gate_path_override and not candidate_gate_paths[0].exists():
        raise BenchmarkChainError(
            f"Explicit STEP1 product gate CSV does not exist: {candidate_gate_paths[0]}",
            "STEP1_GATE_MISSING",
        )
    if seed_path_override:
        explicit_seed_path = ensure_within_repo(Path(seed_path_override), "step1_seed_csv")
        if not explicit_seed_path.exists():
            raise BenchmarkChainError(
                f"Explicit STEP1 product seed CSV does not exist: {explicit_seed_path}",
                "STEP1_SEED_MISSING",
            )

    for gate_path in candidate_gate_paths:
        rows = load_csv_dict_rows(gate_path)
        matching_rows = [
            row
            for row in rows
            if str(row.get("整体状态", "")).strip().upper() == "PASS"
            and match_context_value(row, "站点", context.site)
            and match_context_any(row, ("关键词", "方向词"), context.keyword)
        ]
        if not matching_rows:
            continue

        selected = matching_rows[0]
        seed_path = ensure_within_repo(Path(seed_path_override), "step1_seed_csv") if seed_path_override else gate_path.with_name(STEP1_SEED_FILE)
        return SeedContext(
            source_step="STEP1_PRODUCT_GATE",
            source_gate_path=str(gate_path),
            source_cleaned_path=str(seed_path if seed_path.exists() else ""),
            seed_keyword=str(selected.get("竞品查询词", "") or selected.get("关键词", "") or context.keyword).strip(),
            candidate_market_name=str(selected.get("候选市场名称", "") or selected.get("关键词", "") or context.keyword).strip(),
            market_path=str(selected.get("市场路径", "")).strip(),
            upstream_batch_id=str(selected.get("下推批次号", "")).strip(),
            upstream_status=str(selected.get("整体状态", "")).strip(),
        )

    raise BenchmarkChainError(
        "No PASS row in STEP1 product gate outputs matched the current context.",
        "STEP1_PASS_SEED_MISSING",
    )


def resolve_seed_from_step3(context: BenchmarkContext, gate_path_override: str | None = None, cleaned_path_override: str | None = None) -> SeedContext:
    candidate_gate_paths = [ensure_within_repo(Path(gate_path_override), "step3_gate_csv")] if gate_path_override else latest_generated_files(STEP3_GATE_FILE)
    if not candidate_gate_paths:
        raise BenchmarkChainError(
            "No STEP3 gate output was found under outputs/selection_runs/. Run the STEP3 market-chain builder first or pass --step3-gate-csv explicitly.",
            "STEP3_GATE_MISSING",
        )

    if gate_path_override and not candidate_gate_paths[0].exists():
        raise BenchmarkChainError(
            f"Explicit STEP3 gate CSV does not exist: {candidate_gate_paths[0]}",
            "STEP3_GATE_MISSING",
        )
    if cleaned_path_override:
        explicit_cleaned_path = ensure_within_repo(Path(cleaned_path_override), "step3_cleaned_csv")
        if not explicit_cleaned_path.exists():
            raise BenchmarkChainError(
                f"Explicit STEP3 cleaned CSV does not exist: {explicit_cleaned_path}",
                "STEP3_CLEANED_MISSING",
            )

    for gate_path in candidate_gate_paths:
        rows = load_csv_dict_rows(gate_path)
        matching_rows = [
            row
            for row in rows
            if str(row.get("整体状态", "")).strip().upper() == "PASS"
            and match_context_value(row, "站点", context.site)
            and match_context_value(row, "关键词", context.keyword)
        ]
        if not matching_rows:
            continue
        selected = matching_rows[0]
        cleaned_path = ensure_within_repo(Path(cleaned_path_override), "step3_cleaned_csv") if cleaned_path_override else gate_path.with_name(STEP3_CLEANED_FILE)
        market_path = ""
        if cleaned_path.exists():
            cleaned_rows = load_csv_dict_rows(cleaned_path)
            for cleaned_row in cleaned_rows:
                if (
                    match_context_value(cleaned_row, "运行名称", selected.get("运行名称", ""))
                    and match_context_value(cleaned_row, "关键词", selected.get("关键词", ""))
                    and match_context_value(cleaned_row, "站点", selected.get("站点", ""))
                    and match_context_value(cleaned_row, "候选市场名称", selected.get("候选市场名称", ""))
                ):
                    market_path = str(cleaned_row.get("市场路径", "")).strip()
                    break
        return SeedContext(
            source_step="STEP3_MARKET_GATE",
            source_gate_path=str(gate_path),
            source_cleaned_path=str(cleaned_path if cleaned_path.exists() else ""),
            seed_keyword=str(selected.get("候选市场名称", "") or selected.get("关键词", "")).strip(),
            candidate_market_name=str(selected.get("候选市场名称", "") or selected.get("关键词", "")).strip(),
            market_path=market_path,
            upstream_batch_id=str(selected.get("下推批次号", "")).strip(),
            upstream_status=str(selected.get("整体状态", "")).strip(),
        )

    raise BenchmarkChainError(
        "No PASS row in STEP3 gate outputs matched the current context. The benchmark chain requires a PASS market seed or a PASS STEP2 keyword seed.",
        "STEP3_PASS_SEED_MISSING",
    )


def resolve_seed_from_upstream(
    context: BenchmarkContext,
    product_gate_path_override: str | None = None,
    product_seed_path_override: str | None = None,
    step3_gate_path_override: str | None = None,
    step3_cleaned_path_override: str | None = None,
) -> SeedContext:
    errors: list[str] = []

    try:
        return resolve_seed_from_step1(context, product_gate_path_override, product_seed_path_override)
    except BenchmarkChainError as exc:
        errors.append(exc.reason_code)

    try:
        return resolve_seed_from_step3(context, step3_gate_path_override, step3_cleaned_path_override)
    except BenchmarkChainError as exc:
        errors.append(exc.reason_code)
        raise BenchmarkChainError(
            "No PASS row in STEP1 product gate or STEP3 market gate matched the current context.",
            "__OR__".join(errors),
        ) from exc


def write_markdown(path: Path, content: str) -> None:
    ensure_within_repo(path, "markdown_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def stable_id(prefix: str, *parts: str) -> str:
    raw = "|".join(part.strip() for part in parts if part is not None)
    import hashlib

    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}_{digest}"


def clean_number(value: Any) -> str:
    numeric = safe_float(value)
    return format_number(numeric)


def raw_output_index_rows(output_dir: Path, raw_artifact_path: Path, raw_csv_path: Path, seed_path: Path, gate_path: Path, item_count: int, gate_status: str) -> list[dict[str, str]]:
    return [
        {
            "artifact_id": "STEP4_RAW_JSON",
            "layer": "raw_layer",
            "artifact_path": str(raw_artifact_path),
            "status": "CREATED",
            "notes": f"Structured benchmark raw artifact with {item_count} SellerSprite items.",
        },
        {
            "artifact_id": "STEP4_RAW_CSV",
            "layer": "raw_layer",
            "artifact_path": str(raw_csv_path),
            "status": "CREATED",
            "notes": "Canonical 40_竞品基准结果.csv raw benchmark layer.",
        },
        {
            "artifact_id": "STEP4_SEED_POOL",
            "layer": "seed_pool_layer",
            "artifact_path": str(seed_path),
            "status": "CREATED",
            "notes": "Canonical 41_候选产品种子池.csv deduped seed pool.",
        },
        {
            "artifact_id": "STEP4_GATE",
            "layer": "gate_result_layer",
            "artifact_path": str(gate_path),
            "status": "CREATED",
            "notes": f"Canonical 42_竞品基准下推结果.csv with overall status {gate_status}.",
        },
        {
            "artifact_id": "OUTPUT_DIR",
            "layer": "run_output_layer",
            "artifact_path": str(output_dir),
            "status": "CREATED",
            "notes": "Ignored runtime output directory for the benchmark chain.",
        },
    ]
