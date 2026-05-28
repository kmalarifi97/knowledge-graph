"""LLM edge source.

Today this reads frozen agent-extracted edges from `llm_seed.yaml`. The
seed yaml is what an LLM extractor over textbook material *would* produce
if we had a corpus wired in; freezing it to disk keeps this pass
reproducible and auditable.

When corpus ingestion lands, the swap is local: replace `_load_seed` with
the real extractor. The downstream contract (one record per line in
`candidates/llm.jsonl`, with `source: "llm"` and `reliability: 0.45`) is
preserved.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

from common import CANDIDATES_DIR, SOURCES_DIR, write_jsonl
from registry.registry import Registry

SEED_PATH = SOURCES_DIR / "llm_seed.yaml"
OUT_PATH = CANDIDATES_DIR / "llm.jsonl"
REVIEW_PATH = CANDIDATES_DIR / "llm_review.jsonl"

# Low because we have no corpus anchor; these are model-knowledge claims
# that arbitration should treat as tentative. The threshold (0.70) routes
# anything that doesn't get reinforced into review.jsonl.
RELIABILITY = 0.45

VALID_TYPES = {"prerequisite", "is-a", "part-of"}


def _load_seed(path: Path) -> list[dict]:
    with path.open() as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a YAML list of edge dicts")
    return data


def extract(seed: list[dict], reg: Registry) -> tuple[list[dict], list[dict]]:
    edges: list[dict] = []
    review: list[dict] = []
    for i, item in enumerate(seed, 1):
        edge_type = item.get("type", "prerequisite")
        if edge_type not in VALID_TYPES:
            review.append({
                "kind": "invalid_type",
                "rule_index": i,
                "rule": item,
                "reason": f"unknown edge type {edge_type!r}",
            })
            continue
        f_node = reg.get(item["from"])
        t_node = reg.get(item["to"])
        missing = [k for k, v in [("from", f_node), ("to", t_node)] if v is None]
        if missing:
            review.append({
                "kind": "unanchored_endpoint",
                "rule_index": i,
                "rule": item,
                "missing": missing,
                "reason": "endpoint not in registry; register the node first",
            })
            continue
        edges.append({
            "from": f_node.id,
            "to": t_node.id,
            "type": edge_type,
            "source": "llm",
            "reliability": RELIABILITY,
            "rationale": item["rationale"],
            "endpoints_resolved": True,
        })
    return edges, review


def main() -> int:
    reg = Registry()
    seed = _load_seed(SEED_PATH)
    edges, review = extract(seed, reg)
    n_edges = write_jsonl(OUT_PATH, edges)
    n_review = write_jsonl(REVIEW_PATH, review)
    print(f"llm: {n_edges} edges -> {OUT_PATH}")
    if n_review:
        print(f"llm: {n_review} items to review -> {REVIEW_PATH}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
