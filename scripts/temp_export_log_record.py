from pathlib import Path

from playwright.sync_api import Locator, Playwright, sync_playwright


EXPORT_LOG_URL = "https://www.sellersprite.com/v2/export-log"
STORAGE_STATE_PATH = Path("playwright/auth/sellersprite.storage_state.json")
TARGET_TOKENS = ("KeywordHistory", "squeeze-toys", "US")
DOWNLOAD_SELECTORS = (
    "a[title*='下载']",
    "button[title*='下载']",
    "a[href*='download']",
    "a[href*='export']",
    ".icon-download",
    ".el-icon-download",
)


def visible(locator: Locator) -> bool:
    try:
        return locator.is_visible(timeout=1500)
    except Exception:
        return False


def find_task_row(page) -> Locator:
    rows = page.locator("table tbody tr")
    for index in range(rows.count()):
        row = rows.nth(index)
        row_text = row.inner_text(timeout=1500).casefold()
        if all(token.casefold() in row_text for token in TARGET_TOKENS):
            return row
    raise RuntimeError("No export-log row matched the expected KeywordHistory task tokens.")


def find_download_control(row: Locator) -> Locator:
    for selector in DOWNLOAD_SELECTORS:
        locator = row.locator(selector)
        if locator.count() and visible(locator.first):
            return locator.first
    raise RuntimeError("Matched export-log row has no visible download control.")


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(channel="msedge", headless=False)
    context = browser.new_context(storage_state=str(STORAGE_STATE_PATH), accept_downloads=True)
    page = context.new_page()

    page.goto(EXPORT_LOG_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)

    matched_row = find_task_row(page)
    download_control = find_download_control(matched_row)

    with page.expect_download() as download_info:
        download_control.click()
    download = download_info.value
    print(download.suggested_filename)

    page.close()
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
