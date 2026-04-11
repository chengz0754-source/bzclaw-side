from pathlib import Path

from playwright.sync_api import Playwright, sync_playwright


RESULT_URL = "https://www.sellersprite.com/v3/keyword-miner/?q=Squeeze%20Toys&marketId=1&batch=0"
STORAGE_STATE_PATH = Path("playwright/auth/sellersprite.storage_state.json")


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(channel="msedge", headless=False)
    context = browser.new_context(storage_state=str(STORAGE_STATE_PATH), accept_downloads=False)
    page = context.new_page()

    page.goto(RESULT_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)

    checkboxes = page.locator("input[type='checkbox']")
    target_checkbox = checkboxes.nth(1) if checkboxes.count() > 1 else checkboxes.first
    target_checkbox.check(force=True)
    page.wait_for_timeout(800)

    page.locator("button").filter(has_text="导出明细").first.click()
    page.wait_for_timeout(1200)

    with page.expect_popup() as export_log_popup:
        page.locator("button").filter(has_text="前往查看").first.click()
    export_log_page = export_log_popup.value
    export_log_page.wait_for_load_state("domcontentloaded")

    export_log_page.close()
    page.close()
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
