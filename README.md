# knowledge-graph

A domain-pure science dependency graph (math, physics, chemistry). No CS, no
curriculum ordering — the graph stays valid for any downstream consumer
because it knows about none of them.

## What this is

Nodes are concepts at Wikipedia-article grain (e.g. `Derivative`,
`Newton's second law`, `Conservation of momentum`). Edges are typed:

- `prerequisite` — directed, must form a DAG.
- `is-a` — taxonomy.
- `part-of` — composition.

The three are never collapsed.

## Pipeline

```
sources/  ── candidates/*.jsonl ── arbitration ── arbitrated.jsonl
                                       │            review.jsonl
                                       └─ DAG validator (cycle check)
```

Per-source provenance is physically separated on disk. Arbitration merges
them with confidence, surfaces conflicts, and routes anything below
threshold to human review. The agent proposes; deterministic code verifies.

## Edge contract

Every emitted edge:

```json
{
  "from": "Q11197",
  "to": "Q11465",
  "type": "prerequisite",
  "source": "logical",
  "reliability": 0.95,
  "rationale": "Velocity is the time derivative of position; the concept of derivative is required to define velocity in continuous mechanics.",
  "endpoints_resolved": true
}
```

`from` and `to` are Wikidata QIDs from `registry/nodes.jsonl`. Anything that
cannot resolve to a registered node is **not** emitted as an edge — it is
flagged for node registration first.

## Reliability anchors

| Source      | Weight | Notes                                                 |
|-------------|--------|-------------------------------------------------------|
| `logical`   | 0.95   | Forced by the math itself; auto-accepts.              |
| `empirical` | 0.85   | Inferred from learner data. Dormant this pass.        |
| `llm`       | 0.45   | Model-knowledge proposals, no corpus yet. Escalates.  |

Acceptance threshold: **0.70**. Below threshold → `review.jsonl`.

## Scope of this pass

Two vertical slices:

1. **Classical mechanics + the calculus it forces** — proves the pipeline
   end-to-end on one tract, including cross-domain forced edges
   (math → physics) and the directional-conflict path.
2. **Chemical kinetics + thermochemistry** — proves the machine scales to
   a second domain. Adds chemistry nodes plus a few supporting math/physics
   nodes (Logarithm, Exponential function, Temperature) and exercises two
   new cross-domain forced edges (math → chemistry, physics → chemistry).

The two slices share one registry and one arbitrated graph — chemistry is
not a separate stream. Cross-domain edges flow naturally through
arbitration with no special handling.

Anchor hygiene: every node is verified against Wikidata via
`registry/sync.py`. Run `make sync-all` to re-verify the whole registry
(including previously-trusted seeds) — this exists because the agent's
confident-but-wrong QID assertions were caught by it, not by the original
sync pass.

## Running

Everything runs in Docker. The host needs only Docker + Make.

```bash
make build      # build image
make pipeline   # run all stages end-to-end
make test       # smoke tests
make sh         # shell into the container
```

Outputs land in:

- `registry/nodes.jsonl` — canonical nodes (one per line).
- `candidates/logical.jsonl`, `candidates/llm.jsonl` — per-source proposals.
- `arbitration/arbitrated.jsonl` — accepted, DAG-validated edges.
- `arbitration/review.jsonl` — needs human attention (low confidence,
  conflict, would introduce a cycle, or unresolvable endpoint).

## What this is not

- Not a curriculum.
- Not a course planner.
- Not a CS graph (AL-CPL is consulted once as a grain/shape reference and
  set aside; no rows are imported).
- Not the final authority on its own structure — the DAG validator is.
