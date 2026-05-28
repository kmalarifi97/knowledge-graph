"""Logical edge source: forced dependencies from a curated YAML.

This script is deterministic. The knowledge work — deciding *what* the
forced dependencies are — lives in `logical_rules.yaml`, which a human
(or the agent under review) authors. The script just resolves endpoints
through the registry and emits the candidate JSONL.

Output contract is the project-wide one:

    {"from": "<qid>", "to": "<qid>", "type": "prerequisite|is-a|part-of",
     "source": "logical", "reliability": 0.95,
     "rationale": "...", "endpoints_resolved": true}

If a rule names an endpoint the registry doesn't know, the script emits a
*review* record instead of an edge. Edges where endpoints cannot be
resolved must not enter the candidate stream.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

from common import CANDIDATES_DIR, SOURCES_DIR, write_jsonl
from registry.registry import Registry

RULES_PATH = SOURCES_DIR / "logical_rules.yaml"
OUT_PATH = CANDIDATES_DIR / "logical.jsonl"
REVIEW_PATH = CANDIDATES_DIR / "logical_review.jsonl"

# Logical edges are forced by definition. They get the highest non-empirical
# weight. Empirical (when present) outranks them only because student data
# is harder to fake; structurally the two are peers.
RELIABILITY = 0.95

VALID_TYPES = {"prerequisite", "is-a", "part-of"}


def _load_rules(path: Path) -> list[dict]:
    with path.open() as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a YAML list of rule dicts")
    return data


def extract(rules: list[dict], reg: Registry) -> tuple[list[dict], list[dict]]:
    edges: list[dict] = []
    review: list[dict] = []
    for i, rule in enumerate(rules, 1):
        edge_type = rule.get("type", "prerequisite")
        if edge_type not in VALID_TYPES:
            review.append({
                "kind": "invalid_type",
                "rule_index": i,
                "rule": rule,
                "reason": f"unknown edge type {edge_type!r}",
            })
            continue
        f_node = reg.get(rule["from"])
        t_node = reg.get(rule["to"])
        missing = [k for k, v in [("from", f_node), ("to", t_node)] if v is None]
        if missing:
            review.append({
                "kind": "unanchored_endpoint",
                "rule_index": i,
                "rule": rule,
                "missing": missing,
                "reason": "endpoint not in registry; register the node first",
            })
            continue
        edges.append({
            "from": f_node.id,
            "to": t_node.id,
            "type": edge_type,
            "source": "logical",
            "reliability": RELIABILITY,
            "rationale": rule["rationale"],
            "endpoints_resolved": True,
        })
    return edges, review


def main() -> int:
    reg = Registry()
    rules = _load_rules(RULES_PATH)
    edges, review = extract(rules, reg)
    n_edges = write_jsonl(OUT_PATH, edges)
    n_review = write_jsonl(REVIEW_PATH, review)
    print(f"logical: {n_edges} edges -> {OUT_PATH}")
    if n_review:
        print(f"logical: {n_review} rules to review -> {REVIEW_PATH}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
