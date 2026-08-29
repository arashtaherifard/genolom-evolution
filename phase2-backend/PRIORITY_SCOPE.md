# Phase 2 Priority Scope (Blue Rows) - Milestone 2

This milestone implements the updated task-sheet priority rows first, plus only the non-blue dependencies required to make those rows operational and scientifically testable.

## Priority rows completed in backend

| Task-sheet item | Backend implementation |
|---|---|
| Crossover | `evolution/crossover.py`, `evolution/session.py` |
| Mutation | `evolution/mutation.py`, `evolution/session.py` |
| Selection | `selection/parent_pool.py` + existing selection strategies |
| Abstraction | `content/operators/abstraction.py` |
| Elaboration | `content/operators/elaboration.py` |
| Probing | `content/operators/probing.py` |
| Perish | `evolution/lifecycle.py` |
| Longevity Chance | `evolution/lifecycle.py`, `models/individual.py` |
| Age | `evolution/lifecycle.py`, `models/individual.py` |
| Fusion History | `models/individual.py`, `evolution/fusion_defusion.py` |
| Defusion History | `models/individual.py`, `evolution/fusion_defusion.py` |
| Cohesion | `fitness/cohesion.py` |
| Dependence | `fitness/dependence.py` |
| Coverage Span | `evaluation/coverage.py` |
| Mutation Rules | `evolution/operator_rules.py`, `evolution/mutation.py` |
| Cross Over Rules | `evolution/operator_rules.py`, `evolution/crossover.py` |
| Mutation Rate | `evolution/rates.py` + config |
| Cross Over Rate | `evolution/rates.py` + config |
| Fusion/Defusion Threshold | `evolution/fusion_defusion.py` + config |
| Coverage Threshold | `evaluation/coverage.py` + config |

## Non-blue dependencies implemented now

These are included because the priority rows depend on them:

- **Fitness Function**: Selection requires an individual score before probability mapping. Canonical V1 is weighted Cohesion + Dependence.
- **Maturity Age**: Proposal explicitly gates Crossover (and later Fusion/Defusion/Composition/Decomposition) by minimum age.
- **Coverage Rate**: Proposal defines Coverage Threshold through the number of resources covering ontology nodes; Coverage Rate is therefore computed alongside Coverage Span.
- **Target-genome validation and integrity repair**: Mutation/Crossover cannot be considered complete unless invalid offspring are rejected or repaired under proposal constraints.
- **Offspring creation, events, and lineage**: Required to make genetic operators observable, reproducible, and UI-ready.
- **Generation lifecycle support**: Needed for Age, Longevity Chance, and Perish to have executable meaning.

## Important non-invention rule

Actual **Fusion** and **Defusion genome transformations** are not fabricated in this milestone. Their blue priority variables (history and threshold) are fully represented, gated, serializable, and testable, but the transformation operators depend on later Fusion/Defusion rule definitions and/or matrices. The backend already exposes the state hooks required to add those operators without redesign.

Likewise, learningResourceType mutation/crossover behavior is only used where Appendix B provides an explicit rule. Unsupported source types are conservatively inherited/left unchanged rather than given invented transitions.

## Coverage interpretation

The proposal defines Coverage Span as a **generation-level** ontology variable. Milestone 2 therefore implements it at population/generation level, not per individual. V1 counts resolved CSO keyword nodes directly covered by at least one alive LO, divided by the reference CSO slice rooted at `computer science`.

Because the proposal does not provide a mathematical rule for whether a keyword should additionally cover descendants/subtrees, V1 does not silently invent subtree coverage. That policy remains replaceable through the ontology/evaluation abstraction if the instructor specifies a different interpretation.
