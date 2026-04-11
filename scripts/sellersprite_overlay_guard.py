from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Iterable

from keyword_chain_common import ROOT, compact_text, ensure_within_repo, iso_now, page_guest_markers


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass


SCREENSHOT_ROOT = ROOT / "playwright" / "screenshots" / "sellersprite_keyword_export_flow"

KNOWN_CLOSE_SELECTORS = (
    ".banner-delet",
    ".keyword-store-close",
    ".global-bind-wechat-close",
    "#quick-guide-play-video-player-modal [data-dismiss='modal']",
    "#bbsViewModal [data-dismiss='modal']",
    "#surveyViewModal [data-dismiss='modal']",
    "#global-bind-wechat-modal [data-dismiss='modal']",
    ".modal.show .close",
    ".modal.show button.close",
    ".el-dialog__headerbtn",
    ".el-message-box__headerbtn",
)

KNOWN_HIDE_SELECTORS = (
    "#meiqia-container",
    "#dify-chatbot-bubble-button",
    ".restricted-free-promotion-modal",
    ".teach-banner",
    ".tips-help-video",
    ".newbie-beginner-guide",
    ".js-go-to",
    "#keyword-store",
    "#keyword-store-mask",
    "#sidebar-history",
    "#sidebar-account",
    "#quick-guide-play-video-player-modal",
    "#bbsViewModal",
    "#keywordTrendChartModal",
    "#TopNListModal",
    "#global-bind-wechat-modal",
    "#surveyViewModal",
    ".directional-bind-mask",
    "[data-directional-wechat-mask]",
    "[data-free-member-level]",
    "[data-vip-member-level]",
    ".modal-backdrop",
    ".ss-mask",
    ".popover",
)

GENERIC_OVERLAY_TOKENS = (
    "guide",
    "tutorial",
    "banner",
    "teach",
    "newbie",
    "vip",
    "upgrade",
    "coupon",
    "survey",
    "wechat",
    "bind",
    "kefu",
    "meiqia",
    "chat",
    "service",
    "assistant",
    "bubble",
    "float",
    "feedback",
    "popover",
    "overlay",
    "mask",
    "sidebar-history",
    "keyword-store",
    "客服",
    "帮助",
    "教程",
    "升级",
    "问卷",
    "绑定",
    "浮层",
    "弹窗",
    "遮罩",
)

DEFAULT_PRESERVE_TEXTS = (
    "前往查看",
    "去查看",
    "我的导出",
    "导出明细",
    "下载",
    "开始筛选",
)

GUARD_STYLE = """
[data-ss-overlay-guard-hidden="1"] {
  display: none !important;
  visibility: hidden !important;
  pointer-events: none !important;
}
#meiqia-container,
#dify-chatbot-bubble-button,
.restricted-free-promotion-modal,
.teach-banner,
.tips-help-video,
.newbie-beginner-guide,
.js-go-to,
#keyword-store-mask,
.directional-bind-mask,
[data-directional-wechat-mask],
[data-free-member-level],
[data-vip-member-level],
.modal-backdrop,
.ss-mask,
.popover {
  display: none !important;
  visibility: hidden !important;
  pointer-events: none !important;
}
"""


def visible(locator, timeout_ms: int = 1500) -> bool:
    try:
        return locator.first.is_visible(timeout=timeout_ms)
    except Exception:
        return False


def page_identity(page) -> dict[str, Any]:
    body_text = ""
    title = ""
    try:
        body_text = page.locator("body").inner_text(timeout=5000)
    except Exception:
        body_text = ""
    try:
        title = page.title()
    except Exception:
        title = ""
    compacted = compact_text(body_text)
    return {
        "timestamp": iso_now(),
        "url": page.url,
        "title": title,
        "guest_markers": page_guest_markers(compacted),
        "body_excerpt": compacted[:1200],
    }


def capture_screenshot(page, step_name: str, screenshot_dir: Path | None = None) -> str:
    target_dir = ensure_within_repo((screenshot_dir or SCREENSHOT_ROOT), "screenshot_dir")
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_step = re.sub(r"[^A-Za-z0-9._-]+", "-", step_name).strip("-") or "step"
    screenshot_path = ensure_within_repo(target_dir / f"{iso_now().replace(':', '').replace('+', '_')}-{safe_step}.png", "screenshot_path")
    page.screenshot(path=str(screenshot_path), full_page=True)
    return str(screenshot_path)


def install_guard_style(page) -> None:
    page.add_style_tag(content=GUARD_STYLE)


def _preserve_match(text: str, preserve_texts: Iterable[str]) -> bool:
    lowered = text.casefold()
    return any(token.casefold() in lowered for token in preserve_texts if str(token).strip())


def close_predictable_overlays(page, preserve_texts: Iterable[str] = ()) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    preserve = tuple(DEFAULT_PRESERVE_TEXTS) + tuple(str(token) for token in preserve_texts if str(token).strip())

    for selector in KNOWN_CLOSE_SELECTORS:
        locator = page.locator(selector)
        count = min(locator.count(), 5)
        for index in range(count):
            item = locator.nth(index)
            if not visible(item):
                continue
            try:
                element_text = compact_text(item.inner_text(timeout=1000))
            except Exception:
                element_text = ""
            if _preserve_match(element_text, preserve):
                continue
            try:
                item.click(timeout=2000, force=True)
                page.wait_for_timeout(250)
                actions.append({"selector": selector, "text": element_text or "(icon)"})
            except Exception:
                continue
    return actions


def hide_obvious_overlays(page, preserve_texts: Iterable[str] = ()) -> list[dict[str, Any]]:
    preserve = tuple(DEFAULT_PRESERVE_TEXTS) + tuple(str(token) for token in preserve_texts if str(token).strip())
    script = """
    ([selectors, preserveTexts, overlayTokens]) => {
      const hidden = [];
      const preserveList = (preserveTexts || []).map((item) => String(item || '').toLowerCase()).filter(Boolean);
      const tokenList = (overlayTokens || []).map((item) => String(item || '').toLowerCase()).filter(Boolean);
      const shouldPreserve = (text) => preserveList.some((token) => text.includes(token));
      const safeHide = (element, reason) => {
        if (!element || element.dataset.ssOverlayGuardHidden === '1') {
          return;
        }
        const computed = window.getComputedStyle(element);
        if (computed.display === 'none' || computed.visibility === 'hidden') {
          return;
        }
        const rect = element.getBoundingClientRect();
        const text = ((element.innerText || '') + ' ' + (element.id || '') + ' ' + (element.className || '')).replace(/\\s+/g, ' ').trim().toLowerCase();
        if (shouldPreserve(text)) {
          return;
        }
        if (rect.width < 8 || rect.height < 8) {
          return;
        }
        element.dataset.ssOverlayGuardHidden = '1';
        element.style.setProperty('display', 'none', 'important');
        element.style.setProperty('visibility', 'hidden', 'important');
        element.style.setProperty('pointer-events', 'none', 'important');
        hidden.push({
          reason,
          tag: element.tagName,
          id: element.id || '',
          className: String(element.className || '').slice(0, 120),
          text: text.slice(0, 180),
          rect: {
            top: Math.round(rect.top),
            left: Math.round(rect.left),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          },
        });
      };

      for (const selector of selectors || []) {
        for (const element of document.querySelectorAll(selector)) {
          safeHide(element, `known:${selector}`);
        }
      }

      for (const element of Array.from(document.body.querySelectorAll('*'))) {
        const computed = window.getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        const text = ((element.innerText || '') + ' ' + (element.id || '') + ' ' + (element.className || '')).replace(/\\s+/g, ' ').trim().toLowerCase();
        if (shouldPreserve(text)) {
          continue;
        }
        if (rect.width < 8 || rect.height < 8) {
          continue;
        }
        if (element.matches('table,thead,tbody,tr,td,th,form,input,textarea,button,select,main,.container,.card,.table-responsive,.el-table,.el-table__body-wrapper')) {
          continue;
        }
        const position = computed.position;
        const zIndex = computed.zIndex === 'auto' ? 0 : Number(computed.zIndex) || 0;
        const tokenMatched = tokenList.some((token) => text.includes(token));
        const fixedFloat = (position === 'fixed' || position === 'sticky') && rect.left > window.innerWidth * 0.62 && rect.top > window.innerHeight * 0.18;
        const fullScreenMask = (position === 'fixed' || position === 'absolute') && rect.width >= window.innerWidth * 0.9 && rect.height >= window.innerHeight * 0.9 && text.length < 32;
        const suspicious = tokenMatched || fixedFloat || fullScreenMask;
        if (!suspicious) {
          continue;
        }
        if (!(position === 'fixed' || position === 'sticky' || zIndex >= 999)) {
          continue;
        }
        safeHide(element, tokenMatched ? 'generic-token' : (fixedFloat ? 'generic-float' : 'generic-mask'));
      }
      return hidden;
    }
    """
    return page.evaluate(script, [list(KNOWN_HIDE_SELECTORS), list(preserve), list(GENERIC_OVERLAY_TOKENS)])


def guard_page(page, step_name: str, preserve_texts: Iterable[str] = ()) -> dict[str, Any]:
    try:
        page.wait_for_load_state("domcontentloaded", timeout=30000)
    except Exception:
        pass
    page.wait_for_timeout(400)
    before = page_identity(page)
    close_actions = close_predictable_overlays(page, preserve_texts=preserve_texts)
    install_guard_style(page)
    hidden = hide_obvious_overlays(page, preserve_texts=preserve_texts)
    page.wait_for_timeout(250)
    close_actions.extend(close_predictable_overlays(page, preserve_texts=preserve_texts))
    after = page_identity(page)
    return {
        "step_name": step_name,
        "before": before,
        "after": after,
        "close_actions": close_actions,
        "hidden_overlays": hidden,
        "closed_count": len(close_actions),
        "hidden_count": len(hidden),
    }


def find_first_visible(page_or_locator, selectors: Iterable[str], timeout_ms: int = 1500):
    for selector in selectors:
        locator = page_or_locator.locator(selector)
        if visible(locator, timeout_ms=timeout_ms):
            return locator.first
    return None


def locator_probe(page, locator) -> list[dict[str, Any]]:
    try:
        box = locator.first.bounding_box()
    except Exception:
        box = None
    if not box:
        return []
    center_x = box["x"] + max(1, min(box["width"] / 2, box["width"] - 1))
    center_y = box["y"] + max(1, min(box["height"] / 2, box["height"] - 1))
    script = """
    ([x, y]) => {
      const node = document.elementFromPoint(x, y);
      const chain = [];
      let current = node;
      while (current && chain.length < 6) {
        chain.push({
          tag: current.tagName,
          id: current.id || '',
          className: String(current.className || '').slice(0, 120),
          text: String(current.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 120),
        });
        current = current.parentElement;
      }
      return chain;
    }
    """
    return page.evaluate(script, [center_x, center_y])
