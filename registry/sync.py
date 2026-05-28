"""Deterministic Wikidata anchor verifier.

For each registered node whose anchor is `verified: false`, fetch
Wikidata's Special:EntityData and compare the English label + aliases
against ours. On match, flip the flag. Mismatches and 404s are reported
but left flagged for human attention.

This is the deterministic counterpart to the agent's QID guesses: the
agent proposes, this script verifies. No LLM calls, no fuzzy logic
beyond lowercase + parenthetical strip.

Usage (inside container):
    python -m registry.sync           # apply
    python -m registry.sync --dry-run # report only, no writes
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from urllib import error, request

from common import REGISTRY_PATH

USER_AGENT = "knowledge-graph-anchor-sync/0.1 (research)"
ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
POLITE_DELAY_S = 0.15


def _fetch_entity(qid: str) -> dict | None:
    """Return the entity dict for `qid`, or None if 404 / unreachable."""
    url = ENTITY_URL.format(qid=qid)
    req = request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
    except error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    except error.URLError:
        return None
    return data.get("entities", {}).get(qid)


def _english_names(entity: dict) -> list[str]:
    """English label + aliases as a flat list."""
    out: list[str] = []
    label = entity.get("labels", {}).get("en", {}).get("value")
    if label:
        out.append(label)
    for a in entity.get("aliases", {}).get("en", []):
        v = a.get("value")
        if v:
            out.append(v)
    return out


def _normalize(s: str) -> str:
    """Lowercase, strip parenthesized disambiguator, collapse whitespace."""
    s = s.lower().strip()
    s = re.sub(r"\s*\([^)]*\)", "", s)
    return re.sub(r"\s+", " ", s).strip()


def verify_node(node: dict) -> tuple[str, str]:
    """Classify a node. Returns (status, message).

    status ∈ {verified, mismatch, missing, skipped}.
    """
    anchor = node["anchor"]
    if anchor.get("source") != "wikidata":
        return ("skipped", f"non-wikidata anchor (source={anchor.get('source')!r})")
    qid = anchor["qid"]
    if not re.fullmatch(r"Q\d+", qid):
        return ("skipped", f"non-canonical qid {qid!r}")
    entity = _fetch_entity(qid)
    if entity is None:
        return ("missing", f"{qid} returned 404 from Wikidata")
    our = {_normalize(n) for n in [node["label"], *node.get("aliases", [])]}
    theirs = {_normalize(n) for n in _english_names(entity)}
    if our & theirs:
        match = sorted(our & theirs)[0]
        return ("verified", f"matched {match!r}")
    return ("mismatch", f"our={sorted(our)} theirs(top3)={sorted(theirs)[:3]}")


def _read_nodes() -> list[dict]:
    nodes: list[dict] = []
    with REGISTRY_PATH.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            nodes.append(json.loads(line))
    return nodes


def _write_nodes(nodes: list[dict]) -> None:
    with REGISTRY_PATH.open("w") as f:
        for n in nodes:
            f.write(json.dumps(n, sort_keys=True, ensure_ascii=False) + "\n")


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    nodes = _read_nodes()

    counts = {"already": 0, "verified": 0, "mismatch": 0, "missing": 0, "skipped": 0}
    failures: list[dict] = []

    force_all = "--all" in sys.argv
    for node in nodes:
        if node["anchor"].get("verified") and not force_all:
            counts["already"] += 1
            continue
        # Reset verified before recheck under --all, so the result is
        # honest: if Wikidata no longer matches, we want the flag back to
        # false. Without this, --all would only ever upgrade flags.
        if force_all:
            node["anchor"]["verified"] = False
        status, msg = verify_node(node)
        qid = node["anchor"]["qid"]
        label = node["label"]
        if status == "verified":
            node["anchor"]["verified"] = True
            counts["verified"] += 1
            print(f"  OK     {qid:<26} {label}   ({msg})")
        elif status == "missing":
            counts["missing"] += 1
            failures.append({"qid": qid, "label": label, "reason": msg})
            print(f"  404    {qid:<26} {label}")
        elif status == "mismatch":
            counts["mismatch"] += 1
            failures.append({"qid": qid, "label": label, "reason": msg})
            print(f"  MISM   {qid:<26} {label}")
            print(f"         {msg}")
        else:
            counts["skipped"] += 1
            print(f"  SKIP   {qid:<26} {label}   ({msg})")
        time.sleep(POLITE_DELAY_S)

    print()
    print(
        f"sync: already={counts['already']} verified={counts['verified']} "
        f"mismatch={counts['mismatch']} missing={counts['missing']} "
        f"skipped={counts['skipped']}"
    )

    # Under --all we may also need to write to flip a true-back-to-false on
    # a previously-trusted-but-actually-wrong node, so write whenever the
    # set changed at all.
    changed = counts["verified"] or (force_all and (counts["mismatch"] + counts["missing"]))
    if not dry_run and changed:
        _write_nodes(nodes)
        print(f"sync: rewrote {REGISTRY_PATH}")
    elif dry_run:
        print("sync: --dry-run; no writes")

    # Exit non-zero if any anchor in the registry remains unresolved
    # (mismatch or missing). Skipped non-wikidata anchors are allowed.
    return 0 if (counts["mismatch"] + counts["missing"]) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
