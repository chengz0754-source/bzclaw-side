from __future__ import annotations

import argparse
import codecs
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import import_state_sync_candidate as candidate_ingest  # noqa: E402
from sellersprite_stage_closure_lib import find_repo_root  # noqa: E402


DEFAULT_EXCHANGE_ROOT = Path(r"E:\bzclaw-exchange")
UTF8_BOM = codecs.BOM_UTF8
VERIFICATION_HARNESS_KIND = "a_exchange_verification_result_v1"
PROOF_SCHEMA_VERSION = "bzclaw.side.exchange_state_sync_import_result.v1"


class ExchangeStateSyncError(ValueError):
    """Raised when exchange-driven state-sync ingest must fail closed."""


@dataclass(frozen=True)
class ExchangeStatePaths:
    root: Path
    verification_results_dir: Path
    verification_archive_dir: Path
    verification_quarantine_dir: Path
    state_candidates_dir: Path
    state_candidates_archive_dir: Path
    state_candidates_quarantine_dir: Path
    proof_dir: Path

    @classmethod
    def from_root(cls, root: Path) -> "ExchangeStatePaths":
        resolved = root.resolve()
        return cls(
            root=resolved,
            verification_results_dir=resolved / "verification" / "from_a" / "results",
            verification_archive_dir=resolved / "verification" / "from_a" / "archive",
            verification_quarantine_dir=resolved / "verification" / "from_a" / "quarantine",
            state_candidates_dir=resolved / "state_sync" / "from_b" / "candidates",
            state_candidates_archive_dir=resolved / "state_sync" / "from_b" / "archive",
            state_candidates_quarantine_dir=resolved / "state_sync" / "from_b" / "quarantine",
            proof_dir=resolved / "verification" / "from_b_state",
        )

    def ensure_dirs(self) -> None:
        for path in [
            self.verification_results_dir,
            self.verification_archive_dir,
            self.verification_quarantine_dir,
            self.state_candidates_dir,
            self.state_candidates_archive_dir,
            self.state_candidates_quarantine_dir,
            self.proof_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class VerificationResult:
    source_path: Path
    payload: dict[str, Any]
    verified_at: str
    event_id: str
    packet_id: str
    job_id: str
    receipt_id: str
    downstream_state_sync_allowed: bool
    verification_disposition: str
    lifecycle_after_verification: str
    business_verified: bool


@dataclass(frozen=True)
class CandidateEnvelope:
    source_path: Path
    payload: dict[str, Any]
    candidate_id: str
    candidate_family: str
    event_id: str
    packet_id: str
    job_id: str


@dataclass
class PreflightResult:
    kept_verification_results: list[VerificationResult]
    kept_candidates: list[CandidateEnvelope]
    kept_verification_summaries: list[Path]
    archived: list[dict[str, str]]
    quarantined: list[dict[str, str]]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import exchange-gated B-side state-sync candidates into bzclaw-side staging roots.")
    parser.add_argument("--exchange-root", default=str(DEFAULT_EXCHANGE_ROOT), help="Machine B exchange root. Defaults to E:\\bzclaw-exchange.")
    parser.add_argument("--repo-root", help="Optional explicit repo root. Defaults to git-top-level discovery.")
    parser.add_argument("--packet-id", action="append", default=[], help="Optional packet allowlist for strict one-run intake isolation.")
    parser.add_argument("--preflight-only", action="store_true", help="Run intake cleanup/archive only and print the kept live packet set.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else find_repo_root(Path(__file__).resolve())
    exchange_paths = ExchangeStatePaths.from_root(Path(args.exchange_root).expanduser())
    exchange_paths.ensure_dirs()
    requested_packets = {str(item).strip() for item in args.packet_id if str(item).strip()}

    try:
        preflight = run_exchange_preflight(exchange_paths, repo_root=repo_root, requested_packets=requested_packets)
        if args.preflight_only:
            print(
                json.dumps(
                    {
                        "schema_version": "bzclaw.side.exchange_state_sync_preflight.v1",
                        "status": "PASS",
                        "kept_verification_packets": [item.packet_id for item in preflight.kept_verification_results],
                        "kept_candidate_packets": [item.packet_id for item in preflight.kept_candidates],
                        "archived": preflight.archived,
                        "quarantined": preflight.quarantined,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        proof = process_exchange_state_sync(exchange_paths, repo_root=repo_root, preflight=preflight)
        proof_paths = write_proof_notes(exchange_paths, proof)
        result = {
            "schema_version": PROOF_SCHEMA_VERSION,
            "status": proof["status"],
            "accepted_count": proof["accepted_count"],
            "rejected_count": proof["rejected_count"],
            "proof_json": exchange_relative(exchange_paths, proof_paths["json"]),
            "proof_md": exchange_relative(exchange_paths, proof_paths["md"]),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ExchangeStateSyncError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "schema_version": "bzclaw.side.exchange_state_sync_error.v1",
                    "status": "FAIL",
                    "reason_code": "STATE_SYNC_EXCHANGE_INGEST_FAILED",
                    "message": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1


def run_exchange_preflight(
    exchange_paths: ExchangeStatePaths,
    *,
    repo_root: Path,
    requested_packets: set[str] | None = None,
) -> PreflightResult:
    requested_packets = requested_packets or set()
    archived: list[dict[str, str]] = []
    quarantined: list[dict[str, str]] = []

    valid_candidates: list[CandidateEnvelope] = []
    for path in sorted(exchange_paths.state_candidates_dir.glob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() != ".json":
            archived.append(move_exchange_file(path, exchange_paths.state_candidates_archive_dir, "non_json_state_candidate"))
            continue
        try:
            payload = read_json_object_no_bom(path)
            valid_candidates.append(parse_candidate_envelope(payload, path, repo_root=repo_root))
        except ExchangeStateSyncError as exc:
            quarantined.append(move_exchange_file(path, exchange_paths.state_candidates_quarantine_dir, classify_candidate_error(exc)))

    kept_candidates_by_packet: dict[str, CandidateEnvelope] = {}
    for candidate in valid_candidates:
        if requested_packets and candidate.packet_id not in requested_packets:
            archived.append(move_exchange_file(candidate.source_path, exchange_paths.state_candidates_archive_dir, "stale_nonselected_state_candidate"))
            continue
        previous = kept_candidates_by_packet.get(candidate.packet_id)
        if previous is None:
            kept_candidates_by_packet[candidate.packet_id] = candidate
            continue
        if candidate.source_path.name > previous.source_path.name:
            archived.append(move_exchange_file(previous.source_path, exchange_paths.state_candidates_archive_dir, "duplicate_state_candidate"))
            kept_candidates_by_packet[candidate.packet_id] = candidate
        else:
            archived.append(move_exchange_file(candidate.source_path, exchange_paths.state_candidates_archive_dir, "duplicate_state_candidate"))

    kept_candidates = sorted(kept_candidates_by_packet.values(), key=lambda item: item.source_path.name)
    selected_packets = {item.packet_id for item in kept_candidates}

    valid_verifications: list[VerificationResult] = []
    for path in sorted(exchange_paths.verification_results_dir.glob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".json":
            try:
                payload = read_json_object_no_bom(path)
                valid_verifications.append(parse_verification_result(payload, path))
            except ExchangeStateSyncError as exc:
                quarantined.append(move_exchange_file(path, exchange_paths.verification_quarantine_dir, classify_verification_error(exc)))
            continue
        if suffix == ".md":
            continue
        archived.append(move_exchange_file(path, exchange_paths.verification_archive_dir, "non_json_verification_result"))

    kept_verifications_by_packet: dict[str, VerificationResult] = {}
    for verification in valid_verifications:
        if selected_packets and verification.packet_id not in selected_packets:
            archived.append(move_exchange_file(verification.source_path, exchange_paths.verification_archive_dir, "stale_nonselected_verification_result"))
            continue
        if requested_packets and verification.packet_id not in requested_packets:
            archived.append(move_exchange_file(verification.source_path, exchange_paths.verification_archive_dir, "stale_nonselected_verification_result"))
            continue
        previous = kept_verifications_by_packet.get(verification.packet_id)
        if previous is None:
            kept_verifications_by_packet[verification.packet_id] = verification
            continue
        if verification.source_path.name > previous.source_path.name:
            archived.append(move_exchange_file(previous.source_path, exchange_paths.verification_archive_dir, "duplicate_verification_result"))
            kept_verifications_by_packet[verification.packet_id] = verification
        else:
            archived.append(move_exchange_file(verification.source_path, exchange_paths.verification_archive_dir, "duplicate_verification_result"))

    kept_verifications = sorted(kept_verifications_by_packet.values(), key=lambda item: item.source_path.name)
    kept_packets = {item.packet_id for item in kept_verifications}
    kept_summaries_by_packet: dict[str, Path] = {}
    for path in sorted(exchange_paths.verification_results_dir.glob("*.md")):
        packet_id = verification_summary_packet_id(path)
        if not packet_id:
            archived.append(move_exchange_file(path, exchange_paths.verification_archive_dir, "unrecognized_verification_summary"))
            continue
        if kept_packets and packet_id not in kept_packets:
            archived.append(move_exchange_file(path, exchange_paths.verification_archive_dir, "stale_nonselected_verification_summary"))
            continue
        previous = kept_summaries_by_packet.get(packet_id)
        if previous is None:
            kept_summaries_by_packet[packet_id] = path.resolve()
            continue
        if path.name > previous.name:
            archived.append(move_exchange_file(previous, exchange_paths.verification_archive_dir, "duplicate_verification_summary"))
            kept_summaries_by_packet[packet_id] = path.resolve()
        else:
            archived.append(move_exchange_file(path, exchange_paths.verification_archive_dir, "duplicate_verification_summary"))

    return PreflightResult(
        kept_verification_results=kept_verifications,
        kept_candidates=kept_candidates,
        kept_verification_summaries=sorted(kept_summaries_by_packet.values(), key=lambda item: item.name),
        archived=archived,
        quarantined=quarantined,
    )


def process_exchange_state_sync(
    exchange_paths: ExchangeStatePaths,
    *,
    repo_root: Path,
    preflight: PreflightResult,
    import_destination_root: Path | None = None,
) -> dict[str, Any]:
    destination_root = (import_destination_root or repo_root).resolve()
    verification_by_packet = {item.packet_id: item for item in preflight.kept_verification_results}
    decisions: list[dict[str, Any]] = []
    accepted_count = 0
    rejected_count = 0

    for candidate in preflight.kept_candidates:
        verification = verification_by_packet.get(candidate.packet_id)
        decision = evaluate_candidate_import_decision(candidate, verification)
        if decision["decision"] == "accepted":
            plan = candidate_ingest.build_ingest_plan(candidate.payload, repo_root, destination_root=destination_root)
            candidate_ingest.materialize_candidate(plan)
            decision["record_path"] = relpath_str(plan["record_path"], destination_root)
            decision["payload_path"] = relpath_str(plan["payload_path"], destination_root)
            accepted_count += 1
        else:
            rejected_count += 1
        decisions.append(decision)

    status = "PASS" if accepted_count else "FAIL"
    packet_label = proof_packet_label(decisions)
    return {
        "schema_version": PROOF_SCHEMA_VERSION,
        "generated_at_utc": iso_now_utc(),
        "status": status,
        "proof_label": packet_label,
        "repo_root": repo_root.as_posix(),
        "import_destination_root": destination_root.as_posix(),
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "kept_verification_result_count": len(preflight.kept_verification_results),
        "kept_candidate_count": len(preflight.kept_candidates),
        "preflight": {
            "archived_count": len(preflight.archived),
            "quarantined_count": len(preflight.quarantined),
            "kept_packets": sorted({item.packet_id for item in preflight.kept_candidates}),
        },
        "decisions": decisions,
        "notes": [
            "Only candidate truth objects are imported into staging roots.",
            "Owner writeback remains manual-only.",
            "technical success and receipt visibility do not promote business state.",
        ],
    }


def evaluate_candidate_import_decision(candidate: CandidateEnvelope, verification: VerificationResult | None) -> dict[str, Any]:
    base = {
        "packet_id": candidate.packet_id,
        "event_id": candidate.event_id,
        "job_id": candidate.job_id,
        "candidate_id": candidate.candidate_id,
        "candidate_family": candidate.candidate_family,
        "candidate_source_file": candidate.source_path.as_posix(),
    }
    if verification is None:
        return {
            **base,
            "decision": "rejected",
            "reason_code": "VERIFICATION_GATE_MISSING",
            "verification_result_file": None,
            "verification_disposition": None,
            "downstream_state_sync_allowed": False,
        }

    if verification.event_id != candidate.event_id or verification.job_id != candidate.job_id:
        return {
            **base,
            "decision": "rejected",
            "reason_code": "VERIFICATION_LINKAGE_AMBIGUOUS",
            "verification_result_file": verification.source_path.as_posix(),
            "verification_disposition": verification.verification_disposition,
            "downstream_state_sync_allowed": verification.downstream_state_sync_allowed,
        }

    if verification.downstream_state_sync_allowed is not True:
        return {
            **base,
            "decision": "rejected",
            "reason_code": "DOWNSTREAM_STATE_SYNC_DENIED",
            "verification_result_file": verification.source_path.as_posix(),
            "verification_disposition": verification.verification_disposition,
            "downstream_state_sync_allowed": verification.downstream_state_sync_allowed,
        }

    return {
        **base,
        "decision": "accepted",
        "reason_code": "DOWNSTREAM_STATE_SYNC_ALLOWED",
        "verification_result_file": verification.source_path.as_posix(),
        "verification_disposition": verification.verification_disposition,
        "downstream_state_sync_allowed": verification.downstream_state_sync_allowed,
    }


def parse_verification_result(payload: dict[str, Any], path: Path) -> VerificationResult:
    if str(payload.get("harness_kind", "")).strip() != VERIFICATION_HARNESS_KIND:
        raise ExchangeStateSyncError(f"Unsupported verification harness_kind: {path.name}")
    verification = payload.get("verification")
    if not isinstance(verification, dict):
        raise ExchangeStateSyncError(f"verification object is required: {path.name}")
    required = {
        "verified_at": payload.get("verified_at"),
        "event_id": payload.get("event_id"),
        "packet_id": payload.get("packet_id"),
        "job_id": payload.get("job_id"),
        "verification_disposition": payload.get("verification_disposition"),
        "lifecycle_after_verification": payload.get("lifecycle_after_verification"),
    }
    for label, value in required.items():
        if not str(value or "").strip():
            raise ExchangeStateSyncError(f"Missing verification field {label}: {path.name}")
    if not isinstance(payload.get("downstream_state_sync_allowed"), bool):
        raise ExchangeStateSyncError(f"downstream_state_sync_allowed must be boolean: {path.name}")
    if not isinstance(payload.get("business_verified"), bool):
        raise ExchangeStateSyncError(f"business_verified must be boolean: {path.name}")
    return VerificationResult(
        source_path=path.resolve(),
        payload=payload,
        verified_at=str(payload["verified_at"]).strip(),
        event_id=str(payload["event_id"]).strip(),
        packet_id=str(payload["packet_id"]).strip(),
        job_id=str(payload["job_id"]).strip(),
        receipt_id=str(payload.get("receipt_id", "")).strip(),
        downstream_state_sync_allowed=bool(payload["downstream_state_sync_allowed"]),
        verification_disposition=str(payload["verification_disposition"]).strip(),
        lifecycle_after_verification=str(payload["lifecycle_after_verification"]).strip(),
        business_verified=bool(payload["business_verified"]),
    )


def parse_candidate_envelope(payload: dict[str, Any], path: Path, *, repo_root: Path) -> CandidateEnvelope:
    try:
        candidate_ingest.validate_candidate_input(payload, repo_root)
    except ValueError as exc:
        raise ExchangeStateSyncError(f"Candidate envelope does not satisfy state-sync contract: {path.name}: {exc}") from exc
    source_job = payload.get("source_job", {})
    if not isinstance(source_job, dict):
        raise ExchangeStateSyncError(f"Candidate source_job must be an object: {path.name}")
    event_id = str(source_job.get("event_id") or payload.get("candidate_payload_json", {}).get("event_id") or "").strip()
    packet_id = str(source_job.get("packet_id") or payload.get("candidate_payload_json", {}).get("packet_id") or "").strip()
    job_id = str(source_job.get("job_id") or "").strip()
    if not event_id or not packet_id or not job_id:
        raise ExchangeStateSyncError(f"Candidate envelope must carry source_job event_id, packet_id, and job_id: {path.name}")
    return CandidateEnvelope(
        source_path=path.resolve(),
        payload=payload,
        candidate_id=str(payload["candidate_id"]).strip(),
        candidate_family=str(payload["candidate_family"]).strip(),
        event_id=event_id,
        packet_id=packet_id,
        job_id=job_id,
    )


def write_proof_notes(exchange_paths: ExchangeStatePaths, proof: dict[str, Any]) -> dict[str, Path]:
    label = str(proof["proof_label"]).strip() or "state_sync_batch"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = exchange_paths.proof_dir / f"{timestamp}__state_sync_import__{label}.json"
    md_path = exchange_paths.proof_dir / f"{timestamp}__state_sync_import__{label}.md"
    write_json_utf8(json_path, proof)
    md_path.write_text(build_proof_markdown(proof, json_path), encoding="utf-8")
    return {
        "json": json_path,
        "md": md_path,
    }


def build_proof_markdown(proof: dict[str, Any], json_path: Path) -> str:
    lines = [
        "# B State Exchange Ingest Proof",
        "",
        f"- generated_at_utc: `{proof['generated_at_utc']}`",
        f"- status: `{proof['status']}`",
        f"- accepted_count: `{proof['accepted_count']}`",
        f"- rejected_count: `{proof['rejected_count']}`",
        f"- proof_json: `{json_path.as_posix()}`",
        "",
        "## Decisions",
        "",
    ]
    for decision in proof["decisions"]:
        lines.extend(
            [
                f"- packet_id: `{decision['packet_id']}`",
                f"  decision: `{decision['decision']}`",
                f"  reason_code: `{decision['reason_code']}`",
                f"  candidate_id: `{decision['candidate_id']}`",
                f"  verification_disposition: `{decision.get('verification_disposition')}`",
                f"  record_path: `{decision.get('record_path', 'not_written')}`",
                f"  payload_path: `{decision.get('payload_path', 'not_written')}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- only candidate truth objects were eligible for import",
            "- active truth hosts were not overwritten automatically",
            "- owner_writeback remains manual-only",
            "- downstream sync allowance did not promote business state",
        ]
    )
    return "\n".join(lines) + "\n"


def read_json_object_no_bom(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(UTF8_BOM):
        raise ExchangeStateSyncError(f"UTF-8 BOM is not allowed in exchange JSON: {path.name}")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExchangeStateSyncError(f"Malformed exchange JSON object: {path.name}") from exc
    if not isinstance(payload, dict):
        raise ExchangeStateSyncError(f"Exchange JSON must be an object: {path.name}")
    return payload


def verification_summary_packet_id(path: Path) -> str:
    marker = "__verification_summary__"
    if marker not in path.name:
        return ""
    return path.name.split(marker, 1)[1].rsplit(".", 1)[0]


def classify_candidate_error(exc: ExchangeStateSyncError) -> str:
    message = str(exc).lower()
    if "bom" in message:
        return "bom_tainted_state_candidate"
    if "malformed" in message:
        return "malformed_state_candidate"
    return "nonconforming_state_candidate"


def classify_verification_error(exc: ExchangeStateSyncError) -> str:
    message = str(exc).lower()
    if "bom" in message:
        return "bom_tainted_verification_result"
    if "malformed" in message:
        return "malformed_verification_result"
    return "nonconforming_verification_result"


def move_exchange_file(path: Path, destination_dir: Path, reason_code: str) -> dict[str, str]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}__{reason_code}__{path.name}"
    shutil.move(str(path), str(target))
    return {
        "reason_code": reason_code,
        "source": str(path),
        "destination": str(target),
    }


def write_json_utf8(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def exchange_relative(exchange_paths: ExchangeStatePaths, path: Path) -> str:
    return str(path.resolve().relative_to(exchange_paths.root.resolve())).replace("\\", "/")


def relpath_str(path: Path, base: Path) -> str:
    return str(path.resolve().relative_to(base.resolve())).replace("\\", "/")


def proof_packet_label(decisions: list[dict[str, Any]]) -> str:
    packets = [str(item.get("packet_id", "")).strip() for item in decisions if str(item.get("packet_id", "")).strip()]
    if not packets:
        return "state_sync_batch"
    unique_packets = sorted(dict.fromkeys(packets))
    label = "__".join(unique_packets)
    return label[:120]


def iso_now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
