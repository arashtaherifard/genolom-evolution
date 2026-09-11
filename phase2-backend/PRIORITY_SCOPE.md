# Phase 2 Priority Scope and Structural Operators - through Milestone 6

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

M6 implements only the structural behavior supported by the proposal plus explicitly documented V1 operationalizations. Binary Fusion uses the proposal's Table-2 DNA representation and named AND/OR/XOR/NAND operators; invalid one-hot DNA is rejected rather than repaired. The proposal does not provide a sufficient general inverse for Defusion, so Defusion V1 is restricted to Fusion-derived objects with stored parent provenance. Composition/Decomposition are deterministic and do not rewrite content.

A real Fusion/Defusion content realizer is intentionally deferred to M5B. Likewise, learningResourceType mutation/crossover behavior is only used where Appendix B provides an explicit rule. Unsupported source types are not given invented transitions.

## Coverage interpretation

The proposal defines Coverage Span as a **generation-level** ontology variable. Milestone 2 therefore implements it at population/generation level, not per individual. V1 counts resolved CSO keyword nodes directly covered by at least one alive LO, divided by the reference CSO slice rooted at `computer science`.

Because the proposal does not provide a mathematical rule for whether a keyword should additionally cover descendants/subtrees, V1 does not silently invent subtree coverage. That policy remains replaceable through the ontology/evaluation abstraction if the instructor specifies a different interpretation.
