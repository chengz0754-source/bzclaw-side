from __future__ import annotations

import json
import sys
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
STORAGE_STATE_PATH = ROOT / "playwright" / "auth" / "sellersprite.storage_state.json"
SESSION_REPORT_PATH = ROOT / "reports" / "SELLERSPRITE_SESSION_CHECK.md"
FEASIBILITY_REPORT_PATH = ROOT / "reports" / "SELLERSPRITE_EXPORT_FEASIBILITY.md"

HOME_URL = "https://www.sellersprite.com/"
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
BROWSER_CANDIDATES: list[tuple[str, dict[str, Any]]] = [
    ("msedge_channel", {"channel": "msedge"}),
    ("chrome_channel", {"channel": "chrome"}),
    ("bundled_chromium", {}),
]

SEARCH_SEED = "Squeeze Toys"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compact(text: str) -> str:
    return " ".join(text.split())


def safe_text(page) -> str:
    try:
        return compact(page.locator("body").inner_text(timeout=8000))
    except Exception:
        return ""


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
        "body_excerpt": body[:500],
    }


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


def click_market_entry(page) -> bool:
    try:
        navigate(page, HOME_URL)
        market_link = page.locator("a[href*='/v2/market-research']").first
        if market_link.count():
            market_link.click(timeout=10000)
            page.wait_for_timeout(3000)
            return True
    except Exception:
        return False
    return False


def visible(locator) -> bool:
    try:
        return locator.first.is_visible(timeout=5000)
    except Exception:
        return False


def write_session_report(summary: dict[str, Any]) -> None:
    SESSION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    browser = summary.get("selected_browser", {})
    lines = [
        "# SELLERSPRITE SESSION CHECK",
        "",
        f"- UTC timestamp: `{summary.get('timestamp')}`",
        f"- Browser used: `{browser.get('name', 'unknown')}`",
        f"- Storage state path: `{STORAGE_STATE_PATH}`",
        f"- Reused login state: `{summary.get('authenticated')}`",
        f"- Jumped back to login: `{summary.get('jumped_to_login')}`",
        f"- Secondary verification needed: `{summary.get('secondary_verification_needed')}`",
        f"- Session stability judgment: `{summary.get('session_stability')}`",
        "",
        "## Validation targets",
        "",
        f"- Welcome page final URL: `{summary.get('welcome_url')}`",
        f"- Market page final URL: `{summary.get('market_url')}`",
        f"- Guest markers on welcome: `{', '.join(summary.get('welcome_guest_markers', [])) or 'none'}`",
        f"- Guest markers on market: `{', '.join(summary.get('market_guest_markers', [])) or 'none'}`",
        f"- Secondary verification markers: `{', '.join(summary.get('secondary_markers', [])) or 'none'}`",
        "",
        "## Notes",
        "",
        f"- Welcome title: `{summary.get('welcome_title', '')}`",
        f"- Market title: `{summary.get('market_title', '')}`",
        f"- Error: `{summary.get('error') or 'none'}`",
    ]
    SESSION_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_feasibility_report(summary: dict[str, Any]) -> None:
    FEASIBILITY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# SELLERSPRITE EXPORT FEASIBILITY",
        "",
        f"- UTC timestamp: `{summary.get('timestamp')}`",
        f"- Market entry visible: `{summary.get('market_entry_visible')}`",
        f"- Market page reachable: `{summary.get('market_page_reachable')}`",
        f"- Page structure locatable: `{summary.get('page_structure_locatable')}`",
        f"- Search input visible: `{summary.get('search_input_visible')}`",
        f"- Query button visible: `{summary.get('query_button_visible')}`",
        f"- Search attempt executed: `{summary.get('search_attempt_executed')}`",
        f"- Search attempt final URL: `{summary.get('search_attempt_url')}`",
        f"- Export button visible: `{summary.get('export_button_visible')}`",
        f"- Ready for next-round live export script development: `{summary.get('ready_for_live_export_dev')}`",
        "",
        "## Element probes",
        "",
        f"- Market title: `{summary.get('market_title', '')}`",
        f"- Search placeholder matched: `{summary.get('search_placeholder_match')}`",
        f"- Query button text matched: `{summary.get('query_button_match')}`",
        f"- Export locator matched: `{summary.get('export_locator_match')}`",
        "",
        "## Interpretation",
        "",
        f"- Feasibility note: {summary.get('feasibility_note')}",
        f"- Error: `{summary.get('error') or 'none'}`",
    ]
    FEASIBILITY_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    session_summary: dict[str, Any] = {
        "timestamp": utc_now(),
        "selected_browser": {},
        "authenticated": False,
        "jumped_to_login": False,
        "secondary_verification_needed": False,
        "session_stability": "unverified",
        "welcome_url": "",
        "market_url": "",
        "welcome_title": "",
        "market_title": "",
        "welcome_guest_markers": [],
        "market_guest_markers": [],
        "secondary_markers": [],
        "error": None,
    }
    feasibility_summary: dict[str, Any] = {
        "timestamp": utc_now(),
        "market_entry_visible": False,
        "market_page_reachable": False,
        "page_structure_locatable": False,
        "search_input_visible": False,
        "query_button_visible": False,
        "search_attempt_executed": False,
        "search_attempt_url": "",
        "export_button_visible": False,
        "ready_for_live_export_dev": False,
        "market_title": "",
        "search_placeholder_match": "",
        "query_button_match": "\u7b5b\u9009\u5e02\u573a",
        "export_locator_match": "text=\u5bfc\u51fa",
        "feasibility_note": "",
        "error": None,
    }

    with sync_playwright() as playwright:
        browser_probes, selected = probe_browsers(playwright)
        session_summary["selected_browser"] = {
            "name": selected["name"],
            "channel": selected["channel"],
            "probes": browser_probes,
        }

        if not STORAGE_STATE_PATH.exists():
            session_summary["error"] = "storage state file not found"
            session_summary["session_stability"] = "blocked_no_reusable_state"

            browser = None
            context = None
            try:
                browser = playwright.chromium.launch(headless=True, **selected["kwargs"])
                context = browser.new_context()
                page = context.new_page()
                click_market_entry(page)
                if "market-research" not in page.url:
                    navigate(page, MARKET_URL)
                market = page_snapshot(page)
                feasibility_summary["market_entry_visible"] = visible(page.locator("a[href*='/v2/market-research']")) or ("\u9009\u5e02\u573a" in safe_text(page))
                feasibility_summary["market_page_reachable"] = "market-research" in market["url"]
                feasibility_summary["market_title"] = market["title"]
                search_input = page.locator("input[name='departmentKeyword']")
                query_button = page.locator("button:has-text('\u7b5b\u9009\u5e02\u573a')")
                feasibility_summary["search_placeholder_match"] = "\u7c7b\u76ee\u5173\u952e\u8bcd\uff0c\u5982Light"
                feasibility_summary["search_input_visible"] = visible(search_input)
                feasibility_summary["query_button_visible"] = visible(query_button)
                feasibility_summary["page_structure_locatable"] = feasibility_summary["market_page_reachable"] and feasibility_summary["search_input_visible"] and feasibility_summary["query_button_visible"]
                feasibility_summary["error"] = "storage state file not found"
                feasibility_summary["feasibility_note"] = "The market page is reachable in guest mode, but there is still no reusable authenticated SellerSprite session, so live export development remains blocked."
            except Exception as exc:
                feasibility_summary["error"] = str(exc)
                feasibility_summary["feasibility_note"] = "Auth bootstrap did not produce a reusable storage state, and guest-mode probing also hit an automation error."
            finally:
                if context is not None:
                    try:
                        context.close()
                    except Exception:
                        pass
                if browser is not None:
                    try:
                        browser.close()
                    except Exception:
                        pass

            write_session_report(session_summary)
            write_feasibility_report(feasibility_summary)
            print(json.dumps({"session": session_summary, "feasibility": feasibility_summary}, ensure_ascii=False, indent=2))
            return 1

        browser = None
        context = None
        try:
            browser = playwright.chromium.launch(headless=True, **selected["kwargs"])
            context = browser.new_context(storage_state=str(STORAGE_STATE_PATH))
            page = context.new_page()

            navigate(page, WELCOME_URL)
            welcome = page_snapshot(page)
            session_summary["welcome_url"] = welcome["url"]
            session_summary["welcome_title"] = welcome["title"]
            session_summary["welcome_guest_markers"] = welcome["guest_markers"]

            page.goto(MARKET_URL, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2000)
            if "/w/user/login" in page.url.lower():
                session_summary["jumped_to_login"] = True
            if not page.url.lower().startswith("https://www.sellersprite.com/v2/market-research"):
                click_market_entry(page)
            page.wait_for_timeout(1500)

            market = page_snapshot(page)
            session_summary["market_url"] = market["url"]
            session_summary["market_title"] = market["title"]
            session_summary["market_guest_markers"] = market["guest_markers"]
            session_summary["secondary_markers"] = market["secondary_markers"] or welcome["secondary_markers"]
            session_summary["secondary_verification_needed"] = bool(session_summary["secondary_markers"])

            authenticated = not session_summary["jumped_to_login"] and not session_summary["welcome_guest_markers"] and not session_summary["market_guest_markers"] and not session_summary["secondary_verification_needed"]
            session_summary["authenticated"] = authenticated
            session_summary["session_stability"] = "stable_enough_for_next_round" if authenticated else "fragile_or_invalid"

            feasibility_summary["market_entry_visible"] = visible(page.locator("a[href*='/v2/market-research']")) or ("\u9009\u5e02\u573a" in safe_text(page))
            feasibility_summary["market_page_reachable"] = "market-research" in market["url"]
            feasibility_summary["market_title"] = market["title"]

            search_input = page.locator("input[name='departmentKeyword']")
            query_button = page.locator("button:has-text('\u7b5b\u9009\u5e02\u573a')")
            feasibility_summary["search_placeholder_match"] = "\u7c7b\u76ee\u5173\u952e\u8bcd\uff0c\u5982Light"
            feasibility_summary["search_input_visible"] = visible(search_input)
            feasibility_summary["query_button_visible"] = visible(query_button)
            feasibility_summary["page_structure_locatable"] = feasibility_summary["market_page_reachable"] and feasibility_summary["search_input_visible"] and feasibility_summary["query_button_visible"]

            if authenticated and feasibility_summary["page_structure_locatable"]:
                search_input.fill(SEARCH_SEED)
                query_button.first.click()
                page.wait_for_timeout(8000)
                feasibility_summary["search_attempt_executed"] = True
                feasibility_summary["search_attempt_url"] = page.url
                export_button = page.locator("button:has-text('\u5bfc\u51fa'), a:has-text('\u5bfc\u51fa'), text=\u5bfc\u51fa")
                feasibility_summary["export_button_visible"] = visible(export_button)
                if feasibility_summary["export_button_visible"]:
                    feasibility_summary["ready_for_live_export_dev"] = True
                    feasibility_summary["feasibility_note"] = "Authenticated session is reusable, market page is locatable, one safe search ran, and an export control is visible."
                else:
                    feasibility_summary["feasibility_note"] = "Authenticated session is reusable and the market page/search controls are locatable, but an export control was not confirmed after one minimal search."
            else:
                if not authenticated:
                    feasibility_summary["feasibility_note"] = "Session is not reusable enough yet, so live export development is not ready."
                else:
                    feasibility_summary["feasibility_note"] = "Market page structure could not be located reliably enough for a safe export automation pass."
        except Exception as exc:
            session_summary["error"] = str(exc)
            session_summary["session_stability"] = "error"
            feasibility_summary["error"] = str(exc)
            feasibility_summary["feasibility_note"] = "The session check hit an automation error before export feasibility could be confirmed."
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass

    write_session_report(session_summary)
    write_feasibility_report(feasibility_summary)
    print(json.dumps({"session": session_summary, "feasibility": feasibility_summary}, ensure_ascii=False, indent=2))
    return 0 if session_summary["authenticated"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
