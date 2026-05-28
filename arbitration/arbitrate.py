"""Arbitration: per-source candidates -> arbitrated edges + review queue.

Steps:
1. Load every `candidates/*.jsonl` (skipping `*_review.jsonl`; those are
   already destined for review).
2. Group by (from, to, type). Identical edges asserted by multiple
   sources merge into one with combined provenance and confidence = the
   highest reliability among contributing sources.
3. Detect directional conflicts: a `prerequisite` edge A->B asserted by
   one group and B->A asserted by another. Both directions land in
   review with `kind: conflict`.
4. Detect type conflicts: same (from, to) pair asserted with different
   edge types (e.g. one source says `prerequisite`, another `is-a`).
   Both go to review with `kind: type_conflict`.
5. Run the DAG validator on the candidate accepted set. If a cycle
   exists, the offending edges land in review with `kind: cycle`.
6. Threshold split: anything with confidence < 0.70 -> review.
7. Survivors are written to `arbitrated.jsonl`; rejections (with reason)
   to `review.jsonl`.

Nothing here makes content decisions. It only merges, detects, and
routes. The agent does not get a vote at this stage.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from common import ARBITRATION_DIR, CANDIDATES_DIR, read_jsonl, write_jsonl
from validator.dag import validate

THRESHOLD = 0.70
ARBITRATED_PATH = ARBITRATION_DIR / "arbitrated.jsonl"
REVIEW_PATH = ARBITRATION_DIR / "review.jsonl"


def _candidate_files() -> list[Path]:
    """Per-source candidate files only — *_review.jsonl is already routed."""
    if not CANDIDATES_DIR.exists():
        return []
    return sorted(
        p for p in CANDIDATES_DIR.glob("*.jsonl")
        if not p.stem.endswith("_review")
    )


def _load_all() -> list[dict]:
    edges: list[dict] = []
    for path in _candidate_files():
        for e in read_jsonl(path):
            edges.append(e)
    return edges


def _merge_same_key(edges: list[dict]) -> list[dict]:
    """Collapse identical (from, to, type) edges across sources."""
    by_key: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for e in edges:
        by_key[(e["from"], e["to"], e["type"])].append(e)
    merged: list[dict] = []
    for (f, t, ty), group in by_key.items():
        # confidence = max reliability; provenance lists every contributor.
        sources = sorted({e["source"] for e in group})
        confidence = max(e["reliability"] for e in group)
        # Keep all rationales, attributed; downstream consumers can pick.
        rationales = [
            {"source": e["source"], "rationale": e["rationale"]}
            for e in group
        ]
        merged.append({
            "from": f, "to": t, "type": ty,
            "confidence": confidence,
            "provenance": sources,
            "rationales": rationales,
        })
    return merged


def _detect_directional_conflicts(merged: list[dict]) -> tuple[list[dict], list[dict]]:
    """For prerequisite edges only: flag A->B paired with B->A."""
    prereqs = {(m["from"], m["to"]): m for m in merged if m["type"] == "prerequisite"}
    conflict_keys: set[tuple[str, str]] = set()
    for (a, b) in prereqs:
        if (b, a) in prereqs and (b, a) not in conflict_keys:
            conflict_keys.add((a, b))
            conflict_keys.add((b, a))
    kept: list[dict] = []
    review: list[dict] = []
    for m in merged:
        key = (m["from"], m["to"])
        if m["type"] == "prerequisite" and key in conflict_keys:
            review.append({
                "kind": "conflict",
                "reason": "directional conflict: opposite prerequisite asserted by another source",
                "edge": m,
            })
        else:
            kept.append(m)
    return kept, review


def _detect_type_conflicts(merged: list[dict]) -> tuple[list[dict], list[dict]]:
    """Same (from, to) pair asserted with different edge types."""
    by_pair: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for m in merged:
        by_pair[(m["from"], m["to"])].append(m)
    conflict_pairs = {p for p, ms in by_pair.items() if len({m["type"] for m in ms}) > 1}
    kept: list[dict] = []
    review: list[dict] = []
    for m in merged:
        if (m["from"], m["to"]) in conflict_pairs:
            review.append({
                "kind": "type_conflict",
                "reason": "same endpoint pair asserted with different edge types",
                "edge": m,
            })
        else:
            kept.append(m)
    return kept, review


def _validate_dag(merged: list[dict]) -> tuple[list[dict], list[dict]]:
    """Run the DAG validator; if a cycle exists, route the cycle's edges
    to review (kind: cycle) and re-check until clean.

    The validator returns a single cycle path per call; we strip edges
    along that path one at a time until the prerequisite subgraph is
    acyclic. This is simple and correct for the small slice; if cycles
    ever become common we'd want a feedback-arc-set heuristic instead.
    """
    review: list[dict] = []
    current = list(merged)
    while True:
        result = validate(
            {"from": m["from"], "to": m["to"], "type": m["type"]}
            for m in current
        )
        if result.ok:
            return current, review
        cycle_pairs = set(zip(result.cycle, result.cycle[1:]))
        next_current: list[dict] = []
        for m in current:
            if m["type"] == "prerequisite" and (m["from"], m["to"]) in cycle_pairs:
                review.append({
                    "kind": "cycle",
                    "reason": f"edge participates in cycle {' -> '.join(result.cycle)}",
                    "edge": m,
                })
            else:
                next_current.append(m)
        if len(next_current) == len(current):
            # Defensive: should not happen since cycle_pairs comes from
            # the edges themselves. Bail with what we have.
            return next_current, review
        current = next_current


def _threshold_split(merged: list[dict]) -> tuple[list[dict], list[dict]]:
    accepted: list[dict] = []
    review: list[dict] = []
    for m in merged:
        if m["confidence"] >= THRESHOLD:
            accepted.append(m)
        else:
            review.append({
                "kind": "low_confidence",
                "reason": f"confidence {m['confidence']:.2f} below threshold {THRESHOLD:.2f}",
                "edge": m,
            })
    return accepted, review


def arbitrate(edges: list[dict]) -> tuple[list[dict], list[dict]]:
    review: list[dict] = []
    merged = _merge_same_key(edges)
    merged, r = _detect_directional_conflicts(merged); review.extend(r)
    merged, r = _detect_type_conflicts(merged);        review.extend(r)
    merged, r = _validate_dag(merged);                 review.extend(r)
    accepted, r = _threshold_split(merged);            review.extend(r)
    return accepted, review


def main() -> int:
    edges = _load_all()
    accepted, review = arbitrate(edges)
    n_acc = write_jsonl(ARBITRATED_PATH, accepted)
    n_rev = write_jsonl(REVIEW_PATH, review)
    print(f"arbitration: {n_acc} accepted -> {ARBITRATED_PATH}")
    print(f"arbitration: {n_rev} to review -> {REVIEW_PATH}")
    if review:
        # Tally by reason for the operator's sanity.
        from collections import Counter
        kinds = Counter(r["kind"] for r in review)
        for k, v in sorted(kinds.items()):
            print(f"  review/{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
