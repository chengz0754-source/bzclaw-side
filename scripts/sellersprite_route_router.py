from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from benchmark_chain_common import resolve_context_from_namespace
from keyword_chain_common import ROOT, append_jsonl, ensure_within_repo, iso_now, load_csv_rows, write_json_atomic


DEFAULT_LOG_DIR = ROOT / "logs" / "sellersprite_router"
LATEST_FILE = "latest_route_decision.json"
HISTORY_FILE = "route_decisions.jsonl"

CURRENT_PURPOSE_PATH = ROOT / "inputs" / "selection_run_current" / "01_选品任务路由与目的.csv"
CURRENT_MARKET_DISCOVERY_PATH = ROOT / "inputs" / "selection_run_current" / "01A_市场发现参数.csv"
CURRENT_SEED_INPUT_PATH = ROOT / "inputs" / "selection_run_current" / "01B_产品与竞品种子输入.csv"
CURRENT_SIF_STRATEGY_PATH = ROOT / "inputs" / "selection_run_current" / "02A_SIF补强策略输入.csv"

MARKET_DISCOVERY = "MARKET_DISCOVERY"
PRODUCT_IDEA_VALIDATION = "PRODUCT_IDEA_VALIDATION"
COMPETITOR_REVERSE_MINING = "COMPETITOR_REVERSE_MINING"
SUPPLY_CHAIN_BACKSOLVE = "SUPPLY_CHAIN_BACKSOLVE"

VALID_PURPOSE_TYPES = {
    MARKET_DISCOVERY,
    PRODUCT_IDEA_VALIDATION,
    COMPETITOR_REVERSE_MINING,
    SUPPLY_CHAIN_BACKSOLVE,
}
VALID_STEP3_POLICIES = {"REQUIRED", "OPTIONAL", "SKIP"}
VALID_SIF_POLICIES = {"NONE", "SHORTLIST_ONLY", "REQUIRED"}
VALID_ROUTE_MODES = {"AUTO", "FORCE"}
VALID_INPUT_TYPES = {"KEYWORD", "ASIN", "BRAND", "SELLER", "SUPPLIER_FAMILY"}

PRODUCT_FORM = "PRODUCT_FORM"
MARKET_CATEGORY = "MARKET_CATEGORY"
PRECISE_DEMAND = "PRECISE_DEMAND"

EXACT_PRODUCT_FORM_TERMS = {
    "claw machine",
    "mini claw machine",
    "candy claw machine",
    "bath toy organizer",
}
DEMAND_CONNECTORS = {"for", "with", "without", "under", "over", "mesh", "bag", "desk", "kids", "adult"}
MARKET_MARKERS = {
    "novelty",
    "gag",
    "stress",
    "relief",
    "storage",
    "category",
    "market",
    "supplies",
    "organizers",
}
GENERIC_CATEGORY_TAILS = {"toys", "storage", "decor", "accessories", "supplies"}

PURPOSE_TO_SEQUENCE = {
    MARKET_DISCOVERY: ["STEP3_MARKET", "STEP1_PRODUCT", "STEP4_BENCHMARK", "STEP2_KEYWORD", "STEP7_CANDIDATE_POOL"],
    PRODUCT_IDEA_VALIDATION: ["STEP1_PRODUCT", "STEP4_BENCHMARK", "STEP2_KEYWORD", "STEP3_MARKET", "STEP7_CANDIDATE_POOL"],
    COMPETITOR_REVERSE_MINING: ["STEP4_BENCHMARK", "STEP2_KEYWORD", "STEP1_PRODUCT", "STEP3_MARKET", "STEP7_CANDIDATE_POOL"],
    SUPPLY_CHAIN_BACKSOLVE: ["STEP1_PRODUCT", "STEP4_BENCHMARK", "STEP2_KEYWORD", "STEP3_MARKET", "STEP7_CANDIDATE_POOL"],
}

PURPOSE_PATH_MAPPING = {
    MARKET_DISCOVERY: {
        "seller_sprite_primary_entry": "STEP3_MARKET / Market Research",
        "seller_sprite_supporting_entries": [
            "STEP1_PRODUCT / Product Research",
            "STEP4_BENCHMARK / Competitor Lookup",
            "STEP2_KEYWORD / Keyword Evidence",
        ],
        "step3_required": True,
        "step3_optional_enrichment": False,
        "candidate_projection": "Require broad market pass before product feasibility is promoted.",
    },
    PRODUCT_IDEA_VALIDATION: {
        "seller_sprite_primary_entry": "STEP1_PRODUCT / Product Research",
        "seller_sprite_supporting_entries": [
            "STEP4_BENCHMARK / Competitor Lookup",
            "STEP2_KEYWORD / Keyword Evidence",
            "STEP3_MARKET / Broad Market Mapping",
        ],
        "step3_required": False,
        "step3_optional_enrichment": True,
        "candidate_projection": "Allow real-product feasibility to continue with market-mapping pending boundaries.",
    },
    COMPETITOR_REVERSE_MINING: {
        "seller_sprite_primary_entry": "STEP4_BENCHMARK / Competitor Lookup",
        "seller_sprite_supporting_entries": [
            "STEP2_KEYWORD / Keyword Reverse Check",
            "STEP1_PRODUCT / Product Research",
            "STEP3_MARKET / Broad Market Remap",
        ],
        "step3_required": False,
        "step3_optional_enrichment": True,
        "candidate_projection": "Allow competitor-derived samples to continue while broad market mapping is optional.",
    },
    SUPPLY_CHAIN_BACKSOLVE: {
        "seller_sprite_primary_entry": "STEP1_PRODUCT / Product Research",
        "seller_sprite_supporting_entries": [
            "STEP3_MARKET / Market Discovery",
            "STEP4_BENCHMARK / Competitor Lookup",
            "STEP2_KEYWORD / Keyword Evidence",
        ],
        "step3_required": False,
        "step3_optional_enrichment": True,
        "candidate_projection": "Treat market mapping as conditional enrichment unless the route is explicitly forced to discovery-first.",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route SellerSprite work by business purpose instead of a single universal path.")
    parser.add_argument("--context-row-index", type=int, default=1)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--direction-id", default=None)
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--category-hint", default=None)
    parser.add_argument("--site", default=None)
    parser.add_argument("--task-id", default=None)
    parser.add_argument("--purpose-type", default=None)
    parser.add_argument("--input-type", default=None)
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    return parser.parse_args()


def log_dir_from_namespace(namespace: Any) -> Path:
    raw_path = Path(getattr(namespace, "log_dir", None) or DEFAULT_LOG_DIR).expanduser()
    if not raw_path.is_absolute():
        raw_path = ROOT / raw_path
    return ensure_within_repo(raw_path, "router_log_dir")


def normalize_tokens(keyword: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", str(keyword or "").casefold()) if token]


def classify_keyword(keyword: str) -> tuple[str, list[str], list[str]]:
    normalized_keyword = " ".join(normalize_tokens(keyword))
    tokens = normalize_tokens(keyword)
    reason_codes: list[str] = []
    matched_tokens: list[str] = []

    if normalized_keyword in EXACT_PRODUCT_FORM_TERMS:
        matched_tokens.append(normalized_keyword)
        reason_codes.append("EXACT_PRODUCT_FORM_TERM")
        return PRODUCT_FORM, reason_codes, matched_tokens

    if any(token in DEMAND_CONNECTORS for token in tokens):
        matched_tokens.extend(sorted({token for token in tokens if token in DEMAND_CONNECTORS}))
        reason_codes.append("HAS_DEMAND_CONNECTOR")
        return PRECISE_DEMAND, reason_codes, matched_tokens

    if any(token in MARKET_MARKERS for token in tokens):
        matched_tokens.extend(sorted({token for token in tokens if token in MARKET_MARKERS}))
        reason_codes.append("HAS_MARKET_MARKER")
        return MARKET_CATEGORY, reason_codes, matched_tokens

    if tokens and tokens[-1] in GENERIC_CATEGORY_TAILS and len(tokens) >= 2:
        matched_tokens.append(tokens[-1])
        reason_codes.append("GENERIC_CATEGORY_TAIL")
        return MARKET_CATEGORY, reason_codes, matched_tokens

    if 1 <= len(tokens) <= 4:
        reason_codes.append("DEFAULT_PRODUCT_FORM_WINDOW")
        matched_tokens.extend(tokens)
        return PRODUCT_FORM, reason_codes, matched_tokens

    reason_codes.append("FALLBACK_PRECISE_DEMAND")
    matched_tokens.extend(tokens)
    return PRECISE_DEMAND, reason_codes, matched_tokens


def load_optional_row(path: Path, row_index: int) -> dict[str, str]:
    if row_index <= 0 or not path.exists():
        return {}
    rows = load_csv_rows(path)
    if len(rows) <= row_index:
        return {}
    return {header: rows[row_index][idx] if idx < len(rows[row_index]) else "" for idx, header in enumerate(rows[0])}


def load_optional_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows = load_csv_rows(path)
    if len(rows) < 2:
        return []
    return [
        {header: row[idx] if idx < len(row) else "" for idx, header in enumerate(rows[0])}
        for row in rows[1:]
    ]


def find_by_task_id(path: Path, task_id: str) -> dict[str, str]:
    normalized_task_id = str(task_id or "").strip()
    if not normalized_task_id:
        return {}
    for row in load_optional_rows(path):
        if str(row.get("任务ID", "")).strip() == normalized_task_id:
            return row
    return {}


def normalize_enum(raw_value: str, allowed: set[str], default: str) -> str:
    value = str(raw_value or "").strip().upper()
    return value if value in allowed else default


def default_step3_policy(purpose_type: str) -> str:
    if purpose_type == MARKET_DISCOVERY:
        return "REQUIRED"
    if purpose_type == PRODUCT_IDEA_VALIDATION:
        return "OPTIONAL"
    if purpose_type == COMPETITOR_REVERSE_MINING:
        return "OPTIONAL"
    if purpose_type == SUPPLY_CHAIN_BACKSOLVE:
        return "OPTIONAL"
    return "OPTIONAL"


def default_sif_policy(purpose_type: str) -> str:
    if purpose_type == MARKET_DISCOVERY:
        return "SHORTLIST_ONLY"
    if purpose_type == PRODUCT_IDEA_VALIDATION:
        return "SHORTLIST_ONLY"
    if purpose_type == COMPETITOR_REVERSE_MINING:
        return "SHORTLIST_ONLY"
    if purpose_type == SUPPLY_CHAIN_BACKSOLVE:
        return "SHORTLIST_ONLY"
    return "SHORTLIST_ONLY"


def route_sequence(purpose_type: str) -> list[str]:
    return list(PURPOSE_TO_SEQUENCE.get(purpose_type, PURPOSE_TO_SEQUENCE[PRODUCT_IDEA_VALIDATION]))


def step3_required(purpose_type: str, step3_policy: str) -> bool:
    policy = normalize_enum(step3_policy, VALID_STEP3_POLICIES, default_step3_policy(purpose_type))
    return policy == "REQUIRED"


def step3_optional_enrichment(purpose_type: str, step3_policy: str) -> bool:
    policy = normalize_enum(step3_policy, VALID_STEP3_POLICIES, default_step3_policy(purpose_type))
    return policy == "OPTIONAL"


def seller_sprite_path_mapping(purpose_type: str, step3_policy: str) -> dict[str, Any]:
    base = dict(PURPOSE_PATH_MAPPING.get(purpose_type, PURPOSE_PATH_MAPPING[PRODUCT_IDEA_VALIDATION]))
    base["step3_policy"] = normalize_enum(step3_policy, VALID_STEP3_POLICIES, default_step3_policy(purpose_type))
    base["step3_required"] = step3_required(purpose_type, base["step3_policy"])
    base["step3_optional_enrichment"] = step3_optional_enrichment(purpose_type, base["step3_policy"])
    return base


def infer_purpose_type(
    *,
    keyword: str,
    explicit_purpose_type: str,
    input_type: str,
    seed_asin: str,
    seed_brand: str,
    seed_seller: str,
    supplier_family: str,
) -> tuple[str, list[str], list[str], str]:
    matched_tokens: list[str] = []
    reason_codes: list[str] = []
    normalized_explicit = normalize_enum(explicit_purpose_type, VALID_PURPOSE_TYPES, "")
    normalized_input_type = normalize_enum(input_type, VALID_INPUT_TYPES, "KEYWORD")

    if normalized_explicit:
        reason_codes.append("PURPOSE_TABLE_OVERRIDE")
        if keyword:
            matched_tokens.extend(normalize_tokens(keyword))
        return normalized_explicit, reason_codes, matched_tokens, normalized_input_type

    if supplier_family.strip() or normalized_input_type == "SUPPLIER_FAMILY":
        reason_codes.append("SUPPLIER_FAMILY_INPUT")
        matched_tokens.extend(normalize_tokens(supplier_family or keyword))
        return SUPPLY_CHAIN_BACKSOLVE, reason_codes, matched_tokens, "SUPPLIER_FAMILY"

    if seed_asin.strip() or seed_brand.strip() or seed_seller.strip() or normalized_input_type in {"ASIN", "BRAND", "SELLER"}:
        reason_codes.append("COMPETITOR_SEED_INPUT")
        matched_tokens.extend([value for value in [seed_asin.strip(), seed_brand.strip(), seed_seller.strip()] if value])
        return COMPETITOR_REVERSE_MINING, reason_codes, matched_tokens, normalized_input_type if normalized_input_type != "KEYWORD" else "ASIN"

    legacy_route_type, legacy_reasons, legacy_tokens = classify_keyword(keyword)
    reason_codes.extend(legacy_reasons)
    matched_tokens.extend(legacy_tokens)
    if legacy_route_type == MARKET_CATEGORY:
        return MARKET_DISCOVERY, reason_codes, matched_tokens, normalized_input_type
    return PRODUCT_IDEA_VALIDATION, reason_codes, matched_tokens, normalized_input_type


def resolve_route_decision(
    *,
    context_row_index: int = 1,
    run_name: str = "",
    direction_id: str = "",
    keyword: str = "",
    site: str = "",
    purpose_type_override: str = "",
    input_type_override: str = "",
    task_id_override: str = "",
) -> dict[str, Any]:
    route_row = load_optional_row(CURRENT_PURPOSE_PATH, context_row_index)
    task_id = str(task_id_override or route_row.get("任务ID", "")).strip()
    market_row = find_by_task_id(CURRENT_MARKET_DISCOVERY_PATH, task_id)
    seed_row = find_by_task_id(CURRENT_SEED_INPUT_PATH, task_id)
    sif_row = find_by_task_id(CURRENT_SIF_STRATEGY_PATH, task_id)

    effective_keyword = str(
        keyword
        or route_row.get("input_value")
        or route_row.get("product_idea_term")
        or route_row.get("broad_market_term")
        or route_row.get("任务名称")
    ).strip()
    effective_site = str(site or route_row.get("site")).strip().upper()
    effective_run_name = str(run_name or route_row.get("任务名称") or route_row.get("任务ID")).strip()
    effective_direction_id = str(direction_id or route_row.get("任务ID")).strip()
    explicit_purpose_type = str(purpose_type_override or route_row.get("purpose_type")).strip()
    input_type = str(input_type_override or route_row.get("input_type")).strip()
    seed_asin = str(route_row.get("seed_asin") or seed_row.get("种子ASIN")).strip()
    seed_brand = str(route_row.get("seed_brand") or seed_row.get("品牌")).strip()
    seed_seller = str(route_row.get("seed_seller") or seed_row.get("卖家")).strip()
    supplier_family = str(route_row.get("supplier_family") or seed_row.get("供应链簇")).strip()

    purpose_type, rule_hits, matched_tokens, normalized_input_type = infer_purpose_type(
        keyword=effective_keyword,
        explicit_purpose_type=explicit_purpose_type,
        input_type=input_type,
        seed_asin=seed_asin,
        seed_brand=seed_brand,
        seed_seller=seed_seller,
        supplier_family=supplier_family,
    )
    route_mode = normalize_enum(str(route_row.get("route_mode", "")), VALID_ROUTE_MODES, "AUTO")
    step3_policy = normalize_enum(str(route_row.get("step3_policy", "")), VALID_STEP3_POLICIES, default_step3_policy(purpose_type))
    sif_policy = normalize_enum(str(route_row.get("sif_policy", "")), VALID_SIF_POLICIES, default_sif_policy(purpose_type))
    path_mapping = seller_sprite_path_mapping(purpose_type, step3_policy)

    return {
        "timestamp": iso_now(),
        "module": "sellersprite_route_router",
        "status": "PASS",
        "reason_code": "PASS",
        "purpose_type": purpose_type,
        "route_sequence": route_sequence(purpose_type),
        "step3_policy": step3_policy,
        "step3_required": path_mapping["step3_required"],
        "step3_optional_enrichment": path_mapping["step3_optional_enrichment"],
        "sif_policy": sif_policy,
        "route_mode": route_mode,
        "input_type": normalized_input_type,
        "seller_sprite_primary_entry": path_mapping["seller_sprite_primary_entry"],
        "seller_sprite_supporting_entries": path_mapping["seller_sprite_supporting_entries"],
        "candidate_projection": path_mapping["candidate_projection"],
        "matched_tokens": matched_tokens,
        "rule_hits": rule_hits,
        "任务ID": task_id,
        "任务名称": str(route_row.get("任务名称", "")).strip(),
        "运行名称": effective_run_name,
        "方向ID": effective_direction_id,
        "方向词": effective_keyword,
        "站点": effective_site,
        "broad_market_term": str(route_row.get("broad_market_term") or market_row.get("市场词")).strip(),
        "product_idea_term": str(route_row.get("product_idea_term") or seed_row.get("产品想法词")).strip(),
        "seed_asin": seed_asin,
        "seed_brand": seed_brand,
        "seed_seller": seed_seller,
        "supplier_family": supplier_family,
        "context_row_index": context_row_index,
        "consumed_contract_files": {
            "route_table": str(CURRENT_PURPOSE_PATH if CURRENT_PURPOSE_PATH.exists() else ""),
            "market_discovery_table": str(CURRENT_MARKET_DISCOVERY_PATH if CURRENT_MARKET_DISCOVERY_PATH.exists() else ""),
            "product_seed_table": str(CURRENT_SEED_INPUT_PATH if CURRENT_SEED_INPUT_PATH.exists() else ""),
            "sif_strategy_table": str(CURRENT_SIF_STRATEGY_PATH if CURRENT_SIF_STRATEGY_PATH.exists() else ""),
        },
    }


def persist_route(log_dir: Path, payload: dict[str, Any]) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(log_dir / LATEST_FILE, payload)
    append_jsonl(log_dir / HISTORY_FILE, payload)


def main() -> int:
    args = parse_args()
    context = resolve_context_from_namespace(args, require_direction_id=False)
    payload = resolve_route_decision(
        context_row_index=context.context_row_index,
        run_name=context.run_name,
        direction_id=context.direction_id,
        keyword=str(args.keyword or context.keyword or "").strip(),
        site=str(args.site or context.site or "").strip(),
        purpose_type_override=str(args.purpose_type or "").strip(),
        input_type_override=str(args.input_type or "").strip(),
        task_id_override=str(args.task_id or "").strip(),
    )
    payload["context_source"] = context.context_source
    payload["category_hint"] = context.category_hint
    log_dir = log_dir_from_namespace(args)
    persist_route(log_dir, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
