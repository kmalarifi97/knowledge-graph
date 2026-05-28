"""Canonical concept registry.

Deterministic. No LLM calls live here — this is the part of the system the
agent does NOT grade its own homework on. Every concept gets one stable ID
(the Wikidata QID) and one canonical label. Aliases collapse to the same
node so two source extractors using different surface forms cannot produce
duplicate nodes.

The file format is JSONL, append-friendly and diffable under git. One node
per line, sorted-key JSON:

    {"id":"Q11197","label":"Derivative","domain":"mathematics",
     "anchor":{"source":"wikidata","qid":"Q11197","verified":true},
     "aliases":["Differentiation"]}

`anchor.verified` reflects whether a human (or future deterministic sync
against Wikidata) has confirmed the QID. Unverified QIDs are still used as
IDs — they are our best current guess and stable for this run — but the
flag is preserved so downstream review can target them.

A concept the agent cannot anchor at all is NOT written here; it goes to
`review.jsonl` as a node-registration-needed entry instead.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from common import REGISTRY_PATH, read_jsonl


@dataclass(frozen=True)
class Anchor:
    source: str          # "wikidata"
    qid: str             # "Q11197"
    verified: bool       # human/sync-confirmed


@dataclass(frozen=True)
class Node:
    id: str              # equals anchor.qid for now
    label: str           # canonical surface form
    domain: str          # "mathematics" | "physics" | "chemistry"
    anchor: Anchor
    aliases: tuple[str, ...] = field(default_factory=tuple)

    def all_names(self) -> tuple[str, ...]:
        return (self.label, *self.aliases)


class Registry:
    """In-memory view of nodes.jsonl with id and alias lookup."""

    def __init__(self, path: Path = REGISTRY_PATH):
        self.path = path
        self._by_id: dict[str, Node] = {}
        self._by_name: dict[str, Node] = {}   # lowercased label/alias → node
        self._load()

    def _load(self) -> None:
        for raw in read_jsonl(self.path):
            node = Node(
                id=raw["id"],
                label=raw["label"],
                domain=raw["domain"],
                anchor=Anchor(**raw["anchor"]),
                aliases=tuple(raw.get("aliases", [])),
            )
            self._index(node)

    def _index(self, node: Node) -> None:
        if node.id in self._by_id:
            existing = self._by_id[node.id]
            if existing != node:
                raise ValueError(
                    f"Registry conflict on {node.id}: {existing!r} vs {node!r}"
                )
            return
        self._by_id[node.id] = node
        for name in node.all_names():
            key = name.lower()
            if key in self._by_name and self._by_name[key].id != node.id:
                raise ValueError(
                    f"Alias collision: {name!r} maps to both "
                    f"{self._by_name[key].id} and {node.id}"
                )
            self._by_name[key] = node

    # --- lookup -----------------------------------------------------------

    def get(self, key: str) -> Optional[Node]:
        """Resolve by QID or by label/alias (case-insensitive)."""
        if key in self._by_id:
            return self._by_id[key]
        return self._by_name.get(key.lower())

    def require(self, key: str) -> Node:
        node = self.get(key)
        if node is None:
            raise KeyError(f"Unregistered concept: {key!r}")
        return node

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def __iter__(self) -> Iterable[Node]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)


def _summarize(reg: Registry) -> None:
    by_domain: dict[str, int] = {}
    unverified: list[Node] = []
    for node in reg:
        by_domain[node.domain] = by_domain.get(node.domain, 0) + 1
        if not node.anchor.verified:
            unverified.append(node)
    print(f"registry: {len(reg)} nodes from {reg.path}")
    for d in sorted(by_domain):
        print(f"  {d}: {by_domain[d]}")
    if unverified:
        print(f"  unverified anchors: {len(unverified)}")
        for n in unverified:
            print(f"    {n.id}  {n.label}")


if __name__ == "__main__":
    # `python -m registry.registry --sync` for now just loads + summarizes.
    # A future deterministic sync would hit Wikidata to flip verified flags;
    # that is out of scope for the vertical slice.
    reg = Registry()
    _summarize(reg)
    if "--strict" in sys.argv:
        unverified = [n for n in reg if not n.anchor.verified]
        if unverified:
            print(f"FAIL: {len(unverified)} unverified anchors under --strict",
                  file=sys.stderr)
            sys.exit(1)
