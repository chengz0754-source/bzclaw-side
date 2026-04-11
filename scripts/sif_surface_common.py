from __future__ import annotations

import csv
import hashlib
import json
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
PROFILE_DIR = ROOT / "playwright" / "profiles" / "sif-main"
STORAGE_STATE_PATH = ROOT / "playwright" / "auth" / "sif.storage_state.json"
LOG_DIR = ROOT / "logs" / "sif_surfaces"
OUTPUTS_ROOT = ROOT / "outputs" / "selection_runs"
STANDARD_99_PATH = ROOT / "templates" / "selection_canonical_standards" / "99_字段数据标准总表.csv"

HOME_URL = "https://www.sif.com/"
USER_INFO_URL = "https://www.sif.com/api/user/basic/info"
LOGIN_QR_URL = "https://www.sif.com/api/wx/getWechatQrImg"

CSV_READ_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk")
MARKETING_MARKERS = (
    "免费使用插件",
    "注册免费领会员",
    "40W+ 亚马逊卖家在用的关键词运营工具",
    "功能介绍",
    "生态中心",
)
DETAIL_ROUTE_MAP = {
    "reverse": "/reverse",
    "timemachine-traffic": "/timemachine-traffic",
}
SEARCH_ROUTE_MAP = {
    "snapshot": "/snapshot",
    "dailyrank": "/dailyrank",
    "hourlyrank": "/hourlyrank",
    "search": "/search",
}
BROWSER_CANDIDATES: list[tuple[str, dict[str, Any]]] = [
    ("msedge_channel", {"channel": "msedge"}),
    ("chrome_channel", {"channel": "chrome"}),
    ("bundled_chromium", {}),
]


class SIFSurfaceError(RuntimeError):
    def __init__(self, message: str, reason_code: str = "SIF_SURFACE_ERROR") -> None:
        super().__init__(message)
        self.reason_code = reason_code


@dataclass
class SurfaceContext:
    run_name: str
    direction_id: str
    keyword: str
    sample_id: str
    sample_asin: str
    country: str
    candidate_pool_path: str
    candidate_source: str


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_within_repo(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise SIFSurfaceError(f"{label} is outside the repo root: {resolved}", "PATH_OUTSIDE_REPO")
    return resolved


def load_csv_rows(path: Path) -> list[list[str]]:
    raw_bytes = path.read_bytes()
    decode_errors: list[str] = []
    for encoding in CSV_READ_ENCODINGS:
        try:
            return list(csv.reader(raw_bytes.decode(encoding).splitlines()))
        except UnicodeDecodeError as exc:
            decode_errors.append(f"{encoding}@{exc.start}:{exc.reason}")
    detail = " | ".join(decode_errors) or "unknown decode failure"
    raise SIFSurfaceError(
        f"Failed to read CSV with supported encodings: {path} | {detail}",
        "CSV_DECODE_FAILED",
    )


def load_dict_rows(path: Path) -> list[dict[str, str]]:
    rows = load_csv_rows(path)
    if not rows:
        return []
    headers = rows[0]
    return [
        {header: row[idx] if idx < len(row) else "" for idx, header in enumerate(headers)}
        for row in rows[1:]
    ]


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


def load_field_order(file_name: str) -> list[str]:
    rows = load_csv_rows(STANDARD_99_PATH)
    headers = rows[0]
    file_header = "文件名" if "文件名" in headers else "file_name" if "file_name" in headers else None
    field_header = "字段名" if "字段名" in headers else "field_name" if "field_name" in headers else None
    if file_header is None or field_header is None:
        raise SIFSurfaceError("99_字段数据标准总表.csv is missing required headers.", "STANDARD_99_HEADERS_MISSING")
    file_idx = headers.index(file_header)
    field_idx = headers.index(field_header)

    fields = [row[field_idx].strip() for row in rows[1:] if row[file_idx].strip() == file_name]
    if not fields:
        raise SIFSurfaceError(f"No field definitions found in 99 master for {file_name}.", "STANDARD_99_FILE_MISSING")
    return fields


def compact_text(value: str) -> str:
    return " ".join(str(value or "").split())


def marketing_fallback_detected(body_text: str) -> bool:
    compacted = compact_text(body_text)
    return all(marker in compacted for marker in MARKETING_MARKERS[:3])


def profile_has_content(profile_dir: Path = PROFILE_DIR) -> bool:
    if not profile_dir.exists():
        return False
    return any(profile_dir.iterdir())


def probe_browsers(playwright) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    results: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    for name, kwargs in BROWSER_CANDIDATES:
        result: dict[str, Any] = {"name": name, "channel": kwargs.get("channel", "bundled")}
        try:
            browser = playwright.chromium.launch(headless=True, **kwargs)
            page = browser.new_page()
            page.goto(HOME_URL, wait_until="domcontentloaded", timeout=30000)
            result["status"] = "PASS"
            result["final_url"] = page.url
            result["title"] = page.title()
            browser.close()
            if selected is None:
                selected = {"name": name, "channel": kwargs.get("channel", "bundled"), "kwargs": kwargs}
        except Exception as exc:
            result["status"] = "FAIL"
            result["error"] = str(exc)
        results.append(result)

    if selected is None:
        raise SIFSurfaceError("No Chromium-family browser candidate could open SIF.", "NO_BROWSER_CANDIDATE")
    return results, selected


def stable_sample_id(sample_asin: str, keyword: str) -> str:
    digest = hashlib.sha1(f"{sample_asin}|{keyword}".encode("utf-8")).hexdigest().upper()[:10]
    return f"SIF_TMP_{digest}"


def newest_candidate_pool_paths() -> list[Path]:
    pattern = OUTPUTS_ROOT.glob("*/02_generated_outputs/60_候选样品池.csv")
    return sorted((ensure_within_repo(path, "candidate_pool_path") for path in pattern), key=lambda p: p.stat().st_mtime, reverse=True)


def resolve_surface_context(
    *,
    run_name: str | None,
    direction_id: str | None,
    keyword: str | None,
    sample_id: str | None,
    sample_asin: str | None,
    country: str | None,
    candidate_pool_csv: str | None,
    candidate_index: int,
) -> SurfaceContext:
    candidate_path = None
    if candidate_pool_csv:
        candidate_path = Path(candidate_pool_csv).expanduser()
        if not candidate_path.is_absolute():
            candidate_path = ROOT / candidate_path
        candidate_path = ensure_within_repo(candidate_path, "candidate_pool_csv")
        if not candidate_path.exists():
            raise SIFSurfaceError(f"candidate_pool_csv does not exist: {candidate_path}", "CANDIDATE_POOL_MISSING")
    else:
        latest = newest_candidate_pool_paths()
        if latest:
            candidate_path = latest[0]

    candidate_row: dict[str, str] = {}
    candidate_source = "cli_only"
    if candidate_path is not None:
        candidate_rows = load_dict_rows(candidate_path)
        if candidate_rows:
            row_number = max(candidate_index, 1)
            if row_number > len(candidate_rows):
                raise SIFSurfaceError(
                    f"candidate_index {row_number} exceeds available candidate rows {len(candidate_rows)} in {candidate_path}",
                    "CANDIDATE_INDEX_OUT_OF_RANGE",
                )
            candidate_row = candidate_rows[row_number - 1]
            candidate_source = f"{candidate_path} row {row_number}"

    resolved_run_name = str(run_name or candidate_row.get("运行名称") or "").strip()
    resolved_direction_id = str(direction_id or candidate_row.get("方向ID") or "").strip()
    resolved_keyword = str(keyword or candidate_row.get("核心关键词") or candidate_row.get("方向词") or "").strip()
    resolved_sample_asin = str(sample_asin or candidate_row.get("样品ASIN") or "").strip().upper()
    resolved_sample_id = str(sample_id or candidate_row.get("样品ID") or "").strip()
    resolved_country = str(country or candidate_row.get("站点") or "US").strip().upper()

    if resolved_sample_asin and not resolved_sample_id:
        resolved_sample_id = stable_sample_id(resolved_sample_asin, resolved_keyword)

    missing: list[str] = []
    if not resolved_run_name:
        missing.append("运行名称")
    if not resolved_direction_id:
        missing.append("方向ID")
    if not resolved_keyword:
        missing.append("关键词")
    if not resolved_sample_asin:
        missing.append("样品ASIN")
    if not resolved_sample_id:
        missing.append("样品ID")
    if missing:
        raise SIFSurfaceError(
            "Missing required surface context: " + ", ".join(missing) + ". Pass explicit CLI overrides or provide a valid 60_候选样品池.csv source.",
            "MISSING_SURFACE_CONTEXT",
        )

    return SurfaceContext(
        run_name=resolved_run_name,
        direction_id=resolved_direction_id,
        keyword=resolved_keyword,
        sample_id=resolved_sample_id,
        sample_asin=resolved_sample_asin,
        country=resolved_country,
        candidate_pool_path=str(candidate_path) if candidate_path is not None else "",
        candidate_source=candidate_source,
    )


def auth_probe(request_context) -> dict[str, Any]:
    result: dict[str, Any] = {
        "authenticated": False,
        "http_status": None,
        "code": None,
        "message": "",
        "payload": {},
        "error": "",
    }
    try:
        response = request_context.get(USER_INFO_URL, timeout=30000)
        result["http_status"] = response.status
        payload = response.json()
        result["payload"] = payload
        result["code"] = payload.get("code")
        result["message"] = str(payload.get("message", "")).strip()
        result["authenticated"] = payload.get("code") not in (-10, None)
    except Exception as exc:
        result["error"] = str(exc)
    return result


def default_output_dir(batch_id: str) -> Path:
    return ensure_within_repo(OUTPUTS_ROOT / batch_id / "02_generated_outputs", "output_dir")


def route_url(route_path: str, country: str, *, asin: str | None = None) -> str:
    if asin:
        return f"https://www.sif.com{route_path}?asin={asin}&country={country}"
    return f"https://www.sif.com{route_path}?country={country}"


def page_snapshot(page) -> dict[str, Any]:
    body_text = ""
    try:
        body_text = page.locator("body").inner_text(timeout=8000)
    except Exception:
        body_text = ""
    return {
        "url": page.url,
        "title": page.title() if hasattr(page, "title") else "",
        "body_excerpt": compact_text(body_text)[:1500],
        "marketing_fallback": marketing_fallback_detected(body_text),
    }
