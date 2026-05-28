"""Deterministic DAG validator for the prerequisite layer.

`is-a` and `part-of` edges are not subject to the cycle check — they are
typed taxonomy and composition relations, and an `is-a` cycle, while
weird, would not corrupt the prerequisite ordering. Only `prerequisite`
edges are checked here.

The validator does not modify anything. It returns a verdict plus, on
failure, the exact cycle path so arbitration can route the offending
edge(s) to review.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from common import read_jsonl


@dataclass
class ValidationResult:
    ok: bool
    n_edges_checked: int
    n_nodes: int
    cycle: list[str]   # node-id path; empty if ok

    def summary(self) -> str:
        if self.ok:
            return (f"DAG ok: {self.n_edges_checked} prerequisite edges, "
                    f"{self.n_nodes} nodes")
        return f"DAG FAIL: cycle {' -> '.join(self.cycle)}"


def validate(edges: Iterable[dict]) -> ValidationResult:
    """Check that the prerequisite subgraph of `edges` is acyclic.

    Edges with `type` other than "prerequisite" are ignored here.
    """
    adj: dict[str, list[str]] = defaultdict(list)
    nodes: set[str] = set()
    n_checked = 0
    for e in edges:
        if e.get("type") != "prerequisite":
            continue
        f, t = e["from"], e["to"]
        adj[f].append(t)
        nodes.add(f)
        nodes.add(t)
        n_checked += 1

    # Iterative DFS with colour marks. White = unseen, grey = on current
    # stack, black = finished. A grey hit on the current path is a cycle.
    WHITE, GREY, BLACK = 0, 1, 2
    colour: dict[str, int] = {n: WHITE for n in nodes}
    parent: dict[str, str | None] = {}

    for start in nodes:
        if colour[start] != WHITE:
            continue
        # (node, iterator over its remaining neighbours)
        stack: list[tuple[str, iter]] = [(start, iter(adj[start]))]
        colour[start] = GREY
        parent[start] = None
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                colour[node] = BLACK
                stack.pop()
                continue
            if colour.get(nxt, WHITE) == GREY:
                # Reconstruct cycle: walk parent chain from `node` until
                # we hit `nxt`, then close the loop.
                path = [nxt]
                cur = node
                while cur is not None and cur != nxt:
                    path.append(cur)
                    cur = parent.get(cur)
                path.append(nxt)
                path.reverse()
                return ValidationResult(False, n_checked, len(nodes), path)
            if colour.get(nxt, WHITE) == WHITE:
                colour[nxt] = GREY
                parent[nxt] = node
                stack.append((nxt, iter(adj[nxt])))

    return ValidationResult(True, n_checked, len(nodes), [])


def validate_files(paths: list[Path]) -> ValidationResult:
    edges = [e for p in paths for e in read_jsonl(p)]
    return validate(edges)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python -m validator.dag <edges.jsonl> [more.jsonl ...]",
              file=sys.stderr)
        sys.exit(2)
    paths = [Path(a) for a in sys.argv[1:]]
    result = validate_files(paths)
    print(result.summary())
    sys.exit(0 if result.ok else 1)
