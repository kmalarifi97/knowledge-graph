from validator.dag import validate


def _e(f, t, ty="prerequisite"):
    return {"from": f, "to": t, "type": ty}


def test_acyclic_passes():
    edges = [_e("A", "B"), _e("B", "C"), _e("A", "C")]
    r = validate(edges)
    assert r.ok
    assert r.n_edges_checked == 3
    assert r.cycle == []


def test_cycle_detected():
    edges = [_e("A", "B"), _e("B", "C"), _e("C", "A")]
    r = validate(edges)
    assert not r.ok
    # cycle path should start and end with the same node
    assert r.cycle[0] == r.cycle[-1]
    assert set(r.cycle) == {"A", "B", "C"}


def test_self_loop_detected():
    edges = [_e("A", "A")]
    r = validate(edges)
    assert not r.ok
    assert r.cycle[0] == r.cycle[-1] == "A"


def test_isa_edges_do_not_create_cycles():
    # prerequisite chain A->B->C is fine; an is-a from C back to A
    # is taxonomically odd but the DAG check ignores non-prerequisite
    # edges, so it must not flag.
    edges = [_e("A", "B"), _e("B", "C"), _e("C", "A", ty="is-a")]
    r = validate(edges)
    assert r.ok
