from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

from keyword_chain_common import ROOT, append_jsonl, compact_text, ensure_within_repo, iso_now, write_json_atomic
from sellersprite_overlay_guard import capture_screenshot, page_identity


AUTH_INCIDENTS_DIR = ROOT / "logs" / "sellersprite_auth_incidents"
AUTH_SNAPSHOT_DIR = AUTH_INCIDENTS_DIR / "page_snapshots"
AUTH_RECORD_DIR = AUTH_INCIDENTS_DIR / "incidents"
LATEST_AUTH_INCIDENT = AUTH_INCIDENTS_DIR / "latest_auth_incident.json"
AUTH_INCIDENTS_HISTORY = AUTH_INCIDENTS_DIR / "auth_incidents.jsonl"
AUTH_SCREENSHOT_DIR = ROOT / "playwright" / "screenshots" / "sellersprite_auth_incidents"
LOGIN_REPLAY_REGISTRY_PATH = ROOT / "playwright" / "auth" / "login_replay_registry.json"
LOGIN_REPLAY_SNIPPET_ROOT = ROOT / "playwright" / "auth" / "login_replays"
OWNER_RECORDING_ROOT = ROOT / "playwright" / "auth" / "owner_recordings"

AUTH_REASON_CODES = {
    "SELLERSPRITE_AUTH_REQUIRED",
    "KEYWORD_TREND_AUTH_REQUIRED",
    "EXPORT_LOG_REDIRECTED_TO_LOGIN",
}


def slugify(value: Any) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip()).strip("-")
    return slug or "item"


def snapshot_from_page(page) -> dict[str, Any]:
    return page_identity(page)


def auth_surface_detected(
    *,
    page=None,
    page_snapshot: dict[str, Any] | None = None,
    current_url: str = "",
    title: str = "",
) -> bool:
    snapshot = page_snapshot or (snapshot_from_page(page) if page is not None else {})
    url = str(current_url or snapshot.get("url", "")).strip().lower()
    page_title = str(title or snapshot.get("title", "")).strip().lower()
    body_excerpt = str(snapshot.get("body_excerpt", "")).strip().lower()
    guest_markers = snapshot.get("guest_markers", [])
    auth_markers = (
        "登录",
        "未登录",
        "游客",
        "立即登录",
        "主人~ 您当前是游客身份",
        "建议 立即登录 后使用",
    )
    if any(marker.lower() in page_title for marker in auth_markers):
        return True
    if any(marker.lower() in body_excerpt for marker in auth_markers):
        return True
    return bool(
        "/w/user/login" in url
        or "login" in url
        or "登录" in page_title
        or "login" in page_title
        or guest_markers
        or "未登录" in body_excerpt
        or "游客" in body_excerpt
    )


def is_auth_reason(reason_code: Any) -> bool:
    normalized = str(reason_code or "").strip().upper()
    return normalized in AUTH_REASON_CODES or "AUTH" in normalized or "LOGIN" in normalized


def _default_registry_entries() -> list[dict[str, Any]]:
    return [
        {
            "surface_family": "SELLERSPRITE_KEYWORD_MINER_AUTH",
            "login_page_type": "SELLERSPRITE_LOGIN_PAGE",
            "url_pattern": "/w/user/login?callback=%2Fv3%2Fkeyword-miner",
            "has_replay": False,
            "replay_snippet_path": "",
            "owner_recording_drop_path": str(ensure_within_repo(OWNER_RECORDING_ROOT / "SELLERSPRITE_KEYWORD_MINER_AUTH", "keyword_owner_recording_dir")),
            "last_verified_at": "",
            "applicable_modules": ["keyword_research", "keyword_trend", "sellersprite_keyword_export_flow"],
            "notes": "Owner records one fake login on the keyword-miner surface; Codex then registers the reusable replay snippet.",
        },
        {
            "surface_family": "SELLERSPRITE_EXPORT_LOG_AUTH",
            "login_page_type": "SELLERSPRITE_LOGIN_PAGE",
            "url_pattern": "/w/user/login?callback=%2Fv2%2Fexport-log",
            "has_replay": False,
            "replay_snippet_path": "",
            "owner_recording_drop_path": str(ensure_within_repo(OWNER_RECORDING_ROOT / "SELLERSPRITE_EXPORT_LOG_AUTH", "export_log_owner_recording_dir")),
            "last_verified_at": "",
            "applicable_modules": ["benchmark_export", "sellersprite_nightly_orchestrator"],
            "notes": "This is the current blocker for benchmark workbook export. Do not auto-login; wait for owner recording.",
        },
        {
            "surface_family": "SELLERSPRITE_MARKET_RESEARCH_AUTH",
            "login_page_type": "SELLERSPRITE_LOGIN_PAGE",
            "url_pattern": "/w/user/login?callback=%2Fv2%2Fmarket-research",
            "has_replay": False,
            "replay_snippet_path": "",
            "owner_recording_drop_path": str(ensure_within_repo(OWNER_RECORDING_ROOT / "SELLERSPRITE_MARKET_RESEARCH_AUTH", "market_owner_recording_dir")),
            "last_verified_at": "",
            "applicable_modules": ["market_export", "sellersprite_nightly_orchestrator"],
            "notes": "Use a single owner-supplied fake-login recording instead of repeated manual daytime logins.",
        },
        {
            "surface_family": "SELLERSPRITE_PRODUCT_RESEARCH_AUTH",
            "login_page_type": "SELLERSPRITE_LOGIN_PAGE",
            "url_pattern": "/w/user/login?callback=%2Fv3%2Fproduct-research",
            "has_replay": False,
            "replay_snippet_path": "",
            "owner_recording_drop_path": str(ensure_within_repo(OWNER_RECORDING_ROOT / "SELLERSPRITE_PRODUCT_RESEARCH_AUTH", "product_research_owner_recording_dir")),
            "last_verified_at": "",
            "applicable_modules": ["product_research", "market_export"],
            "notes": "Real Product Research export and STEP3 handoff reopening depend on this family. Wait for one owner fake-login recording before registering a reusable replay.",
        },
        {
            "surface_family": "SELLERSPRITE_COMPETITOR_LOOKUP_AUTH",
            "login_page_type": "SELLERSPRITE_LOGIN_PAGE",
            "url_pattern": "/w/user/login?callback=%2Fv3%2Fcompetitor-lookup",
            "has_replay": False,
            "replay_snippet_path": "",
            "owner_recording_drop_path": str(ensure_within_repo(OWNER_RECORDING_ROOT / "SELLERSPRITE_COMPETITOR_LOOKUP_AUTH", "competitor_owner_recording_dir")),
            "last_verified_at": "",
            "applicable_modules": ["benchmark_export"],
            "notes": "Benchmark and product-entry both depend on the competitor-lookup family.",
        },
        {
            "surface_family": "SELLERSPRITE_LOGIN_GENERIC",
            "login_page_type": "SELLERSPRITE_LOGIN_PAGE",
            "url_pattern": "/w/user/login",
            "has_replay": False,
            "replay_snippet_path": "",
            "owner_recording_drop_path": str(ensure_within_repo(OWNER_RECORDING_ROOT / "SELLERSPRITE_LOGIN_GENERIC", "generic_owner_recording_dir")),
            "last_verified_at": "",
            "applicable_modules": ["keyword_research", "keyword_trend", "market_export", "benchmark_export", "product_research", "sellersprite_nightly_orchestrator"],
            "notes": "Fallback bucket for auth incidents that do not match a tighter SellerSprite surface family.",
        },
    ]


def ensure_login_replay_registry() -> dict[str, Any]:
    registry = {
        "version": 1,
        "updated_at": iso_now(),
        "snippet_root": str(ensure_within_repo(LOGIN_REPLAY_SNIPPET_ROOT, "login_replay_snippet_root")),
        "owner_recording_root": str(ensure_within_repo(OWNER_RECORDING_ROOT, "owner_recording_root")),
        "entries": _default_registry_entries(),
    }
    if LOGIN_REPLAY_REGISTRY_PATH.exists():
        try:
            payload = json.loads(LOGIN_REPLAY_REGISTRY_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict):
            merged_entries = payload.get("entries", [])
            if isinstance(merged_entries, list) and merged_entries:
                by_surface: dict[str, dict[str, Any]] = {}
                ordered_surfaces: list[str] = []
                for entry in registry["entries"]:
                    surface_family = str(entry.get("surface_family", "")).strip()
                    if not surface_family:
                        continue
                    by_surface[surface_family] = entry
                    ordered_surfaces.append(surface_family)
                for entry in merged_entries:
                    if not isinstance(entry, dict):
                        continue
                    surface_family = str(entry.get("surface_family", "")).strip()
                    if not surface_family:
                        continue
                    by_surface[surface_family] = entry
                    if surface_family not in ordered_surfaces:
                        ordered_surfaces.append(surface_family)
                registry["entries"] = [by_surface[surface_family] for surface_family in ordered_surfaces if surface_family in by_surface]
            registry["version"] = int(payload.get("version", registry["version"]))
    write_json_atomic(LOGIN_REPLAY_REGISTRY_PATH, registry)
    return registry


def infer_surface_family(module_name: str, current_url: str, redirect_from_url: str, body_excerpt: str = "") -> str:
    combined = " ".join([str(module_name or ""), str(current_url or ""), str(redirect_from_url or ""), str(body_excerpt or "")]).lower()
    if "export-log" in combined:
        return "SELLERSPRITE_EXPORT_LOG_AUTH"
    if "keyword-miner" in combined:
        return "SELLERSPRITE_KEYWORD_MINER_AUTH"
    if "market-research" in combined:
        return "SELLERSPRITE_MARKET_RESEARCH_AUTH"
    if "product-research" in combined or "product_research" in combined:
        return "SELLERSPRITE_PRODUCT_RESEARCH_AUTH"
    if "competitor-lookup" in combined or "product-entry" in combined or "product_research" in combined:
        return "SELLERSPRITE_COMPETITOR_LOOKUP_AUTH"
    return "SELLERSPRITE_LOGIN_GENERIC"


def lookup_login_replay(
    *,
    module_name: str,
    current_url: str,
    redirect_from_url: str,
    page_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = ensure_login_replay_registry()
    snapshot = page_snapshot or {}
    surface_family = infer_surface_family(module_name, current_url, redirect_from_url, str(snapshot.get("body_excerpt", "")))
    entries = registry.get("entries", [])
    if isinstance(entries, list):
        for entry in entries:
            if str(entry.get("surface_family", "")).strip() == surface_family:
                return {
                    "surface_family": surface_family,
                    "entry": entry,
                    "registry_path": str(LOGIN_REPLAY_REGISTRY_PATH),
                }
    fallback = {
        "surface_family": "SELLERSPRITE_LOGIN_GENERIC",
        "entry": {
            "surface_family": "SELLERSPRITE_LOGIN_GENERIC",
            "login_page_type": "SELLERSPRITE_LOGIN_PAGE",
            "url_pattern": "/w/user/login",
            "has_replay": False,
            "replay_snippet_path": "",
            "owner_recording_drop_path": str(ensure_within_repo(OWNER_RECORDING_ROOT / "SELLERSPRITE_LOGIN_GENERIC", "generic_owner_recording_dir")),
            "last_verified_at": "",
            "applicable_modules": [module_name],
            "notes": "",
        },
        "registry_path": str(LOGIN_REPLAY_REGISTRY_PATH),
    }
    return fallback


def _incident_paths(module_name: str, step_name: str, surface_family: str) -> dict[str, Path]:
    stamp = iso_now().replace(":", "").replace("+", "_")
    stem = f"{stamp}-{slugify(module_name)}-{slugify(step_name)}-{slugify(surface_family)}"
    return {
        "snapshot_json": ensure_within_repo(AUTH_SNAPSHOT_DIR / f"{stem}.json", "auth_snapshot_json"),
        "snapshot_html": ensure_within_repo(AUTH_SNAPSHOT_DIR / f"{stem}.html", "auth_snapshot_html"),
    }


def _write_page_snapshot(
    *,
    module_name: str,
    step_name: str,
    surface_family: str,
    page=None,
    page_snapshot: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str, str]:
    snapshot = dict(page_snapshot or {})
    if not snapshot and page is not None:
        snapshot = snapshot_from_page(page)
    paths = _incident_paths(module_name, step_name, surface_family)
    write_json_atomic(paths["snapshot_json"], snapshot)
    html_path = ""
    if page is not None:
        try:
            html = page.content()
            paths["snapshot_html"].parent.mkdir(parents=True, exist_ok=True)
            paths["snapshot_html"].write_text(html, encoding="utf-8")
            html_path = str(paths["snapshot_html"])
        except Exception:
            html_path = ""
    return snapshot, str(paths["snapshot_json"]), html_path


def _materialize_auth_screenshot(module_name: str, step_name: str, screenshot_path: str) -> str:
    source = str(screenshot_path or "").strip()
    if not source:
        return ""
    source_path = Path(source)
    if not source_path.exists():
        return source
    target_name = f"{slugify(module_name)}-{slugify(step_name)}-{source_path.name}"
    target_path = ensure_within_repo(AUTH_SCREENSHOT_DIR / target_name, "auth_incident_screenshot_path")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.resolve() != target_path.resolve():
        shutil.copy2(source_path, target_path)
    return str(target_path)


def _incident_context(run_context: Any) -> dict[str, Any]:
    if run_context is None:
        return {}
    if isinstance(run_context, dict):
        return run_context
    if hasattr(run_context, "__dict__"):
        return dict(run_context.__dict__)
    return {"value": str(run_context)}


def register_auth_incident(
    *,
    module_name: str,
    step_name: str,
    source_script: str,
    reason_code: str,
    current_url: str = "",
    redirect_from_url: str = "",
    page=None,
    page_snapshot: dict[str, Any] | None = None,
    run_context: Any = None,
    screenshot_path: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    replay = lookup_login_replay(
        module_name=module_name,
        current_url=current_url,
        redirect_from_url=redirect_from_url,
        page_snapshot=page_snapshot,
    )
    entry = replay["entry"]
    surface_family = str(replay["surface_family"])
    snapshot, snapshot_json_path, snapshot_html_path = _write_page_snapshot(
        module_name=module_name,
        step_name=step_name,
        surface_family=surface_family,
        page=page,
        page_snapshot=page_snapshot,
    )
    resolved_url = str(current_url or snapshot.get("url", "")).strip()
    resolved_title = str(snapshot.get("title", "")).strip()
    resolved_redirect = str(redirect_from_url or "").strip()
    resolved_screenshot = str(screenshot_path or "").strip()
    if not resolved_screenshot and page is not None:
        try:
            resolved_screenshot = capture_screenshot(page, f"{module_name}-{step_name}-auth", AUTH_SCREENSHOT_DIR)
        except Exception:
            resolved_screenshot = ""
    elif resolved_screenshot:
        resolved_screenshot = _materialize_auth_screenshot(module_name, step_name, resolved_screenshot)
    incident_id = slugify(f"{iso_now()}-{module_name}-{step_name}-{surface_family}")
    incident_record_path = ensure_within_repo(AUTH_RECORD_DIR / f"{incident_id}.json", "incident_record_path")
    incident = {
        "incident_id": incident_id,
        "triggered_at": iso_now(),
        "module_name": module_name,
        "step_name": step_name,
        "current_url": resolved_url,
        "redirect_from_url": resolved_redirect,
        "page_title": resolved_title,
        "source_script": source_script,
        "current_run_context": _incident_context(run_context),
        "screenshot_path": resolved_screenshot,
        "page_snapshot_path": snapshot_json_path,
        "page_snapshot_html_path": snapshot_html_path,
        "reason_code": str(reason_code or "").strip(),
        "guest_markers": list(snapshot.get("guest_markers", [])),
        "body_excerpt": str(snapshot.get("body_excerpt", "")).strip()[:1200],
        "login_page_type": str(entry.get("login_page_type", "SELLERSPRITE_LOGIN_PAGE")),
        "surface_family": surface_family,
        "url_pattern": str(entry.get("url_pattern", "")),
        "has_login_replay": bool(entry.get("has_replay")),
        "replay_snippet_path": str(entry.get("replay_snippet_path", "")).strip(),
        "replay_registry_path": str(replay.get("registry_path", "")),
        "owner_recording_drop_path": str(entry.get("owner_recording_drop_path", "")).strip(),
        "applicable_modules": list(entry.get("applicable_modules", [])),
        "incident_record_path": str(incident_record_path),
    }
    if extra:
        incident["extra"] = extra
    write_json_atomic(incident_record_path, incident)
    write_json_atomic(LATEST_AUTH_INCIDENT, incident)
    append_jsonl(AUTH_INCIDENTS_HISTORY, incident)
    return incident


def replay_meta_from_incident(incident: dict[str, Any]) -> dict[str, Any]:
    return {
        "auth_incident_path": str(incident.get("incident_record_path", LATEST_AUTH_INCIDENT)),
        "auth_surface_family": str(incident.get("surface_family", "")).strip(),
        "auth_replay_available": bool(incident.get("has_login_replay")),
        "auth_replay_snippet_path": str(incident.get("replay_snippet_path", "")).strip(),
        "auth_owner_recording_drop_path": str(incident.get("owner_recording_drop_path", "")).strip(),
    }


def register_login_replay(
    *,
    surface_family: str,
    recording_manifest_path: Path,
    replay_snippet_path: Path,
    applicable_modules: list[str] | None = None,
    last_verified_at: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    registry = ensure_login_replay_registry()
    recording_manifest_path = ensure_within_repo(recording_manifest_path, "recording_manifest_path")
    replay_snippet_path = ensure_within_repo(replay_snippet_path, "replay_snippet_path")
    if not recording_manifest_path.exists():
        raise FileNotFoundError(f"Owner recording manifest does not exist: {recording_manifest_path}")
    if not replay_snippet_path.exists():
        raise FileNotFoundError(f"Replay snippet does not exist: {replay_snippet_path}")

    updated_entry: dict[str, Any] | None = None
    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        entries = []
    for entry in entries:
        if str(entry.get("surface_family", "")).strip() != surface_family:
            continue
        entry["has_replay"] = True
        entry["replay_snippet_path"] = str(replay_snippet_path)
        entry["owner_recording_manifest_path"] = str(recording_manifest_path)
        entry["last_verified_at"] = last_verified_at or iso_now()
        if applicable_modules:
            existing = {str(item).strip() for item in entry.get("applicable_modules", []) if str(item).strip()}
            existing.update(str(item).strip() for item in applicable_modules if str(item).strip())
            entry["applicable_modules"] = sorted(existing)
        updated_entry = entry
        break
    if updated_entry is None:
        updated_entry = {
            "surface_family": surface_family,
            "login_page_type": "SELLERSPRITE_LOGIN_PAGE",
            "url_pattern": "/w/user/login",
            "has_replay": True,
            "replay_snippet_path": str(replay_snippet_path),
            "owner_recording_manifest_path": str(recording_manifest_path),
            "owner_recording_drop_path": str(recording_manifest_path.parent),
            "last_verified_at": last_verified_at or iso_now(),
            "applicable_modules": sorted({str(item).strip() for item in applicable_modules or [] if str(item).strip()}),
            "notes": "Registered from owner-supplied fake-login recording.",
        }
        entries.append(updated_entry)
    registry["entries"] = entries
    registry["updated_at"] = iso_now()
    if not dry_run:
        write_json_atomic(LOGIN_REPLAY_REGISTRY_PATH, registry)
    return updated_entry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Register an owner-supplied SellerSprite login replay snippet.")
    parser.add_argument("--surface-family", required=True)
    parser.add_argument("--recording-manifest", required=True)
    parser.add_argument("--replay-snippet", required=True)
    parser.add_argument("--module", action="append", default=[])
    parser.add_argument("--last-verified-at", default="")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    entry = register_login_replay(
        surface_family=str(args.surface_family).strip(),
        recording_manifest_path=Path(args.recording_manifest).expanduser(),
        replay_snippet_path=Path(args.replay_snippet).expanduser(),
        applicable_modules=[str(item).strip() for item in args.module if str(item).strip()],
        last_verified_at=str(args.last_verified_at).strip(),
        dry_run=bool(args.dry_run),
    )
    print(json.dumps({"dry_run": bool(args.dry_run), "entry": entry}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
