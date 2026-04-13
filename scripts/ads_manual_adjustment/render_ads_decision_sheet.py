from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a markdown decision sheet for Ads Phase1 manual review."
    )
    parser.add_argument("--input", required=True, help="Path to the decision payload JSON.")
    parser.add_argument("--output", required=True, help="Path to the output markdown file.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def render_actions(actions: list[dict[str, Any]]) -> str:
    if not actions:
        return "- No actions provided"
    blocks: list[str] = []
    for action in actions:
        blocks.extend(
            [
                f"- action_type: `{action.get('action_type', '')}`",
                f"- scope: `{action.get('scope', '')}`",
                f"- expected_effect: {action.get('expected_effect', '')}",
                f"- guardrail: {action.get('guardrail', '')}",
                "",
            ]
        )
    return "\n".join(blocks).rstrip()


def render_list(values: list[str]) -> str:
    if not values:
        return "- None"
    return "\n".join(f"- {value}" for value in values)


def render_markdown(payload: dict[str, Any]) -> str:
    verification = payload.get("verification_window", {})
    lines = [
        "# Ads Phase1 Decision Sheet",
        "",
        f"- decision_sheet_id: `{payload.get('decision_sheet_id', '')}`",
        f"- linked_problem_card_id: `{payload.get('linked_problem_card_id', '')}`",
        f"- decision_owner: `{payload.get('decision_owner', '')}`",
        f"- approval_owner: `{payload.get('approval_owner', '')}`",
        f"- approval_status: `{payload.get('approval_status', '')}`",
        f"- decision_date: `{payload.get('decision_date', '')}`",
        "",
        "## Objective",
        "",
        payload.get("objective", ""),
        "",
        "## Diagnosis",
        "",
        render_list(payload.get("diagnosis", [])),
        "",
        "## Chosen Actions",
        "",
        render_actions(payload.get("chosen_actions", [])),
        "",
        "## Verification Window",
        "",
        f"- same_session: {verification.get('same_session', '')}",
        f"- plus_24h: {verification.get('plus_24h', '')}",
        f"- plus_72h: {verification.get('plus_72h', '')}",
        "",
        "## Rollback Trigger",
        "",
        payload.get("rollback_trigger", ""),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    payload = load_json(Path(args.input))
    write_text(Path(args.output), render_markdown(payload))


if __name__ == "__main__":
    main()
