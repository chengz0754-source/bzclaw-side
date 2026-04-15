from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from sellersprite_stage_closure_lib import find_repo_root, read_json, relpath_str, write_json, write_text  # noqa: E402

INPUT_CONTRACT_PATH = Path("contracts/state_sync_candidate_input_contract_v1.json")
RECORD_CONTRACT_PATH = Path("contracts/state_sync_candidate_record_contract_v1.json")
STATE_SYNC_SCHEMA_PATH = Path("docs/state_sync_io_contract.schema.json")
INPUT_SCHEMA_VERSION = "bzclaw.side.state_sync_candidate_input.v1"
FILENAME_SAFE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")


def normalize_relpath(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        raise ValueError("Relative path may not be empty.")
    if re.match(r"^[A-Za-z]:/", normalized):
        raise ValueError(f"Absolute paths are not allowed: {value}")
    if normalized.startswith("/") or normalized == ".." or normalized.startswith("../") or "/../" in normalized:
        raise ValueError(f"Parent traversal is not allowed: {value}")
    return normalized


def parse_iso8601(value: str) -> None:
    normalized = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO-8601 timestamp: {value}") from exc


def sha256_for_payload(content_format: str, payload_json: Any | None, payload_text: str | None) -> str:
    if content_format == "json":
        serialized = json.dumps(payload_json, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    if payload_text is None:
        raise ValueError("Missing text payload.")
    return hashlib.sha256((payload_text.rstrip("\n") + "\n").encode("utf-8")).hexdigest()


def load_input_contract(repo_root: Path) -> dict[str, Any]:
    return read_json(repo_root / INPUT_CONTRACT_PATH)


def load_record_contract(repo_root: Path) -> dict[str, Any]:
    return read_json(repo_root / RECORD_CONTRACT_PATH)


def load_state_sync_schema(repo_root: Path) -> dict[str, Any]:
    return read_json(repo_root / STATE_SYNC_SCHEMA_PATH)


def validate_contract_alignment(repo_root: Path) -> dict[str, str]:
    input_contract = load_input_contract(repo_root)
    state_schema = load_state_sync_schema(repo_root)
    candidate_entrypoints = state_schema.get("properties", {}).get("candidate_sync_entrypoints", {}).get("properties", {})
    expected = {
        "truth_pack_candidate": candidate_entrypoints.get("truth_pack_candidate_root", {}).get("const"),
        "board_candidate": candidate_entrypoints.get("board_candidate_root", {}).get("const"),
        "current_state_candidate": candidate_entrypoints.get("current_state_candidate_root", {}).get("const"),
    }
    actual = {
        family: details["staging_root"]
        for family, details in input_contract.get("candidate_families", {}).items()
        if family in expected
    }
    if expected != actual:
        raise ValueError(f"State-sync candidate roots are out of alignment: expected={expected!r} actual={actual!r}")
    return actual


def validate_candidate_input(payload: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    contract = load_input_contract(repo_root)
    validate_contract_alignment(repo_root)

    required_fields = contract["required_input_fields"]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise ValueError(f"Missing required input fields: {', '.join(missing)}")

    if payload["schema_version"] != INPUT_SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema_version: {payload['schema_version']}")
    if payload["source_repo"] != contract["accepted_source_repo"]:
        raise ValueError("source_repo does not match the frozen execution-side repo.")
    if payload["source_plane"] != contract["accepted_source_plane"]:
        raise ValueError("source_plane does not match the frozen execution-side plane.")

    family = payload["candidate_family"]
    family_contract = contract["candidate_families"].get(family)
    if family_contract is None:
        if family in contract.get("manual_only_families", {}):
            raise ValueError(f"{family} remains manual-only and is excluded from automated ingest.")
        raise ValueError(f"Unsupported candidate_family: {family}")

    candidate_id = str(payload["candidate_id"]).strip()
    if not FILENAME_SAFE_RE.match(candidate_id):
        raise ValueError("candidate_id must be filename-safe and use only letters, numbers, dot, underscore, and dash.")

    parse_iso8601(str(payload["candidate_created_at_utc"]))

    source_job = payload["source_job"]
    if not isinstance(source_job, dict):
        raise ValueError("source_job must be an object.")
    if not str(source_job.get("job_id", "")).strip():
        raise ValueError("source_job.job_id is required.")
    if "run_id" in source_job and not str(source_job["run_id"]).strip():
        raise ValueError("source_job.run_id may not be blank when present.")

    review_flags = payload["review_flags"]
    if not isinstance(review_flags, dict):
        raise ValueError("review_flags must be an object.")
    for flag_name, expected_value in contract["required_review_flags"].items():
        if review_flags.get(flag_name) != expected_value:
            raise ValueError(f"review_flags.{flag_name} must be {expected_value!r}.")

    content_format = payload["content_format"]
    allowed_formats = family_contract["allowed_content_formats"]
    if content_format not in allowed_formats:
        raise ValueError(f"content_format {content_format!r} is not allowed for {family}.")

    payload_json = payload.get("candidate_payload_json")
    payload_text = payload.get("candidate_payload_text")
    if content_format == "json":
        if payload_json is None:
            raise ValueError("candidate_payload_json is required for json content.")
        if payload_text is not None:
            raise ValueError("candidate_payload_text must be omitted for json content.")
    else:
        if not isinstance(payload_text, str) or not payload_text.strip():
            raise ValueError("candidate_payload_text is required for csv/markdown content.")
        if payload_json is not None:
            raise ValueError("candidate_payload_json must be omitted for text content.")

    summary_lines = payload.get("summary_lines", [])
    if not isinstance(summary_lines, list) or any(not isinstance(item, str) or not item.strip() for item in summary_lines):
        raise ValueError("summary_lines must be a list of non-empty strings.")

    provenance_refs = payload["provenance_refs"]
    if not isinstance(provenance_refs, list) or not provenance_refs:
        raise ValueError("provenance_refs must be a non-empty list.")
    for ref in provenance_refs:
        if not isinstance(ref, dict):
            raise ValueError("Each provenance ref must be an object.")
        ref_kind = ref.get("ref_kind")
        ref_path = ref.get("ref_path")
        if ref_kind not in contract["allowed_provenance_ref_kinds"]:
            raise ValueError(f"Unsupported provenance ref_kind: {ref_kind}")
        normalized_path = normalize_relpath(str(ref_path))
        for forbidden_prefix in contract["forbidden_provenance_prefixes"]:
            if normalized_path.startswith(forbidden_prefix):
                raise ValueError(f"Forbidden provenance ref_path: {normalized_path}")
        allowed_prefixes = tuple(contract["allowed_provenance_ref_kinds"][ref_kind]["allowed_prefixes"])
        if not normalized_path.startswith(allowed_prefixes):
            raise ValueError(f"ref_path {normalized_path!r} is not allowed for ref_kind {ref_kind!r}.")
        ref["ref_path"] = normalized_path

    return {
        "contract": contract,
        "family_contract": family_contract,
        "candidate_id": candidate_id,
        "content_format": content_format,
        "payload_json": payload_json,
        "payload_text": payload_text,
        "summary_lines": summary_lines,
    }


def build_ingest_plan(
    payload: dict[str, Any],
    repo_root: Path,
    *,
    destination_root: Path | None = None,
) -> dict[str, Any]:
    validated = validate_candidate_input(payload, repo_root)
    record_contract = load_record_contract(repo_root)

    family_contract = validated["family_contract"]
    content_format = validated["content_format"]
    candidate_id = validated["candidate_id"]
    destination_root = (destination_root or repo_root).resolve()
    staging_root = destination_root / Path(family_contract["staging_root"])
    payload_extension = family_contract["payload_extension_by_format"][content_format]
    record_path = staging_root / f"{candidate_id}.candidate.json"
    materialized_payload_path = staging_root / f"{candidate_id}{payload_extension}"

    payload_sha256 = sha256_for_payload(content_format, validated["payload_json"], validated["payload_text"])
    record = {
        "schema_version": record_contract["record_schema_version"],
        "candidate_family": payload["candidate_family"],
        "candidate_id": candidate_id,
        "candidate_created_at_utc": payload["candidate_created_at_utc"],
        "source_repo": payload["source_repo"],
        "source_plane": payload["source_plane"],
        "source_job": payload["source_job"],
        "content_format": content_format,
        "staging_root": family_contract["staging_root"],
        "active_hosts_unchanged": family_contract.get("active_hosts", [family_contract.get("active_host")]),
        "record_path": relpath_str(record_path, destination_root),
        "materialized_payload_path": relpath_str(materialized_payload_path, destination_root),
        "payload_sha256": payload_sha256,
        "provenance_refs": payload["provenance_refs"],
        "review_flags": payload["review_flags"],
        "summary_lines": validated["summary_lines"],
    }

    missing_record_fields = [field for field in record_contract["required_record_fields"] if field not in record]
    if missing_record_fields:
        raise ValueError(f"Generated candidate record is missing fields: {', '.join(missing_record_fields)}")

    return {
        "record": record,
        "record_path": record_path,
        "payload_path": materialized_payload_path,
        "payload_json": validated["payload_json"],
        "payload_text": validated["payload_text"],
        "content_format": content_format,
    }


def materialize_candidate(plan: dict[str, Any]) -> None:
    record_path: Path = plan["record_path"]
    payload_path: Path = plan["payload_path"]
    if plan["content_format"] == "json":
        write_json(payload_path, plan["payload_json"])
    else:
        write_text(payload_path, plan["payload_text"])
    write_json(record_path, plan["record"])


def cli() -> int:
    parser = argparse.ArgumentParser(description="Import a deterministic candidate truth object into bzclaw-side staging roots.")
    parser.add_argument("--input", required=True, help="Path to a candidate input JSON file.")
    parser.add_argument("--repo-root", help="Optional explicit repo root. Defaults to git top-level discovery.")
    parser.add_argument("--validate-only", action="store_true", help="Validate and print the import plan without writing files.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else find_repo_root(Path(__file__).resolve())
    payload = read_json(Path(args.input).resolve())
    plan = build_ingest_plan(payload, repo_root)
    if not args.validate_only:
        materialize_candidate(plan)

    result = {
        "status": "PASS",
        "repo_root": repo_root.as_posix(),
        "validate_only": args.validate_only,
        "candidate_family": plan["record"]["candidate_family"],
        "candidate_id": plan["record"]["candidate_id"],
        "record_path": relpath_str(plan["record_path"], repo_root),
        "payload_path": relpath_str(plan["payload_path"], repo_root),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
