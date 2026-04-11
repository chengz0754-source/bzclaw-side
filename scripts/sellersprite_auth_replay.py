from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from keyword_chain_common import REPLAY_PROFILE_DIR, ROOT, STORAGE_STATE_PATH, append_jsonl, ensure_within_repo, iso_now, write_json_atomic
from sellersprite_auth_registry import (
    LOGIN_REPLAY_REGISTRY_PATH,
    LOGIN_REPLAY_SNIPPET_ROOT,
    OWNER_RECORDING_ROOT,
    ensure_login_replay_registry,
    is_auth_reason,
    register_login_replay,
)


MANIFEST_FILE_NAME = "recording_manifest.json"
REPLAY_ATTEMPT_LATEST = ROOT / "logs" / "sellersprite_auth_incidents" / "latest_replay_attempt.json"
REPLAY_ATTEMPT_HISTORY = ROOT / "logs" / "sellersprite_auth_incidents" / "replay_attempts.jsonl"
REPLAY_BACKUP_DIR = ROOT / "playwright" / "auth" / "replay_backups"
PROFILE_BACKUP_DIR = REPLAY_BACKUP_DIR / "profiles"
RUNTIME_REPLAY_PROFILE_ROOT = ROOT / "logs" / "runtime_replay_profiles"

REPLAY_KIND_STORAGE_STATE_COPY = "storage_state_copy"
REPLAY_KIND_PERSISTENT_PROFILE_SEED = "persistent_profile_seed"
PROFILE_SEED_MODE_REBUILD = "rebuild"

SURFACE_REPLAY_POLICIES: dict[str, dict[str, Any]] = {
    "SELLERSPRITE_PRODUCT_RESEARCH_AUTH": {
        "source_surface_family": "SELLERSPRITE_PRODUCT_RESEARCH_AUTH",
        "applicable_modules": ["product_research", "market_export"],
        "replay_kind": REPLAY_KIND_PERSISTENT_PROFILE_SEED,
        "execution_mode_override": "persistent",
        "profile_seed_mode": PROFILE_SEED_MODE_REBUILD,
        "notes": "Use the Product Research owner recording to rebuild the dedicated SellerSprite persistent profile before retrying Product Research or STEP3 handoff reopening.",
    },
    "SELLERSPRITE_EXPORT_LOG_AUTH": {
        "source_surface_family": "SELLERSPRITE_KEYWORD_MINER_AUTH",
        "applicable_modules": ["product_research", "benchmark_export", "market_export", "sellersprite_nightly_orchestrator"],
        "replay_kind": REPLAY_KIND_PERSISTENT_PROFILE_SEED,
        "execution_mode_override": "persistent",
        "profile_seed_mode": PROFILE_SEED_MODE_REBUILD,
        "notes": "Use the verified keyword-miner owner state to rebuild the dedicated SellerSprite persistent profile before retrying export-log flows.",
    },
    "SELLERSPRITE_MARKET_RESEARCH_AUTH": {
        "source_surface_family": "SELLERSPRITE_MARKET_RESEARCH_AUTH",
        "applicable_modules": ["market_export", "sellersprite_nightly_orchestrator"],
        "replay_kind": REPLAY_KIND_STORAGE_STATE_COPY,
        "execution_mode_override": "storage_state",
        "notes": "Market replay currently refreshes the canonical storage-state slot before a single storage_state retry.",
    },
    "SELLERSPRITE_KEYWORD_MINER_AUTH": {
        "source_surface_family": "SELLERSPRITE_KEYWORD_MINER_AUTH",
        "applicable_modules": ["keyword_research", "keyword_trend", "sellersprite_keyword_export_flow"],
        "replay_kind": REPLAY_KIND_STORAGE_STATE_COPY,
        "execution_mode_override": "storage_state",
        "notes": "Keyword replay currently refreshes the canonical storage-state slot before a single storage_state retry.",
    },
    "SELLERSPRITE_COMPETITOR_LOOKUP_AUTH": {
        "source_surface_family": "SELLERSPRITE_KEYWORD_MINER_AUTH",
        "applicable_modules": ["benchmark_export", "product_research"],
        "replay_kind": REPLAY_KIND_PERSISTENT_PROFILE_SEED,
        "execution_mode_override": "persistent",
        "profile_seed_mode": PROFILE_SEED_MODE_REBUILD,
        "notes": "Competitor lookup shares the same dedicated persistent-profile repair path as Product Research.",
    },
}


class SellerSpriteReplayError(RuntimeError):
    def __init__(self, message: str, reason_code: str = "SELLERSPRITE_AUTH_REPLAY_ERROR") -> None:
        super().__init__(message)
        self.reason_code = reason_code


def slugify(value: Any) -> str:
    text = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in str(value or "").strip())
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-") or "item"


def owner_recording_dir(surface_family: str) -> Path:
    return ensure_within_repo(OWNER_RECORDING_ROOT / str(surface_family).strip(), "owner_recording_dir")


def manifest_path_for_surface(surface_family: str) -> Path:
    return ensure_within_repo(owner_recording_dir(surface_family) / MANIFEST_FILE_NAME, "recording_manifest_path")


def snippet_path_for_surface(surface_family: str) -> Path:
    file_name = f"{slugify(str(surface_family).lower())}_replay.py"
    return ensure_within_repo(LOGIN_REPLAY_SNIPPET_ROOT / file_name, "replay_snippet_path")


def _file_sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_recording_manifest(
    surface_family: str,
    *,
    source_surface_family: str | None = None,
    applicable_modules: list[str] | None = None,
    replay_kind: str = REPLAY_KIND_STORAGE_STATE_COPY,
    execution_mode_override: str = "storage_state",
    profile_seed_mode: str = "",
    notes: str = "",
) -> dict[str, Any]:
    resolved_source_surface = str(source_surface_family or surface_family).strip()
    source_dir = owner_recording_dir(resolved_source_surface)
    recording_script_path = ensure_within_repo(source_dir / "owner_fake_login_recording.py", "owner_fake_login_recording")
    storage_state_path = ensure_within_repo(source_dir / "storage_state.json", "owner_storage_state_path")
    if not recording_script_path.exists():
        raise SellerSpriteReplayError(f"Owner recording script is missing: {recording_script_path}", "OWNER_RECORDING_SCRIPT_MISSING")
    if not storage_state_path.exists():
        raise SellerSpriteReplayError(f"Owner storage state is missing: {storage_state_path}", "OWNER_RECORDING_STORAGE_STATE_MISSING")
    return {
        "version": 1,
        "surface_family": str(surface_family).strip(),
        "source_surface_family": resolved_source_surface,
        "created_at": iso_now(),
        "updated_at": iso_now(),
        "owner_recording_dir": str(source_dir),
        "owner_recording_script_path": str(recording_script_path),
        "storage_state_path": str(storage_state_path),
        "storage_state_sha1": _file_sha1(storage_state_path),
        "recording_script_sha1": _file_sha1(recording_script_path),
        "replay_kind": replay_kind,
        "execution_mode_override": execution_mode_override,
        "canonical_storage_state_target": str(STORAGE_STATE_PATH),
        "canonical_profile_target": str(REPLAY_PROFILE_DIR),
        "profile_seed_mode": profile_seed_mode,
        "applicable_modules": sorted({str(item).strip() for item in applicable_modules or [] if str(item).strip()}),
        "notes": notes
        or (
            "Generated from an owner fake-login recording. Formal replay copies this storage_state into the canonical SellerSprite storage-state slot before a single storage_state retry."
            if replay_kind == REPLAY_KIND_STORAGE_STATE_COPY
            else "Generated from an owner fake-login recording. Formal replay rebuilds the dedicated SellerSprite persistent profile from this owner storage state before a single persistent retry."
        ),
    }


def write_recording_manifest(
    surface_family: str,
    *,
    source_surface_family: str | None = None,
    applicable_modules: list[str] | None = None,
    replay_kind: str = REPLAY_KIND_STORAGE_STATE_COPY,
    execution_mode_override: str = "storage_state",
    profile_seed_mode: str = "",
    notes: str = "",
) -> Path:
    manifest_path = manifest_path_for_surface(surface_family)
    payload = build_recording_manifest(
        surface_family,
        source_surface_family=source_surface_family,
        applicable_modules=applicable_modules,
        replay_kind=replay_kind,
        execution_mode_override=execution_mode_override,
        profile_seed_mode=profile_seed_mode,
        notes=notes,
    )
    write_json_atomic(manifest_path, payload)
    return manifest_path


def write_replay_snippet(surface_family: str, manifest_path: Path, replay_kind: str) -> Path:
    snippet_path = snippet_path_for_surface(surface_family)
    snippet_path.parent.mkdir(parents=True, exist_ok=True)
    snippet = (
        '"""Local-only SellerSprite replay asset. Do not commit.\\n'
        "Generated from an owner fake-login recording.\\n"
        '"""\\n\\n'
        f'SURFACE_FAMILY = "{surface_family}"\\n'
        f'REPLAY_KIND = "{replay_kind}"\\n'
        f'OWNER_RECORDING_MANIFEST_PATH = r"{manifest_path}"\\n'
    )
    snippet_path.write_text(snippet, encoding="utf-8")
    return snippet_path


def prepare_and_register_replay(
    surface_family: str,
    *,
    source_surface_family: str | None = None,
    applicable_modules: list[str] | None = None,
    last_verified_at: str = "",
    dry_run: bool = False,
    replay_kind: str = REPLAY_KIND_STORAGE_STATE_COPY,
    execution_mode_override: str = "storage_state",
    profile_seed_mode: str = "",
    notes: str = "",
) -> dict[str, Any]:
    manifest_path = write_recording_manifest(
        surface_family,
        source_surface_family=source_surface_family,
        applicable_modules=applicable_modules,
        replay_kind=replay_kind,
        execution_mode_override=execution_mode_override,
        profile_seed_mode=profile_seed_mode,
        notes=notes,
    )
    snippet_path = write_replay_snippet(surface_family, manifest_path, replay_kind)
    entry = register_login_replay(
        surface_family=surface_family,
        recording_manifest_path=manifest_path,
        replay_snippet_path=snippet_path,
        applicable_modules=applicable_modules,
        last_verified_at=last_verified_at or iso_now(),
        dry_run=dry_run,
    )
    return {
        "surface_family": surface_family,
        "source_surface_family": str(source_surface_family or surface_family).strip(),
        "recording_manifest_path": str(manifest_path),
        "replay_snippet_path": str(snippet_path),
        "registry_entry": entry,
    }


def default_replay_plan() -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for surface_family, policy in SURFACE_REPLAY_POLICIES.items():
        plan.append(
            {
                "surface_family": surface_family,
                "source_surface_family": str(policy.get("source_surface_family", surface_family)).strip(),
                "applicable_modules": list(policy.get("applicable_modules", [])),
                "replay_kind": str(policy.get("replay_kind", REPLAY_KIND_STORAGE_STATE_COPY)).strip(),
                "execution_mode_override": str(policy.get("execution_mode_override", "storage_state")).strip(),
                "profile_seed_mode": str(policy.get("profile_seed_mode", "")).strip(),
                "notes": str(policy.get("notes", "")).strip(),
            }
        )
    return plan


def prepare_default_replays(*, dry_run: bool = False) -> dict[str, Any]:
    results = []
    for item in default_replay_plan():
        results.append(
            prepare_and_register_replay(
                str(item["surface_family"]),
                source_surface_family=str(item["source_surface_family"]),
                applicable_modules=list(item.get("applicable_modules", [])),
                dry_run=dry_run,
                replay_kind=str(item.get("replay_kind", REPLAY_KIND_STORAGE_STATE_COPY)).strip(),
                execution_mode_override=str(item.get("execution_mode_override", "storage_state")).strip(),
                profile_seed_mode=str(item.get("profile_seed_mode", "")).strip(),
                notes=str(item.get("notes", "")).strip(),
            )
        )
    return {
        "prepared_at": iso_now(),
        "dry_run": dry_run,
        "prepared_surfaces": results,
    }


def load_registry_entry(surface_family: str) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = ensure_login_replay_registry()
    entries = registry.get("entries", [])
    if isinstance(entries, list):
        for entry in entries:
            if str(entry.get("surface_family", "")).strip() == str(surface_family).strip():
                return registry, entry
    raise SellerSpriteReplayError(f"No replay-registry entry exists for {surface_family}.", "LOGIN_REPLAY_ENTRY_MISSING")


def _load_manifest_from_entry(entry: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    manifest_raw = str(entry.get("owner_recording_manifest_path", "")).strip()
    if not manifest_raw:
        manifest_raw = str(Path(str(entry.get("owner_recording_drop_path", "")).strip()) / MANIFEST_FILE_NAME)
    manifest_path = ensure_within_repo(Path(manifest_raw), "owner_recording_manifest_path")
    if not manifest_path.exists():
        raise SellerSpriteReplayError(f"Replay manifest is missing: {manifest_path}", "LOGIN_REPLAY_MANIFEST_MISSING")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SellerSpriteReplayError(f"Replay manifest is not a JSON object: {manifest_path}", "LOGIN_REPLAY_MANIFEST_INVALID")
    return manifest_path, payload


def summary_requests_auth_replay(summary: dict[str, Any], *, reason_keys: tuple[str, ...] = ("reason_code", "failure_reason_code")) -> bool:
    if not isinstance(summary, dict):
        return False
    if not bool(summary.get("auth_replay_available")):
        return False
    surface_family = str(summary.get("auth_surface_family", "")).strip()
    if not surface_family:
        return False
    if bool(summary.get("auth_replay_attempted")):
        return False
    for key in reason_keys:
        if is_auth_reason(summary.get(key)):
            return True
    return False


def _update_registry_verified_at(surface_family: str, verified_at: str) -> None:
    registry, _entry = load_registry_entry(surface_family)
    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        return
    for entry in entries:
        if str(entry.get("surface_family", "")).strip() != str(surface_family).strip():
            continue
        entry["last_verified_at"] = verified_at
        break
    registry["updated_at"] = iso_now()
    write_json_atomic(LOGIN_REPLAY_REGISTRY_PATH, registry)


def _load_storage_state_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SellerSpriteReplayError(f"Replay storage state is not a JSON object: {path}", "LOGIN_REPLAY_STORAGE_STATE_INVALID")
    return payload


def _apply_storage_state_payload_to_context(context, payload: dict[str, Any]) -> dict[str, int]:
    cookies = payload.get("cookies", [])
    if isinstance(cookies, list) and cookies:
        context.add_cookies(cookies)

    origin_count = 0
    origins = payload.get("origins", [])
    if isinstance(origins, list):
        for origin in origins:
            if not isinstance(origin, dict):
                continue
            origin_url = str(origin.get("origin", "")).strip()
            if not origin_url:
                continue
            origin_count += 1
            page = context.new_page()
            try:
                page.goto(origin_url, wait_until="domcontentloaded", timeout=90000)
                for item in origin.get("localStorage", []):
                    if not isinstance(item, dict):
                        continue
                    name = item.get("name")
                    if name is None:
                        continue
                    value = item.get("value", "")
                    page.evaluate("([k, v]) => window.localStorage.setItem(k, v)", [str(name), str(value)])
            finally:
                try:
                    page.close()
                except Exception:
                    pass

    return {
        "seeded_cookie_count": len(cookies) if isinstance(cookies, list) else 0,
        "seeded_origin_count": origin_count,
    }


def _seed_persistent_profile_from_storage_state(
    source_storage_state_path: Path,
    *,
    target_profile_dir: Path,
    surface_family: str,
    started_at: str,
    profile_seed_mode: str,
) -> dict[str, Any]:
    payload = _load_storage_state_payload(source_storage_state_path)
    target_profile_dir = ensure_within_repo(target_profile_dir, "replay_profile_target")
    backup_profile_path = ""

    if target_profile_dir.exists() and any(target_profile_dir.iterdir()) and profile_seed_mode == PROFILE_SEED_MODE_REBUILD:
        backup_dir = ensure_within_repo(
            PROFILE_BACKUP_DIR / f"{slugify(surface_family)}-{started_at.replace(':', '').replace('+', '_')}",
            "replay_profile_backup_dir",
        )
        backup_dir.parent.mkdir(parents=True, exist_ok=True)
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.move(str(target_profile_dir), str(backup_dir))
        backup_profile_path = str(backup_dir)

    target_profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(target_profile_dir),
            channel="msedge",
            headless=False,
            viewport={"width": 1600, "height": 1400},
            accept_downloads=True,
        )
        try:
            seed_counts = _apply_storage_state_payload_to_context(context, payload)
        finally:
            try:
                context.close()
            except Exception:
                pass
    time.sleep(1.5)

    return {
        "profile_target_path": str(target_profile_dir),
        "profile_backup_path": backup_profile_path,
        "seeded_cookie_count": seed_counts.get("seeded_cookie_count", 0),
        "seeded_origin_count": seed_counts.get("seeded_origin_count", 0),
    }


def launch_runtime_seeded_persistent_context(
    playwright,
    *,
    surface_family: str,
    headless: bool,
    viewport: dict[str, int],
    accept_downloads: bool,
    channel: str = "msedge",
) -> tuple[Any, dict[str, Any]]:
    _registry, entry = load_registry_entry(surface_family)
    if not bool(entry.get("has_replay")):
        raise SellerSpriteReplayError(f"Replay is not registered for {surface_family}.", "LOGIN_REPLAY_NOT_REGISTERED")
    manifest_path, manifest = _load_manifest_from_entry(entry)
    source_storage_state_path = ensure_within_repo(Path(str(manifest.get("storage_state_path", "")).strip()), "runtime_replay_source_storage_state")
    if not source_storage_state_path.exists():
        raise SellerSpriteReplayError(f"Replay storage state is missing: {source_storage_state_path}", "LOGIN_REPLAY_STORAGE_STATE_MISSING")

    runtime_profile_dir = ensure_within_repo(
        RUNTIME_REPLAY_PROFILE_ROOT / f"{slugify(surface_family)}-{iso_now().replace(':', '').replace('+', '_')}",
        "runtime_replay_profile_dir",
    )
    if runtime_profile_dir.exists():
        shutil.rmtree(runtime_profile_dir)
    runtime_profile_dir.mkdir(parents=True, exist_ok=True)

    payload = _load_storage_state_payload(source_storage_state_path)
    context = playwright.chromium.launch_persistent_context(
        str(runtime_profile_dir),
        channel=channel,
        headless=headless,
        viewport=viewport,
        accept_downloads=accept_downloads,
    )
    seed_counts = _apply_storage_state_payload_to_context(context, payload)
    info = {
        "runtime_profile_dir": str(runtime_profile_dir),
        "source_storage_state_path": str(source_storage_state_path),
        "recording_manifest_path": str(manifest_path),
        "seeded_cookie_count": seed_counts.get("seeded_cookie_count", 0),
        "seeded_origin_count": seed_counts.get("seeded_origin_count", 0),
        "source_surface_family": str(manifest.get("source_surface_family", manifest.get("surface_family", ""))).strip(),
    }
    return context, info


def perform_registered_login_replay(
    *,
    surface_family: str,
    module_name: str,
    trigger_reason_code: str,
    trigger_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started_at = iso_now()
    result: dict[str, Any] = {
        "timestamp": started_at,
        "surface_family": str(surface_family).strip(),
        "module_name": str(module_name).strip(),
        "trigger_reason_code": str(trigger_reason_code).strip(),
        "status": "FAILED",
        "reason_code": "",
        "message": "",
        "replay_snippet_path": "",
        "recording_manifest_path": "",
        "source_storage_state_path": "",
        "target_storage_state_path": str(STORAGE_STATE_PATH),
        "backup_storage_state_path": "",
        "execution_mode_override": "",
        "profile_target_path": "",
        "profile_backup_path": "",
    }
    try:
        registry, entry = load_registry_entry(surface_family)
        if not bool(entry.get("has_replay")):
            raise SellerSpriteReplayError(f"Replay is not registered for {surface_family}.", "LOGIN_REPLAY_NOT_REGISTERED")
        manifest_path, manifest = _load_manifest_from_entry(entry)
        source_storage_state_path = ensure_within_repo(Path(str(manifest.get("storage_state_path", "")).strip()), "replay_source_storage_state")
        if not source_storage_state_path.exists():
            raise SellerSpriteReplayError(f"Replay storage state is missing: {source_storage_state_path}", "LOGIN_REPLAY_STORAGE_STATE_MISSING")
        replay_kind = str(manifest.get("replay_kind", REPLAY_KIND_STORAGE_STATE_COPY)).strip() or REPLAY_KIND_STORAGE_STATE_COPY
        execution_mode_override = str(manifest.get("execution_mode_override", "")).strip()

        if replay_kind == REPLAY_KIND_PERSISTENT_PROFILE_SEED:
            profile_target = ensure_within_repo(
                Path(str(manifest.get("canonical_profile_target", "")).strip() or REPLAY_PROFILE_DIR),
                "replay_profile_target",
            )
            seed_result = _seed_persistent_profile_from_storage_state(
                source_storage_state_path,
                target_profile_dir=profile_target,
                surface_family=surface_family,
                started_at=started_at,
                profile_seed_mode=str(manifest.get("profile_seed_mode", PROFILE_SEED_MODE_REBUILD)).strip() or PROFILE_SEED_MODE_REBUILD,
            )
            result["profile_target_path"] = str(seed_result.get("profile_target_path", ""))
            result["profile_backup_path"] = str(seed_result.get("profile_backup_path", ""))
            result["seeded_cookie_count"] = seed_result.get("seeded_cookie_count", 0)
            result["seeded_origin_count"] = seed_result.get("seeded_origin_count", 0)
        else:
            STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            if STORAGE_STATE_PATH.exists():
                backup_path = ensure_within_repo(
                    REPLAY_BACKUP_DIR / f"{slugify(surface_family)}-{started_at.replace(':', '').replace('+', '_')}.json",
                    "replay_backup_storage_state",
                )
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(STORAGE_STATE_PATH, backup_path)
                result["backup_storage_state_path"] = str(backup_path)
            shutil.copy2(source_storage_state_path, STORAGE_STATE_PATH)

        verified_at = iso_now()
        _update_registry_verified_at(surface_family, verified_at)
        result.update(
            {
                "status": "PASS",
                "reason_code": "LOGIN_REPLAY_APPLIED",
                "message": (
                    "Registered owner storage_state was copied into the canonical SellerSprite storage-state slot."
                    if replay_kind == REPLAY_KIND_STORAGE_STATE_COPY
                    else "Registered owner storage_state was used to rebuild the dedicated SellerSprite persistent profile."
                ),
                "replay_snippet_path": str(entry.get("replay_snippet_path", "")).strip(),
                "recording_manifest_path": str(manifest_path),
                "source_storage_state_path": str(source_storage_state_path),
                "last_verified_at": verified_at,
                "replay_registry_path": str(LOGIN_REPLAY_REGISTRY_PATH),
                "registry_modules": list(entry.get("applicable_modules", [])),
                "manifest_source_surface_family": str(manifest.get("source_surface_family", manifest.get("surface_family", ""))).strip(),
                "replay_kind": replay_kind,
                "execution_mode_override": execution_mode_override or ("persistent" if replay_kind == REPLAY_KIND_PERSISTENT_PROFILE_SEED else "storage_state"),
            }
        )
        if isinstance(trigger_summary, dict) and trigger_summary:
            result["trigger_summary_snapshot"] = {
                key: trigger_summary.get(key)
                for key in (
                    "status",
                    "reason_code",
                    "failure_reason_code",
                    "message",
                    "failure_reason",
                    "auth_surface_family",
                    "auth_incident_path",
                )
                if key in trigger_summary
            }
    except SellerSpriteReplayError as exc:
        result["reason_code"] = exc.reason_code
        result["message"] = str(exc)
    except Exception as exc:
        result["reason_code"] = "LOGIN_REPLAY_UNHANDLED_ERROR"
        result["message"] = str(exc)

    write_json_atomic(REPLAY_ATTEMPT_LATEST, result)
    append_jsonl(REPLAY_ATTEMPT_HISTORY, result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare or apply local-only SellerSprite auth replay assets.")
    parser.add_argument("--prepare-default-replays", action="store_true")
    parser.add_argument("--surface-family", action="append", default=[])
    parser.add_argument("--source-surface-family", default=None)
    parser.add_argument("--module", action="append", default=[])
    parser.add_argument("--apply-replay", action="store_true")
    parser.add_argument("--trigger-reason-code", default="SELLERSPRITE_AUTH_REQUIRED")
    parser.add_argument("--module-name", default="")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.prepare_default_replays:
        payload = prepare_default_replays(dry_run=bool(args.dry_run))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    surfaces = [str(item).strip() for item in args.surface_family if str(item).strip()]
    if args.apply_replay:
        if len(surfaces) != 1:
            raise SystemExit("--apply-replay requires exactly one --surface-family.")
        payload = perform_registered_login_replay(
            surface_family=surfaces[0],
            module_name=str(args.module_name or surfaces[0]).strip(),
            trigger_reason_code=str(args.trigger_reason_code).strip(),
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("status") == "PASS" else 2

    if not surfaces:
        raise SystemExit("Specify --prepare-default-replays or at least one --surface-family.")

    payload = {
        "prepared_at": iso_now(),
        "dry_run": bool(args.dry_run),
        "prepared_surfaces": [
            prepare_and_register_replay(
                surface_family=surface_family,
                source_surface_family=str(args.source_surface_family or surface_family).strip(),
                applicable_modules=[str(item).strip() for item in args.module if str(item).strip()],
                dry_run=bool(args.dry_run),
            )
            for surface_family in surfaces
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
