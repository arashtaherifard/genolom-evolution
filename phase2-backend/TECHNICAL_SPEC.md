# Frozen Phase 2 Technical Specification - v1.1

## 1. Individual and genome

One Learning Object (LO) is one evolutionary individual. Educational content is separate from its GenoLOM genome. Genetic operators first create a **target genome**; content operators then generate/transform content toward that target.

The 12 GenoLOM fields remain the genome. CSO diagnostics such as `Depth` are derived data, not genes.

Evolutionary state now includes Age, Longevity Chance, reproduction/participation counters, Fusion History, Defusion History, alive/perished state, and content status.

## 2. Generation 0

The strict Phase-1 output is cryptographically frozen as Generation 0 through the dataset manifest and SHA256 checksum.

## 3. Proposal constraints

The backend enforces fixed metadata, Table-3 interactivity constraints, forbidden semantic-density/difficulty combinations, and non-negative learning time.

No missing learningResourceType transition is invented. Appendix-B rules are used only for explicit supported source types.

## 4. Priority individual fitness

Cohesion is the frozen mean inverse pairwise undirected ontology distance.

The task-sheet/proposal term **Dependence** is canonical in Milestone 2. The V1 operational proxy uses strongest same-LO ancestor support in the directed CSO hierarchy. This is explicitly a proxy to be validated later with experts.

Micro Fitness:

`F = wC * Cohesion + wD * Dependence`

Default architecture weights are 0.5/0.5 and are configurable. The previous `coherence` name remains only as a compatibility alias.

## 5. Selection

Selection is distinct from Perish/survival. Parent selection performs:

1. eligibility gating;
2. descending fitness ranking (for observability/UI/reporting);
3. probability mapping;
4. stochastic parent draw.

Main strategy is fitness-proportionate with uniform fallback when all eligible fitnesses are zero. Random selection is retained as a baseline.

## 6. Maturity and eligibility

Maturity Age is implemented now as a required dependency. Proposal-defined mature-only operators include Crossover and later Fusion, Defusion, Composition, and Decomposition. Mutation is not maturity-gated in V1.

Eligibility also checks alive status, genome validity, available fitness, and optional participation limits.

## 7. Mutation

Mutation Rate is an explicit probabilistic gate. Mutation candidates come only from proposal-defined rules:

- learningResourceType transitions from Appendix B where explicit and non-Drop;
- one-step interactivityLevel changes;
- one-step semanticDensity changes;
- one-step difficulty changes.

Only candidates that satisfy target-genome validation are eligible. Unsupported genes/source transitions are not invented.

## 8. Crossover

Crossover Rate is an explicit probabilistic gate. Appendix-D matrices are used for interactivityType, interactivityLevel, semanticDensity, and difficulty.

Crossover rules also include deterministic integrity repair when independently crossed fields would violate Table-3 constraints. Non-specified genes are conservatively inherited from a real parent. `semanticDensity` and `difficulty` remain marked provisional until content generation/re-analysis.

## 9. Content operators

Abstraction, Elaboration, and Probing are provider-independent operators. They build a versioned `GenerationRequest`, call an injected `ContentGenerator`, and require an independent `ContentValidator` before offspring become viable/accepted.

The included deterministic generator/validator are test doubles only and are marked not for scientific use.

## 10. Age, Longevity Chance, and Perish

Age counts survived generations.

Longevity Chance receives a configured initial value. Each successful participation in producing a viable offspring gives one configured reward; an alive LO with no successful participation in a generation receives one configured penalty.

Perish marks/removes an LO when Longevity Chance is at or below the configured threshold (proposal default semantics: zero or below).

Final numeric longevity parameters are intentionally not guessed in the frozen default config.

## 11. Fusion/Defusion History and Threshold

History records are executable state variables. Threshold policy stores lower/upper operation-count bounds and can gate future operations at the upper bound. Actual Fusion/Defusion genome transformation rules are later non-priority work and are not fabricated.

## 12. Coverage

Coverage Span is implemented as a **generation-level** variable according to the proposal. V1 direct-topic coverage is:

`covered reference CSO nodes / total reference CSO nodes`

Coverage Threshold is the minimum number of distinct LOs covering a node. Coverage Rate is implemented as its required dependency:

`reference nodes with resource_count >= threshold / total reference nodes`

The reference CSO slice is rooted at `computer science`. Subtree/descendant expansion is not silently assumed because the proposal does not supply that mathematical rule.

## 13. Reproducibility and lineage

Controlled RNG, stable IDs, target-genome details, operator rate draws, repairs, parent IDs, offspring IDs, content validation events, longevity events, Perish events, and lineage are serializable.

## 14. UI boundary

Core modules have no UI dependency. `service/engine.py` is the stable Phase-3 boundary and supports both pure previews and a stateful priority evolution session.

## 15. Deferred paper studies

Expert metric validation, held-out chapters, multiple books/domains, expert content evaluation, inter-rater reliability, and learner studies remain deferred but their data/service abstractions are preserved.
