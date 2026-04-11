# SIF Playwright Surface Contract

## Scope

- This contract covers only the SIF Playwright bootstrap layer and the minimum reusable surfaces needed before Step 5 integration.
- This round does not make business judgments and does not finalize `53_SIF补强下推结果.csv`.
- This round only standardizes:
  - isolated SIF Playwright profile / auth bootstrap
  - detail-page traffic probe
  - search-page keyword / pit probe
  - structured fail-closed outputs that already match canonical CSV headers

## Repo Paths

- Profile directory: `playwright/profiles/sif-main/`
- Storage state path: `playwright/auth/sif.storage_state.json`
- Runtime logs: `logs/sif_surfaces/`
- Bootstrap script: `scripts/bootstrap_sif_auth.py`
- Detail probe: `scripts/collect_sif_detail_surface.py`
- Search probe: `scripts/collect_sif_search_surface.py`
- Shared helper: `scripts/sif_surface_common.py`

## Current Repo Truth

- On `2026-04-07`, guest requests to `https://www.sif.com/api/user/basic/info` return `{"code": -10, "message": "UNAUTHORIZED"}`.
- The web-app routes exist in the current SIF frontend bundle, including:
  - detail-family routes: `/reverse`, `/timemachine-traffic`
  - search-family routes: `/search`, `/snapshot`, `/dailyrank`, `/hourlyrank`
- Without a reusable authenticated session, those routes currently fall back to the public marketing shell instead of exposing the business surface.
- No repo-local unpacked SIF extension artifact was found at validation time.
- No verified installed SIF browser extension was found inside the repo-local automation profile.

## Bootstrap Contract

- `python scripts/bootstrap_sif_auth.py --init-only`
  - creates / validates the isolated repo-local profile path
  - probes Chromium-family browser availability
  - does not claim auth success
- `python scripts/bootstrap_sif_auth.py --probe-login-surface`
  - opens `https://www.sif.com/`
  - triggers the login surface
  - verifies whether the QR/login request path appears
  - records current auth truth through `/api/user/basic/info`
- `python scripts/bootstrap_sif_auth.py`
  - opens the isolated persistent profile
  - waits for manual operator login
  - only saves `playwright/auth/sif.storage_state.json` after `/api/user/basic/info` stops returning `UNAUTHORIZED`

## Extension Handling

- `scripts/bootstrap_sif_auth.py` accepts `--extension-path`.
- Default path is `playwright/extensions/sif`.
- If no unpacked extension artifact exists, bootstrap stays in `NOT_CONFIGURED` extension mode and must not claim extension load success.
- This is intentional fail-closed behavior.

## Minimal Surface Contract

### Detail Surface

- Probe script: `scripts/collect_sif_detail_surface.py`
- Current canonical output:
  - `50_SIF流量结构补强.csv`
  - `sif_detail_surface_probe.json`
- Default route family:
  - `/reverse?asin=<ASIN>&country=<SITE>`
- Current output promise:
  - when auth is reusable and the route no longer falls back to marketing shell, emit a real `50` row
  - otherwise emit a standards-aligned blocked row with `核心流量结构状态=HOLD`

### Search Surface

- Probe script: `scripts/collect_sif_search_surface.py`
- Current canonical outputs:
  - `51_SIF关键词价值补强.csv`
  - `52_SIF广告结构补强.csv`
  - `sif_search_surface_probe.json`
- Default route family:
  - `/snapshot?country=<SITE>`
- Current output promise:
  - when auth is reusable and the route no longer falls back to marketing shell, emit real `51/52` rows
  - otherwise emit standards-aligned blocked rows with `关键词价值状态=HOLD` and `广告依赖状态 / 坑位稳定性状态 = HOLD`

## Reason Codes

- `PROFILE_INITIALIZED`
- `LOGIN_SURFACE_PROBED__AUTH_REQUIRED`
- `LOGIN_SURFACE_PROBED__AUTH_REUSABLE`
- `AUTH_BOOTSTRAP_COMPLETED`
- `AUTH_REQUIRED__MANUAL_LOGIN_NOT_COMPLETED`
- `LOGIN_SURFACE_NOT_REACHABLE`
- `SIF_AUTH_REQUIRED`
- `DETAIL_ROUTE_FALLBACK_TO_MARKETING_PAGE`
- `SEARCH_ROUTE_FALLBACK_TO_MARKETING_PAGE`

## Current Status

- Current classification is `PARTIAL_SURFACE_ONLY`.
- What is verified now:
  - isolated repo-local SIF profile path
  - browser probe
  - login surface trigger
  - auth API truth
  - standards-aligned blocked outputs for detail/search probes
- What is not yet verified:
  - reusable authenticated SIF storage state
  - non-marketing detail surface data
  - non-marketing search / pit surface data
  - extension-loaded execution path
