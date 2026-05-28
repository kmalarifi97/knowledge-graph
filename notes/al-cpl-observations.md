# AL-CPL calibration notes

Reference photo only. Not imported, not merged. These notes calibrate node grain
and edge shape for our own graph; nothing below crosses into `registry/` or
`candidates/`.

## Source
- Repo: `harrylclc/AL-CPL-dataset`
- Files inspected: `data/physics.preqs`, `data/precalculus.preqs`
- Format: each line is `concept_a,concept_b` meaning **b is a prerequisite of a**.
  Underscores stand in for spaces; parenthesized disambiguators mirror Wikipedia.

## Grain (what nodes look like)
Concepts sit at roughly Wikipedia-article granularity. Examples lifted verbatim:

- Physics: `Newton's_laws_of_motion`, `Acceleration`, `Work_(physics)`,
  `Normal_force`, `Projectile_motion`, `Electric_potential_energy`,
  `Equations_of_motion`, `Frame_of_reference`.
- Precalculus: `Differential_equation`, `Exponentiation`, `Cartesian_coordinate_system`,
  `Binomial_coefficient`, `Unit_circle`, `Domain_of_a_function`, `Asymptote`.

This matches our concept-level grain target (Bernoulli's principle, partial
derivatives, redox reactions). We adopt the same level.

## Edge shape
Directed and pairwise. No edge types beyond prerequisite in this corpus
— `is-a` and `part-of` are not represented. We keep ours typed separately.

Examples worth keeping in mind:
- `Work_(physics),Force` — clean concept→concept dependency. This is the kind
  of forced edge our `logical` source should produce.
- `Acceleration,Position_(vector)` — non-obvious to a layperson but inherent
  (acceleration is the second time-derivative of position).
- `Normal_force,Force` — borderline `is-a` masquerading as prerequisite.
  We would split this: `Normal_force is-a Force`, not a prerequisite edge.

## Anti-patterns to avoid
AL-CPL is noisy. Rows we will **not** mimic:

- `Photoelectric_effect,Physics` — concept→whole subject. Curriculum-shaped.
- `Sine,Geometry` — same shape. Calls a concept a prerequisite of its parent
  field. That's a taxonomic relation at best, and our `is-a` edge belongs
  pointed the other way (sine is-a geometric function, not geometry).
- `Plasticity_(physics),Physics`, `Elasticity_(physics),Physics`,
  `Doppler_effect,Physics` — same pattern, repeatedly.

These leak the very curriculum framing the spec forbids. Our graph treats
"Physics" as out-of-scope as a node entirely; the domain field on each node
carries that information without needing edges.

## What this calibration changes in our build
1. Adopt Wikipedia-article grain.
2. Anchor every node to a Wikidata QID — the AL-CPL surface form (article
   title) is exactly what Wikidata stably identifies.
3. Refuse `concept → subject` edges; they get rejected at the logical source
   and would land in `review.jsonl` if proposed by the LLM source.
4. Keep `is-a` and `part-of` strictly separate from `prerequisite`.
   AL-CPL's collapsing of all three is the failure mode we are explicitly
   designed against.

## Setting it aside
That's the whole use of AL-CPL for this project. No rows are imported. No QIDs
are inherited. The dataset informs the output spec and exits the loop here.
