from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    paths = json.loads((root / "configs" / "paths.json").read_text(encoding="utf-8"))
    profile_dir = Path(paths["playwright"]["profile_dir"])
    screenshot_path = Path(paths["playwright"]["screenshots_dir"]) / "playwright-smoke.png"
    trace_path = Path(paths["playwright"]["traces_dir"]) / "playwright-smoke.zip"
    smoke_state_path = Path(paths["playwright"]["smoke_storage_state_path"])
    report_path = root / "reports" / "PLAYWRIGHT_SMOKE_REPORT.md"

    profile_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    smoke_state_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    page_title = "Machine B Playwright Smoke"
    data_url = (
        "data:text/html,"
        "<html><head><title>Machine B Playwright Smoke</title></head>"
        "<body><h1>Playwright smoke baseline</h1></body></html>"
    )

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True,
        )
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        page.goto(data_url, wait_until="load")
        page.screenshot(path=str(screenshot_path), full_page=True)
        context.storage_state(path=str(smoke_state_path))
        context.tracing.stop(path=str(trace_path))
        observed_title = page.title()
        context.close()

    lines = [
        "# Playwright Smoke Report",
        "",
        f"- UTC timestamp: `{datetime.now(timezone.utc).isoformat()}`",
        "- Runtime: `Python Playwright`",
        f"- Persistent profile dir: `{profile_dir}`",
        f"- Smoke storage state: `{smoke_state_path}`",
        f"- Screenshot: `{screenshot_path}`",
        f"- Trace: `{trace_path}`",
        f"- Observed title: `{observed_title}`",
        "- Result: `PASS`",
        "",
        "This smoke run proves the Playwright runtime, browser launch, dedicated",
        "automation profile directory, screenshot output, trace output, and an",
        "unauthenticated storage state path are working.",
        "",
        "No site login was performed in this smoke run.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
