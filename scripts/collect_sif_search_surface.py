from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from sif_surface_common import (
    LOG_DIR,
    OUTPUTS_ROOT,
    PROFILE_DIR,
    ROOT,
    SEARCH_ROUTE_MAP,
    STORAGE_STATE_PATH,
    SurfaceContext,
    auth_probe,
    compact_text,
    default_output_dir,
    ensure_within_repo,
    iso_now,
    load_field_order,
    page_snapshot,
    probe_browsers,
    profile_has_content,
    resolve_surface_context,
    route_url,
    write_csv_atomic,
    write_json_atomic,
)


OUTPUT_51 = "51_SIF关键词价值补强.csv"
OUTPUT_52 = "52_SIF广告结构补强.csv"
RAW_JSON_FILE = "sif_search_surface_probe.json"
LATEST_LOG_FILE = LOG_DIR / "latest_search_run.json"
RUN_HISTORY_FILE = LOG_DIR / "search_runs.jsonl"
RUN_FAILURE_FILE = LOG_DIR / "search_failures.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe the minimal SIF search-page keyword/pit surface and map the result into 51/52 standard CSVs."
    )
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--direction-id", default=None)
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--sample-id", default=None)
    parser.add_argument("--asin", default=None)
    parser.add_argument("--country", default="US")
    parser.add_argument("--candidate-pool-csv", default=None)
    parser.add_argument("--candidate-index", type=int, default=1)
    parser.add_argument("--route", choices=sorted(SEARCH_ROUTE_MAP), default="snapshot")
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def append_jsonl(path: Path, payload: dict) -> None:
    ensure_within_repo(path, "jsonl_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def build_51_row(context: SurfaceContext, status: str) -> dict[str, str]:
    return {
        "运行名称": context.run_name,
        "方向ID": context.direction_id,
        "关键词": context.keyword,
        "样品ID": context.sample_id,
        "样品ASIN": context.sample_asin,
        "核心关键词": "",
        "长尾关键词": "",
        "关键词数量": "",
        "高价值关键词数": "",
        "建议竞价中位数": "",
        "高竞价关键词数": "",
        "关键词价值状态": status,
        "抓取时间": iso_now(),
        "来源模块": "SIF_选词/查竞价",
    }


def build_52_row(context: SurfaceContext, status: str) -> dict[str, str]:
    return {
        "运行名称": context.run_name,
        "方向ID": context.direction_id,
        "关键词": context.keyword,
        "样品ID": context.sample_id,
        "样品ASIN": context.sample_asin,
        "广告词数量": "",
        "广告活动结构摘要": "",
        "广告依赖状态": status,
        "自然位趋势摘要": "",
        "广告位趋势摘要": "",
        "坑位稳定性状态": status,
        "抓取时间": iso_now(),
        "来源模块": "SIF_广告透视仪/查坑位",
    }


def main() -> int:
    args = parse_args()
    context = resolve_surface_context(
        run_name=args.run_name,
        direction_id=args.direction_id,
        keyword=args.keyword,
        sample_id=args.sample_id,
        sample_asin=args.asin,
        country=args.country,
        candidate_pool_csv=args.candidate_pool_csv,
        candidate_index=args.candidate_index,
    )

    output_dir = Path(args.output_dir).expanduser() if args.output_dir else default_output_dir("SIF_SEARCH_" + iso_now().replace(":", "").replace("+", "_"))
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir = ensure_within_repo(output_dir, "output_dir")
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_json_path = ensure_within_repo(output_dir / RAW_JSON_FILE, "raw_json_path")
    csv_51_path = ensure_within_repo(output_dir / OUTPUT_51, "csv_51_path")
    csv_52_path = ensure_within_repo(output_dir / OUTPUT_52, "csv_52_path")

    summary: dict[str, object] = {
        "timestamp": iso_now(),
        "module": "sif_search_surface",
        "status": "HOLD",
        "reason_code": "NOT_RUN",
        "context": {
            "run_name": context.run_name,
            "direction_id": context.direction_id,
            "keyword": context.keyword,
            "sample_id": context.sample_id,
            "sample_asin": context.sample_asin,
            "country": context.country,
            "candidate_source": context.candidate_source,
            "candidate_pool_path": context.candidate_pool_path,
        },
        "route": args.route,
        "route_url": route_url(SEARCH_ROUTE_MAP[args.route], context.country),
        "auth_probe": {},
        "navigation": {},
        "network_calls": [],
        "output_51_path": str(csv_51_path),
        "output_52_path": str(csv_52_path),
        "output_json_path": str(raw_json_path),
    }

    with sync_playwright() as playwright:
        browser_probes, selected = probe_browsers(playwright)
        summary["browser_probes"] = browser_probes
        summary["selected_browser"] = {"name": selected["name"], "channel": selected["channel"]}

        browser = None
        persistent_launch_error = ""
        if profile_has_content(PROFILE_DIR):
            try:
                context_browser = playwright.chromium.launch_persistent_context(
                    str(PROFILE_DIR),
                    headless=True,
                    viewport={"width": 1600, "height": 1400},
                    **selected["kwargs"],
                )
                summary["execution_mode"] = "persistent_profile"
            except Exception as exc:
                persistent_launch_error = str(exc)
                browser = playwright.chromium.launch(headless=True, **selected["kwargs"])
                if STORAGE_STATE_PATH.exists():
                    context_browser = browser.new_context(
                        storage_state=str(STORAGE_STATE_PATH),
                        viewport={"width": 1600, "height": 1400},
                    )
                    summary["execution_mode"] = "storage_state_fallback"
                else:
                    context_browser = browser.new_context(viewport={"width": 1600, "height": 1400})
                    summary["execution_mode"] = "guest_context_fallback"
        else:
            browser = playwright.chromium.launch(headless=True, **selected["kwargs"])
            if STORAGE_STATE_PATH.exists():
                context_browser = browser.new_context(
                    storage_state=str(STORAGE_STATE_PATH),
                    viewport={"width": 1600, "height": 1400},
                )
                summary["execution_mode"] = "storage_state"
            else:
                context_browser = browser.new_context(viewport={"width": 1600, "height": 1400})
                summary["execution_mode"] = "guest_context"
        if persistent_launch_error:
            summary["persistent_launch_warning"] = persistent_launch_error

        try:
            summary["auth_probe"] = auth_probe(context_browser.request)
            page = context_browser.pages[-1] if context_browser.pages else context_browser.new_page()
            network_calls: list[dict[str, object]] = []
            page.on(
                "response",
                lambda resp: network_calls.append(
                    {
                        "url": resp.url,
                        "status": resp.status,
                        "resource_type": resp.request.resource_type,
                    }
                ),
            )
            page.goto(str(summary["route_url"]), wait_until="networkidle", timeout=60000)
            snapshot = page_snapshot(page)
            snapshot["body_excerpt"] = compact_text(str(snapshot.get("body_excerpt", "")))
            summary["navigation"] = snapshot
            summary["network_calls"] = [
                call
                for call in network_calls
                if any(token in str(call["url"]).lower() for token in ["api", "search", "rank", "snapshot", "hourly", "daily", "keyword"])
            ][:80]

            if not summary["auth_probe"].get("authenticated"):
                summary["status"] = "HOLD"
                summary["reason_code"] = "SIF_AUTH_REQUIRED"
            elif snapshot.get("marketing_fallback"):
                summary["status"] = "HOLD"
                summary["reason_code"] = "SEARCH_ROUTE_FALLBACK_TO_MARKETING_PAGE"
            else:
                summary["status"] = "PASS"
                summary["reason_code"] = "SEARCH_SURFACE_VISIBLE"
        finally:
            context_browser.close()
            if browser is not None:
                browser.close()

    status_value = "PASS" if summary["status"] == "PASS" else "HOLD"
    field_order_51 = load_field_order(OUTPUT_51)
    field_order_52 = load_field_order(OUTPUT_52)
    row_51 = build_51_row(context, status_value)
    row_52 = build_52_row(context, status_value)
    write_csv_atomic(csv_51_path, field_order_51, [[row_51.get(field, "") for field in field_order_51]])
    write_csv_atomic(csv_52_path, field_order_52, [[row_52.get(field, "") for field in field_order_52]])
    write_json_atomic(raw_json_path, summary)
    write_json_atomic(LATEST_LOG_FILE, summary)
    append_jsonl(RUN_HISTORY_FILE, summary)
    if summary["status"] != "PASS":
        append_jsonl(RUN_FAILURE_FILE, summary)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
