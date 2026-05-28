from arbitration.arbitrate import arbitrate


def _edge(f, t, source, reliability, ty="prerequisite", rationale="r"):
    return {
        "from": f, "to": t, "type": ty,
        "source": source, "reliability": reliability,
        "rationale": rationale, "endpoints_resolved": True,
    }


def test_merge_same_edge_across_sources():
    edges = [
        _edge("A", "B", "logical", 0.95),
        _edge("A", "B", "llm", 0.45),
    ]
    accepted, review = arbitrate(edges)
    assert len(accepted) == 1
    e = accepted[0]
    assert e["confidence"] == 0.95
    assert e["provenance"] == ["llm", "logical"]
    assert len(e["rationales"]) == 2
    assert review == []


def test_low_confidence_goes_to_review():
    edges = [_edge("A", "B", "llm", 0.45)]
    accepted, review = arbitrate(edges)
    assert accepted == []
    assert len(review) == 1
    assert review[0]["kind"] == "low_confidence"


def test_directional_conflict_routes_both_to_review():
    edges = [
        _edge("A", "B", "logical", 0.95),
        _edge("B", "A", "llm", 0.45),
    ]
    accepted, review = arbitrate(edges)
    kinds = sorted(r["kind"] for r in review)
    assert kinds == ["conflict", "conflict"]
    assert accepted == []


def test_type_conflict_routes_both_to_review():
    edges = [
        _edge("A", "B", "logical", 0.95, ty="is-a"),
        _edge("A", "B", "llm", 0.45, ty="prerequisite"),
    ]
    accepted, review = arbitrate(edges)
    kinds = sorted(r["kind"] for r in review)
    assert kinds == ["type_conflict", "type_conflict"]
    assert accepted == []


def test_cycle_routes_edges_to_review():
    edges = [
        _edge("A", "B", "logical", 0.95),
        _edge("B", "C", "logical", 0.95),
        _edge("C", "A", "logical", 0.95),
    ]
    accepted, review = arbitrate(edges)
    # all three edges participate in the cycle; at least one is removed
    assert any(r["kind"] == "cycle" for r in review)
    # whatever survives must be acyclic
    from validator.dag import validate
    assert validate(accepted).ok


def test_logical_alone_above_threshold_accepted():
    edges = [_edge("A", "B", "logical", 0.95)]
    accepted, review = arbitrate(edges)
    assert len(accepted) == 1
    assert review == []
