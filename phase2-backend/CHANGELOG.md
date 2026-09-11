# Changelog

## 0.6.0 - Structural operators milestone

- Added proposal Table-2 binary DNA schema for Fusion.
- Added AND / OR / XOR / NAND Fusion execution with strict invalid-one-hot rejection.
- Added an explicit Phase-1 ↔ proposal Table-2 compatibility adapter for Fusion DNA: current `Question` maps to Table-2 `Questionnaire`, `Headline` is coarse-grained to `Narrative Text` only at the DNA boundary, and the frozen Generation-0 labels are left unchanged. Fractional `typicalLearningTime` values are minutes in both Phase 1 and the proposal; V1 quantizes them deterministically to the nearest whole proposal minute for the 6-bit DNA field and logs every normalization.
- Added provenance-based V1 Defusion target recovery.
- Added deterministic Composition preserving parent IDs, component order, roles, content and source spans.
- Added deterministic Decomposition for Composition-V1 artifacts with no LLM rewriting.
- Added stateful session and UI-service methods for all four structural operators.
- Kept Fusion/Defusion real content realization deferred to M5B.
- Expanded the full reconstructed M5A+M6 suite to 142 passing tests.

## 0.2.0 - Priority blue-row milestone

- Added canonical Dependence metric and retained Coherence compatibility alias.
- Added generation-level Coverage Span, Coverage Threshold, and Coverage Rate dependency.
- Added parent eligibility with Maturity Age and participation limits.
- Added descending fitness ranking to Selection before probability mapping.
- Added proposal-based Mutation rules/rate/execution.
- Added proposal-based Crossover rules/rate/execution with integrity repair.
- Added offspring IDs/state and pending-content lifecycle.
- Added Abstraction, Elaboration, and Probing content operators.
- Added Age, Longevity Chance, and Perish lifecycle execution.
- Added Fusion/Defusion histories and threshold policy hooks.
- Added stateful PriorityEvolutionSession and expanded UI service contract to v1.1.
- Added offline priority smoke test and expanded automated suite to 63 tests.
- Updated paper/deferred-study traceability and priority scope documentation.
