from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from sif_surface_common import (
    HOME_URL,
    LOGIN_QR_URL,
    LOG_DIR,
    PROFILE_DIR,
    ROOT,
    STORAGE_STATE_PATH,
    SIFSurfaceError,
    append_jsonl,
    auth_probe,
    ensure_within_repo,
    iso_now,
    probe_browsers,
    profile_has_content,
    write_json_atomic,
)


LATEST_RUN_PATH = LOG_DIR / "latest_bootstrap_run.json"
RUN_HISTORY_PATH = LOG_DIR / "bootstrap_runs.jsonl"
RUN_FAILURE_PATH = LOG_DIR / "bootstrap_failures.jsonl"
DEFAULT_EXTENSION_PATH = Path("playwright/extensions/sif")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap an isolated SIF Playwright profile and optionally wait for manual login."
    )
    parser.add_argument("--wait-seconds", type=int, default=300, help="How long to wait for a reusable authenticated session.")
    parser.add_argument("--poll-seconds", type=float, default=5.0, help="Polling interval for auth probe.")
    parser.add_argument("--init-only", action="store_true", help="Only initialize the isolated profile path and browser probe.")
    parser.add_argument(
        "--probe-login-surface",
        action="store_true",
        help="Open the login surface, verify QR/login prompt reachability, but do not wait for manual auth.",
    )
    parser.add_argument("--headless", action="store_true", help="Run bootstrap in headless mode.")
    parser.add_argument(
        "--extension-path",
        default=str(DEFAULT_EXTENSION_PATH),
        help="Optional unpacked SIF extension directory. When absent, bootstrap stays in web-app-only mode.",
    )
    return parser.parse_args()


def extension_launch_args(extension_path: Path | None) -> tuple[list[str], dict[str, Any]]:
    if extension_path is None or not extension_path.exists():
        return [], {"extension_mode": "NOT_CONFIGURED", "extension_loaded": False}
    resolved = ensure_within_repo(extension_path, "extension_path")
    args = [
        f"--disable-extensions-except={resolved}",
        f"--load-extension={resolved}",
    ]
    return args, {"extension_mode": "UNPACKED_EXTENSION", "extension_loaded": True, "extension_path": str(resolved)}


def persist_summary(summary: dict[str, Any]) -> None:
    write_json_atomic(LATEST_RUN_PATH, summary)
    append_jsonl(RUN_HISTORY_PATH, summary)
    if summary["status"] != "PASS":
        append_jsonl(RUN_FAILURE_PATH, summary)


def main() -> int:
    args = parse_args()
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    extension_path = Path(args.extension_path).expanduser()
    if not extension_path.is_absolute():
        extension_path = ROOT / extension_path
    extension_args, extension_meta = extension_launch_args(extension_path if str(args.extension_path).strip() else None)

    summary: dict[str, Any] = {
        "timestamp": iso_now(),
        "module": "sif_auth_bootstrap",
        "status": "HOLD",
        "reason_code": "BOOTSTRAP_NOT_RUN",
        "profile_dir": str(PROFILE_DIR),
        "profile_has_content_before": profile_has_content(PROFILE_DIR),
        "storage_state_path": str(STORAGE_STATE_PATH),
        "storage_state_exists_before": STORAGE_STATE_PATH.exists(),
        "init_only": bool(args.init_only),
        "probe_login_surface": bool(args.probe_login_surface),
        "headless": bool(args.headless),
        "wait_seconds": int(args.wait_seconds),
        "poll_seconds": float(args.poll_seconds),
        "browser_probes": [],
        "selected_browser": {},
        "login_surface_probe": {
            "attempted": False,
            "login_clicked": False,
            "qr_request_seen": False,
            "final_url": "",
            "error": "",
        },
        "auth_probe": {},
        "extension": extension_meta,
    }

    with sync_playwright() as playwright:
        browser_probes, selected = probe_browsers(playwright)
        summary["browser_probes"] = browser_probes
        summary["selected_browser"] = {
            "name": selected["name"],
            "channel": selected["channel"],
        }

        if args.init_only:
            summary["status"] = "PASS"
            summary["reason_code"] = "PROFILE_INITIALIZED"
            persist_summary(summary)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0

        context = playwright.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=bool(args.headless),
            viewport={"width": 1600, "height": 1400},
            args=extension_args,
            **selected["kwargs"],
        )

        try:
            page = context.pages[-1] if context.pages else context.new_page()
            responses: list[str] = []
            page.on("response", lambda resp: responses.append(resp.url))

            page.goto(HOME_URL, wait_until="networkidle", timeout=60000)
            summary["login_surface_probe"]["attempted"] = True

            try:
                page.locator("text=登录").first.click(timeout=10000)
                summary["login_surface_probe"]["login_clicked"] = True
                page.wait_for_timeout(2500)
            except Exception as exc:
                summary["login_surface_probe"]["error"] = str(exc)

            summary["login_surface_probe"]["qr_request_seen"] = any(LOGIN_QR_URL in url for url in responses)
            summary["login_surface_probe"]["final_url"] = page.url
            summary["auth_probe"] = auth_probe(context.request)

            if args.probe_login_surface:
                summary["status"] = "HOLD"
                summary["reason_code"] = "LOGIN_SURFACE_PROBED__AUTH_REQUIRED"
                if summary["auth_probe"].get("authenticated"):
                    context.storage_state(path=str(STORAGE_STATE_PATH))
                    summary["status"] = "PASS"
                    summary["reason_code"] = "LOGIN_SURFACE_PROBED__AUTH_REUSABLE"
                persist_summary(summary)
                print(json.dumps(summary, ensure_ascii=False, indent=2))
                return 0 if summary["status"] == "PASS" else 2

            deadline = time.time() + max(int(args.wait_seconds), 0)
            while time.time() < deadline:
                current_probe = auth_probe(context.request)
                summary["auth_probe"] = current_probe
                if current_probe.get("authenticated"):
                    context.storage_state(path=str(STORAGE_STATE_PATH))
                    summary["status"] = "PASS"
                    summary["reason_code"] = "AUTH_BOOTSTRAP_COMPLETED"
                    break
                page.wait_for_timeout(int(max(args.poll_seconds, 1.0) * 1000))

            if summary["status"] != "PASS":
                summary["status"] = "HOLD"
                if not summary["login_surface_probe"]["qr_request_seen"]:
                    summary["reason_code"] = "LOGIN_SURFACE_NOT_REACHABLE"
                else:
                    summary["reason_code"] = "AUTH_REQUIRED__MANUAL_LOGIN_NOT_COMPLETED"
        finally:
            context.close()

    persist_summary(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
