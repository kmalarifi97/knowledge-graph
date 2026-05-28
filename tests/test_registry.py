import json
from pathlib import Path

from registry.registry import Registry


def _write(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "nodes.jsonl"
    with p.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return p


def _node(qid: str, label: str, aliases=()):
    return {
        "id": qid, "label": label, "domain": "mathematics",
        "anchor": {"source": "wikidata", "qid": qid, "verified": True},
        "aliases": list(aliases),
    }


def test_lookup_by_qid_and_alias(tmp_path):
    p = _write(tmp_path, [_node("Q11197", "Derivative", ["Differentiation"])])
    reg = Registry(p)
    assert reg.get("Q11197").label == "Derivative"
    assert reg.get("Derivative").id == "Q11197"
    assert reg.get("differentiation").id == "Q11197"     # case-insensitive
    assert reg.get("unknown") is None


def test_require_raises_on_unknown(tmp_path):
    p = _write(tmp_path, [_node("Q1", "A")])
    reg = Registry(p)
    try:
        reg.require("ghost")
    except KeyError:
        pass
    else:
        raise AssertionError("require() should raise on unknown key")


def test_alias_collision_rejected(tmp_path):
    # Two different concepts claiming the same alias is a registry bug;
    # construction must refuse rather than silently overwrite.
    p = _write(tmp_path, [
        _node("Q1", "A", ["overlap"]),
        _node("Q2", "B", ["overlap"]),
    ])
    try:
        Registry(p)
    except ValueError:
        pass
    else:
        raise AssertionError("Registry should reject alias collisions")
