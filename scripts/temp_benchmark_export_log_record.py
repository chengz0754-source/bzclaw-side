import re

from playwright.sync_api import Playwright, sync_playwright


EXPORT_LOG_URL = "https://www.sellersprite.com/v2/export-log"
TASK_PATTERN = re.compile(r"Competitor-US-Last-30-days-\d+", re.IGNORECASE)


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(channel="msedge", headless=False)
    context = browser.new_context(storage_state="playwright\\auth\\sellersprite.storage_state.json", accept_downloads=True)
    page = context.new_page()

    page.goto(EXPORT_LOG_URL)
    page.wait_for_timeout(3000)

    target_row = page.locator("tbody tr").filter(has_text=TASK_PATTERN).first
    with page.expect_download() as download_info:
        target_row.locator("a.download-excel, button.download-excel, .download-excel").first.click()
    download = download_info.value
    _ = download

    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
