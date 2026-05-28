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

Vertical slice: **classical mechanics + the calculus it forces**.
Picked to exercise the full pipeline including a cross-domain forced edge
(calculus → dynamics), entity resolution, DAG check, and arbitration
between `logical` and `llm` sources.

The other domains (chemistry, the rest of physics, the rest of math) are
deliberately not seeded yet. Prove the machine before scaling it.

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
