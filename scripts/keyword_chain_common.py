from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass


ROOT = Path(__file__).resolve().parents[1]
STORAGE_STATE_PATH = ROOT / "playwright" / "auth" / "sellersprite.storage_state.json"
PROFILE_DIR = ROOT / "playwright" / "profiles" / "sellersprite-main"
REPLAY_PROFILE_DIR = ROOT / "playwright" / "profiles" / "sellersprite-replay"
KEYWORD_LOG_DIR = ROOT / "logs" / "keyword_chain"
OUTPUTS_ROOT = ROOT / "outputs" / "selection_runs"
CURRENT_GOAL_RELATIVE = Path("inputs/selection_run_current/00_选品运行目标与边界.csv")
CURRENT_ENTRY_RELATIVE = Path("inputs/selection_run_current/01_市场入口与筛选参数.csv")
STANDARD_90_RELATIVE = Path("templates/selection_canonical_standards/90_下推参数表.csv")
STANDARD_99_RELATIVE = Path("templates/selection_canonical_standards/99_字段数据标准总表.csv")
CSV_READ_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk")
GUEST_MARKERS = (
    "未登录",
    "游客",
    "卖家精灵登录",
    "立即登录",
    "主人~ 您当前是游客身份",
    "建议 立即登录 后使用",
    "Log In",
    "Sign Up",
)

class KeywordChainError(RuntimeError):
    def __init__(self, message: str, reason_code: str = "KEYWORD_CHAIN_ERROR") -> None:
        super().__init__(message)
        self.reason_code = reason_code


@dataclass
class KeywordContext:
    run_name: str
    direction_id: str
    keyword: str
    category_hint: str
    site: str
    days: int
    sample_top_n: int
    max_push_keywords: int | None
    context_row_index: int
    context_source: str


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_within_repo(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise KeywordChainError(f"{label} is outside the repo root: {resolved}", "PATH_OUTSIDE_REPO")
    return resolved


def profile_has_content(profile_dir: Path) -> bool:
    return profile_dir.exists() and any(profile_dir.iterdir())


def preferred_sellersprite_profile_dir() -> Path | None:
    for candidate in (REPLAY_PROFILE_DIR, PROFILE_DIR):
        if profile_has_content(candidate):
            return ensure_within_repo(candidate, "preferred_sellersprite_profile_dir")
    return None


def load_csv_rows(path: Path) -> list[list[str]]:
    raw_bytes = path.read_bytes()
    decode_errors: list[str] = []
    for encoding in CSV_READ_ENCODINGS:
        try:
            return list(csv.reader(raw_bytes.decode(encoding).splitlines()))
        except UnicodeDecodeError as exc:
            decode_errors.append(f"{encoding}@{exc.start}:{exc.reason}")
    detail = " | ".join(decode_errors) or "unknown decode failure"
    raise KeywordChainError(
        f"Failed to read CSV with supported encodings: {path} | {detail}",
        "CSV_DECODE_FAILED",
    )


def parse_int_value(raw_value: str | int | None, field_name: str) -> int:
    try:
        return int(raw_value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise KeywordChainError(f"{field_name} must be an integer value, got: {raw_value!r}", "INVALID_INTEGER") from exc


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    if text.endswith("%"):
        text = text[:-1].strip()
    try:
        return float(text)
    except ValueError:
        return None


def format_number(value: float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    if float(value).is_integer():
        return str(int(value))
    return f"{float(value):.4f}".rstrip("0").rstrip(".")


def normalize_keyword_text(value: Any) -> str:
    text = str(value or "").casefold()
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def bool_cn(flag: bool) -> str:
    return "是" if flag else "否"


def compact_text(value: str) -> str:
    return " ".join(str(value or "").split())


def page_guest_markers(body_text: str) -> list[str]:
    compacted = compact_text(body_text)
    return [marker for marker in GUEST_MARKERS if marker.lower() in compacted.lower()]


def write_json_atomic(path: Path, payload: Any) -> None:
    ensure_within_repo(path, "json_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def append_jsonl(path: Path, payload: Any) -> None:
    ensure_within_repo(path, "jsonl_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_csv_atomic(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    ensure_within_repo(path, "csv_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
    tmp_path.replace(path)


def load_current_context(row_index: int) -> dict[str, str]:
    if row_index <= 0:
        raise KeywordChainError("--context-row-index must be >= 1.", "INVALID_CONTEXT_INDEX")

    goal_path = ROOT / CURRENT_GOAL_RELATIVE
    entry_path = ROOT / CURRENT_ENTRY_RELATIVE
    if not goal_path.exists():
        raise KeywordChainError(f"Current goal CSV is missing: {goal_path}", "CURRENT_GOAL_MISSING")
    if not entry_path.exists():
        raise KeywordChainError(f"Current market entry CSV is missing: {entry_path}", "CURRENT_ENTRY_MISSING")

    goal_rows = load_csv_rows(goal_path)
    entry_rows = load_csv_rows(entry_path)
    if len(goal_rows) < 2:
        raise KeywordChainError(f"Current goal CSV has no data row: {goal_path}", "CURRENT_GOAL_EMPTY")
    if len(entry_rows) <= row_index:
        raise KeywordChainError(
            f"--context-row-index {row_index} is out of range for {entry_path}; available rows: {max(len(entry_rows) - 1, 0)}",
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
        "max_push_keywords": entry_map.get("每个方向最大下推关键词数", "").strip(),
    }


def resolve_context_from_namespace(namespace: Any, require_direction_id: bool = False) -> KeywordContext:
    row_index = int(getattr(namespace, "context_row_index", 1))
    current = load_current_context(row_index)
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
    raw_max_push = getattr(namespace, "max_push_keywords", None)
    if raw_max_push is None:
        raw_max_push = current.get("max_push_keywords") or ""
    max_push_keywords = parse_int_value(raw_max_push, "每个方向最大下推关键词数") if str(raw_max_push).strip() else None

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
        raise KeywordChainError(
            "Missing required current-input context: " + ", ".join(missing) + ". Fill inputs/selection_run_current/01 manually or pass explicit CLI overrides.",
            "MISSING_REQUIRED_CONTEXT",
        )

    return KeywordContext(
        run_name=run_name,
        direction_id=direction_id,
        keyword=keyword,
        category_hint=category_hint,
        site=site,
        days=days,
        sample_top_n=sample_top_n,
        max_push_keywords=max_push_keywords,
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
    raw_log_dir = getattr(namespace, "log_dir", None) or str(KEYWORD_LOG_DIR)
    log_dir = Path(raw_log_dir).expanduser()
    if not log_dir.is_absolute():
        log_dir = ROOT / log_dir
    return ensure_within_repo(log_dir, "log_dir")


def load_field_order(file_name: str) -> list[str]:
    standard_path = ROOT / STANDARD_99_RELATIVE
    rows = list(csv.DictReader(standard_path.read_text(encoding="utf-8-sig").splitlines()))
    return [row["field_name"] for row in rows if row["file_name"] == file_name]


def load_step2_rules() -> list[dict[str, str]]:
    standard_path = ROOT / STANDARD_90_RELATIVE
    rows = list(csv.DictReader(standard_path.read_text(encoding="utf-8-sig").splitlines()))
    filtered = [row for row in rows if row.get("step_code") == "STEP2" and row.get("enabled") == "TRUE"]
    filtered.sort(key=lambda row: parse_int_value(row.get("tie_breaker_rank") or 999, "tie_breaker_rank"))
    return filtered


def step2_rule_map() -> dict[str, dict[str, str]]:
    return {row["rule_id"]: row for row in load_step2_rules()}


def traffic_cost_index_from_bid(bid_value: Any) -> str:
    bid = safe_float(bid_value)
    if bid is None:
        return ""
    return format_number(min(100.0, max(0.0, bid * 100.0)))


def persist_run_summary(
    log_dir: Path,
    latest_file_name: str,
    history_file_name: str,
    summary: dict[str, Any],
) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    latest_path = log_dir / latest_file_name
    history_path = log_dir / history_file_name
    write_json_atomic(latest_path, summary)
    append_jsonl(history_path, summary)
    if summary.get("status") != "PASS":
        append_jsonl(log_dir / "keyword_failures.jsonl", summary)
