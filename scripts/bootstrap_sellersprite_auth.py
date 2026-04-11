from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import Error, TimeoutError as PlaywrightTimeoutError, sync_playwright


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass


ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / "playwright" / "profiles" / "sellersprite-main"
STORAGE_STATE_PATH = ROOT / "playwright" / "auth" / "sellersprite.storage_state.json"
REPORT_PATH = ROOT / "reports" / "SELLERSPRITE_AUTH_BOOTSTRAP_REPORT.md"

HOME_URL = "https://www.sellersprite.com/"
LOGIN_URL = "https://www.sellersprite.com/w/user/login"
WELCOME_URL = "https://www.sellersprite.com/v2/welcome"
MARKET_URL = "https://www.sellersprite.com/v2/market-research"

GUEST_MARKERS = ("\u672a\u767b\u5f55", "\u6e38\u5ba2", "Log In", "Sign Up")
SECONDARY_MARKERS = (
    "\u9a8c\u8bc1\u7801",
    "\u626b\u7801\u767b\u5f55",
    "\u5b89\u5168\u9a8c\u8bc1",
    "\u4eba\u673a\u9a8c\u8bc1",
    "captcha",
    "2fa",
    "\u4e8c\u6b21\u9a8c\u8bc1",
    "\u4e8c\u6b65\u9a8c\u8bc1",
)
LOGIN_MARKERS = ("\u767b\u5f55", "Login", "\u90ae\u7bb1", "\u5bc6\u7801", "\u624b\u673a\u53f7")

BROWSER_CANDIDATES: list[tuple[str, dict[str, Any]]] = [
    ("msedge_channel", {"channel": "msedge"}),
    ("chrome_channel", {"channel": "chrome"}),
    ("bundled_chromium", {}),
]

WAIT_TIMEOUT_SECONDS = 900
POLL_SECONDS = 5


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compact(text: str) -> str:
    return " ".join(text.split())


def safe_text(page) -> str:
    try:
        return compact(page.locator("body").inner_text(timeout=8000))
    except Exception:
        return ""


def has_any(text: str, markers: tuple[str, ...]) -> bool:
    text_lower = text.lower()
    return any(marker.lower() in text_lower for marker in markers)


def page_snapshot(page) -> dict[str, Any]:
    body = safe_text(page)
    title = ""
    try:
        title = page.title()
    except Exception:
        title = ""
    return {
        "url": page.url,
        "title": title,
        "guest_markers": [m for m in GUEST_MARKERS if m in body],
        "secondary_markers": [m for m in SECONDARY_MARKERS if m.lower() in body.lower()],
        "login_markers": [m for m in LOGIN_MARKERS if m.lower() in body.lower()],
        "body_excerpt": body[:500],
    }


def write_report(summary: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    selected_browser = summary.get("selected_browser", {})
    selected_name = selected_browser.get("name", "unknown")
    selected_channel = selected_browser.get("channel", "bundled")
    probe_lines = [
        f"- `{probe['name']}`: `{probe['status']}`"
        + (f" | title=`{probe['title']}`" if probe.get("title") else "")
        + (f" | final_url=`{probe['final_url']}`" if probe.get("final_url") else "")
        + (f" | error=`{probe['error']}`" if probe.get("error") else "")
        for probe in summary.get("browser_probes", [])
    ]
    risk_lines = [f"- {item}" for item in summary.get("risk_points", [])]
    validation = summary.get("validation_before_save", {})
    reuse = summary.get("reuse_check", {})
    lines = [
        "# SELLERSPRITE AUTH BOOTSTRAP REPORT",
        "",
        f"- UTC timestamp: `{summary.get('timestamp')}`",
        f"- Browser selected for bootstrap: `{selected_name}`",
        f"- Browser channel: `{selected_channel}`",
        f"- Profile path: `{PROFILE_DIR}`",
        f"- Login URL: `{LOGIN_URL}`",
        f"- Home page reachable: `{summary.get('home_reachable')}`",
        f"- Manual intervention used: `{summary.get('manual_intervention')}`",
        f"- Storage state saved: `{summary.get('storage_state_saved')}`",
        f"- Storage state path: `{STORAGE_STATE_PATH}`",
        f"- Saved state reusable after bootstrap: `{reuse.get('authenticated')}`",
        "",
        "## Browser probe",
        "",
        *probe_lines,
        "",
        "## Validation before save",
        "",
        f"- Validation target: `{validation.get('target')}`",
        f"- Authenticated in active context: `{validation.get('authenticated')}`",
        f"- Guest markers seen: `{', '.join(validation.get('guest_markers', [])) or 'none'}`",
        f"- Secondary verification markers seen: `{', '.join(validation.get('secondary_markers', [])) or 'none'}`",
        "",
        "## Reuse check",
        "",
        f"- Reuse check ran: `{reuse.get('ran')}`",
        f"- Reuse authenticated: `{reuse.get('authenticated')}`",
        f"- Reuse final URL: `{reuse.get('final_url')}`",
        f"- Reuse guest markers: `{', '.join(reuse.get('guest_markers', [])) or 'none'}`",
        f"- Reuse secondary verification markers: `{', '.join(reuse.get('secondary_markers', [])) or 'none'}`",
        "",
        "## Risks",
        "",
        *risk_lines,
        "",
        "## Notes",
        "",
        "- SellerSprite guest pages can expose some tool pages without a logged-in",
        "  session, so login success is judged using guest markers plus clean-context",
        "  reuse validation instead of page reachability alone.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        raise RuntimeError("No Chromium-family browser candidate could open SellerSprite.")
    return results, selected


def navigate(page, url: str) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(1500)


def validate_authenticated_session(context) -> dict[str, Any]:
    page = context.pages[-1] if context.pages else context.new_page()
    result: dict[str, Any] = {
        "target": WELCOME_URL,
        "authenticated": False,
        "guest_markers": [],
        "secondary_markers": [],
        "final_url": "",
        "title": "",
        "body_excerpt": "",
        "error": None,
    }
    try:
        navigate(page, WELCOME_URL)
        snapshot = page_snapshot(page)
        result.update(snapshot)
        result["target"] = WELCOME_URL
        result["authenticated"] = not snapshot["guest_markers"] and not snapshot["secondary_markers"]
        if not result["authenticated"]:
            navigate(page, MARKET_URL)
            snapshot = page_snapshot(page)
            result.update(snapshot)
            result["target"] = MARKET_URL
            result["authenticated"] = not snapshot["guest_markers"] and not snapshot["secondary_markers"]
    except Exception as exc:
        result["error"] = str(exc)
    return result


def reuse_check(playwright, selected: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ran": False,
        "authenticated": False,
        "final_url": "",
        "guest_markers": [],
        "secondary_markers": [],
        "error": None,
    }
    if not STORAGE_STATE_PATH.exists():
        result["error"] = "storage state file not found"
        return result
    try:
        browser = playwright.chromium.launch(headless=True, **selected["kwargs"])
        context = browser.new_context(storage_state=str(STORAGE_STATE_PATH))
        result["ran"] = True
        validation = validate_authenticated_session(context)
        result["authenticated"] = bool(validation.get("authenticated"))
        result["final_url"] = validation.get("url", "") or validation.get("final_url", "")
        result["guest_markers"] = validation.get("guest_markers", [])
        result["secondary_markers"] = validation.get("secondary_markers", [])
        result["error"] = validation.get("error")
        context.close()
        browser.close()
    except Exception as exc:
        result["ran"] = True
        result["error"] = str(exc)
    return result


def main() -> int:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "timestamp": utc_now(),
        "home_reachable": False,
        "manual_intervention": True,
        "storage_state_saved": False,
        "browser_probes": [],
        "selected_browser": {},
        "validation_before_save": {},
        "reuse_check": {},
        "risk_points": [
            "The saved storage state contains live account cookies and must stay out of git.",
            "SellerSprite exposes some guest pages, so page access alone does not prove login success.",
            "Future captcha or secondary verification prompts can invalidate an otherwise reusable session.",
        ],
    }

    with sync_playwright() as playwright:
        browser_probes, selected = probe_browsers(playwright)
        summary["browser_probes"] = browser_probes
        summary["selected_browser"] = {
            "name": selected["name"],
            "channel": selected["channel"],
        }
        summary["home_reachable"] = any(item["status"] == "PASS" for item in browser_probes)

        context = None
        page = None
        try:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                headless=False,
                **selected["kwargs"],
            )
            page = context.pages[0] if context.pages else context.new_page()
            navigate(page, LOGIN_URL)

            print("SellerSprite login window is open.")
            print("Complete the login manually in the browser window.")
            print("The script will validate the session and save storage state automatically.")

            deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                current_page = context.pages[-1] if context.pages else page
                snapshot = page_snapshot(current_page)
                current_url = snapshot["url"].lower()
                title_lower = snapshot["title"].lower()
                login_like = "/w/user/login" in current_url or "login" in title_lower

                if not login_like:
                    validation = validate_authenticated_session(context)
                    summary["validation_before_save"] = validation
                    if validation.get("authenticated"):
                        context.storage_state(path=str(STORAGE_STATE_PATH))
                        summary["storage_state_saved"] = STORAGE_STATE_PATH.exists()
                        break

                current_page.wait_for_timeout(POLL_SECONDS * 1000)

            if not summary["storage_state_saved"]:
                validation = validate_authenticated_session(context)
                summary["validation_before_save"] = validation

            if summary["storage_state_saved"]:
                summary["reuse_check"] = reuse_check(playwright, selected)
            else:
                summary["reuse_check"] = {
                    "ran": False,
                    "authenticated": False,
                    "final_url": "",
                    "guest_markers": [],
                    "secondary_markers": [],
                    "error": "login validation did not pass before timeout",
                }
                summary["risk_points"].append(
                    "Manual login did not become verifiably reusable before the bootstrap timeout expired."
                )
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass

    write_report(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["storage_state_saved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
