from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render an operator-facing context pack and manifest for Ads Phase1."
    )
    parser.add_argument("--input", required=True, help="Path to the context request JSON.")
    parser.add_argument("--output-md", required=True, help="Path to the output markdown file.")
    parser.add_argument(
        "--output-manifest", required=True, help="Path to the output manifest JSON file."
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def bullets(values: list[str]) -> str:
    if not values:
        return "- None"
    return "\n".join(f"- {value}" for value in values)


def render_markdown(payload: dict[str, Any]) -> str:
    date_range = payload.get("date_range", {})
    observations = payload.get("observations", [])
    guardrails = payload.get("guardrails", [])
    actions = payload.get("proposed_actions", [])

    lines = [
        "# Ads Phase1 Context Pack",
        "",
        f"- context_pack_id: `{payload.get('context_pack_id', '')}`",
        f"- marketplace: `{payload.get('marketplace', '')}`",
        f"- account_name: `{payload.get('account_name', '')}`",
        f"- campaign_name: `{payload.get('campaign_name', '')}`",
        f"- ad_group_name: `{payload.get('ad_group_name', '')}`",
        f"- objective: `{payload.get('objective', '')}`",
        f"- date_range: `{date_range.get('start', '')}` to `{date_range.get('end', '')}`",
        "",
        "## Observations",
        "",
        bullets(observations),
        "",
        "## Diagnostic Summary",
        "",
        payload.get("diagnostic_summary", ""),
        "",
        "## Guardrails",
        "",
        bullets(guardrails),
        "",
        "## Proposed Actions",
        "",
        bullets(actions),
        "",
    ]
    return "\n".join(lines)


def build_manifest(
    payload: dict[str, Any],
    input_path: Path,
    markdown_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    return {
        "context_pack_id": payload.get("context_pack_id", ""),
        "input_path": str(input_path),
        "output_markdown_path": str(markdown_path),
        "output_manifest_path": str(manifest_path),
        "marketplace": payload.get("marketplace", ""),
        "campaign_name": payload.get("campaign_name", ""),
        "ad_group_name": payload.get("ad_group_name", ""),
        "observation_count": len(payload.get("observations", [])),
        "guardrail_count": len(payload.get("guardrails", [])),
        "proposed_action_count": len(payload.get("proposed_actions", [])),
        "supporting_only": True,
        "runtime_open_claim": False,
        "auto_upload": False,
        "requires_approval": True,
    }


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_md_path = Path(args.output_md)
    output_manifest_path = Path(args.output_manifest)

    payload = load_json(input_path)
    markdown = render_markdown(payload)
    manifest = build_manifest(payload, input_path, output_md_path, output_manifest_path)

    write_text(output_md_path, markdown)
    write_json(output_manifest_path, manifest)


if __name__ == "__main__":
    main()
