# SELLERSPRITE AUTH BOOTSTRAP REPORT

- UTC timestamp: `2026-04-04T14:05:51.391109+00:00`
- Browser selected for bootstrap: `chrome_channel`
- Browser channel: `chrome`
- Profile path: `E:\选品文件夹\amazon-selection-automation\playwright\profiles\sellersprite-main`
- Login URL: `https://www.sellersprite.com/w/user/login`
- Home page reachable: `True`
- Manual intervention used: `True`
- Storage state saved: `False`
- Storage state path: `E:\选品文件夹\amazon-selection-automation\playwright\auth\sellersprite.storage_state.json`
- Saved state reusable after bootstrap: `False`

## Browser probe

- `chrome_channel`: `PASS` | title=`卖家精灵官网 - 170万亚马逊卖家的选品及关键词工具` | final_url=`https://www.sellersprite.com/`
- `msedge_channel`: `PASS` | title=`卖家精灵官网 - 170万亚马逊卖家的选品及关键词工具` | final_url=`https://www.sellersprite.com/`
- `bundled_chromium`: `PASS` | title=`SellerSprite: Amazon Seller Tools for Profitable Growth` | final_url=`https://www.sellersprite.com/`

## Validation before save

- Validation target: `https://www.sellersprite.com/v2/market-research`
- Authenticated in active context: `False`
- Guest markers seen: `未登录, 游客`
- Secondary verification markers seen: `none`

## Reuse check

- Reuse check ran: `False`
- Reuse authenticated: `False`
- Reuse final URL: ``
- Reuse guest markers: `none`
- Reuse secondary verification markers: `none`

## Risks

- The saved storage state contains live account cookies and must stay out of git.
- SellerSprite exposes some guest pages, so page access alone does not prove login success.
- Future captcha or secondary verification prompts can invalidate an otherwise reusable session.
- Manual login did not become verifiably reusable before the bootstrap timeout expired.

## Notes

- SellerSprite guest pages can expose some tool pages without a logged-in
  session, so login success is judged using guest markers plus clean-context
  reuse validation instead of page reachability alone.
