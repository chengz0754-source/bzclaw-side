from playwright.sync_api import Playwright, sync_playwright


BENCHMARK_URL = "https://www.sellersprite.com/v3/competitor-lookup"
EXPORT_LOG_URL = "https://www.sellersprite.com/v2/export-log"


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(channel="msedge", headless=False)
    context = browser.new_context(storage_state="playwright\\auth\\sellersprite.storage_state.json")
    page = context.new_page()

    page.goto(BENCHMARK_URL)
    page.locator(".filter-item.input-wrap input[placeholder*='flashlight']").first.click()
    page.locator(".filter-item.input-wrap input[placeholder*='flashlight']").first.fill("Squeeze Toys")
    page.locator(".filter-item.input-wrap button").first.click()
    page.wait_for_timeout(5000)

    page.locator(".el-table__body .el-checkbox.table-check").first.click(force=True)
    page.wait_for_timeout(1200)
    page.locator("button.my-download").first.click()
    page.wait_for_timeout(2000)

    page1 = context.new_page()
    page1.goto(EXPORT_LOG_URL)

    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
