import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(channel="msedge", headless=False)
    context = browser.new_context(storage_state="playwright\\auth\\sellersprite.storage_state.json")
    page = context.new_page()
    page.goto("https://www.sellersprite.com/v3/keyword-miner/?q=Squeeze%20Toys&marketId=1&batch=0")
    page.get_by_role("link", name="工具").click()
    page.locator("#KM").get_by_role("link", name="关键词挖掘").click()
    page.get_by_role("textbox", name="输入关键词，如: flashlight").click()
    page.get_by_role("textbox", name="输入关键词，如: flashlight").click()
    page.get_by_role("textbox", name="输入关键词，如: flashlight").fill("Squeeze Toys")
    page.get_by_role("button", name="立即查询").click()
    page.locator(".left > .el-checkbox").click()
    page.get_by_role("button", name="导出明细").click()
    with page.expect_popup() as page1_info:
        page.get_by_role("button", name="前往查看").click()
    page1 = page1_info.value
    page1.close()
    page.close()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
