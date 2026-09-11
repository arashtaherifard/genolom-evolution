# Phase 2 - Milestone 4: Proposal-exact Content Planning

This is the corrected Milestone-4 overlay built directly from the uploaded proposal:
`NShahhoseini Proposal After Revision Highlighted.pdf`.

It extends the clean Milestone-3 TargetGenome/RealizedGenome architecture. It does **not** redesign the evolutionary operators and it does **not** add the Milestone-5 LLM/NLI stack.

## Authoritative proposal locations used

- Appendix A, page 87: content-operation matrix by source `learningResourceType` for:
  - interactivity-level increase/decrease
  - semantic-density increase/decrease
  - difficulty increase/decrease
- Appendix B, pages 89-93: source->target `learningResourceType` transition tables for:
  - Exercise
  - Question
  - Problem Statement
  using the exact actions `==`, `is_Same_as()`, `Drop()`, and `Converts_to()`.
- Appendix C, pages 95-96: ordinal mutation matrices for:
  - `interactivityLevel` -> `ilIncrease(n)` / `ilDecrease(n)`
  - `semanticDensity` -> `sdIncrease(n)` / `sdDecrease(n)`
  - `difficulty` -> `diffIncrease(n)` / `diffDecrease(n)`

The project V1 meaning of `n` remains the frozen deterministic ordinal distance:

`n = abs(target_index - source_index)`

## What this corrected milestone adds

- deterministic `SourceGenome -> TargetGenome -> GenomeDiff -> ContentPlan`
- proposal-exact Appendix-A operation rows, keyed by the **source** learning-resource type
- proposal-exact Appendix-B resource-type transitions as the scientific defaults
- Appendix-C action helper for exact ordinal mutation labels
- typed proposal-step records carrying proposal provenance
- explicit rule classifications:
  - `PROPOSAL_DEFINED`
  - `OUR_OPERATIONALIZATION`
  - `UNSUPPORTED`
  - plus `CONFIGURED` / `DEFERRED` for controlled extension points
- parent-only grounding context, extensible later to approved same-textbook evidence
- explicit `UNSUPPORTED_REALIZATION` gating before a generator is called
- direction-only handling for `typicalLearningTime`
- blocked proposal plans never reach content generation

## Important corrections versus the discarded first M4 build

The discarded M4 build simplified the proposal too aggressively. In particular:

1. Semantic-density decrease is **not** globally `Expand(n)`.
   Appendix A makes it source-type dependent. For example:
   - Narrative Text -> `Expand(n)`
   - Exercise -> `Unpack(hints: text, voice, video, animation)`
   - Hypertext Document -> both `Expand(n)` and `Unpack(...)`

2. Interactivity-level changes are **not** generic `Add_Actions(n)` / `Remove_Actions(n)`.
   Appendix A gives concrete action sets such as Navigation, Click, Animation, Hotspots, TextInput, and Export2HTML.

3. Difficulty changes are also source-type dependent.
   For example, Exercise difficulty increase uses both `Cognitive_Level_up(n)` and `sdIncrease(n)`, while Narrative Text uses only `sdIncrease(n)`.

4. Appendix-B resource-type transitions are now built in as proposal-defined defaults. They are no longer an empty table to be configured later.

## Appendix-B `Drop()` semantics

The Persian explanation in Appendix B labels `Drop()` transitions as non-convertible (`غیر قابل تبدیل`). Therefore the planner records the exact `Drop()` step and marks the plan as blocking. It does not call a generator for that target.

## Appendix-B `Index` anomaly

The Question and Problem Statement tables contain a `Drop() Index` row even though:

- `Index` is not shown as a destination-column header in the table, and
- `Index` is not in the frozen Phase-1 learningResourceType vocabulary.

This is stored in `APPENDIX_B_DOCUMENTED_ANOMALIES` for traceability, but it is deliberately **not** added as a valid GenoLOM transition. This is a documented proposal inconsistency, not silently repaired.

## Appendix-C difficulty-label discrepancy

Appendix C visually labels the five difficulty positions with very-low..very-high terminology, while the project/Phase-1 GenoLOM vocabulary is:

`Very Easy -> Easy -> Medium -> Difficult -> Very Difficult`.

The implementation maps those five positions by ordinal index. The `diffIncrease(n)` / `diffDecrease(n)` action is proposal-defined; the vocabulary reconciliation is a project operationalization already consistent with the frozen V1 difficulty scale.

## Undefined rules

Generation-0 is not reduced to the resource types shown in Appendix A/B. If a source type exists in the real dataset but the proposal does not define the required Appendix-A operation or Appendix-B transition, the planner returns a blocking `UNSUPPORTED` issue rather than inventing a transformation.

This preserves the frozen policy:

- mutation must not invent unsupported LRT transitions;
- crossover remains conservative where a proposal rule is absent;
- the content realizer never decides scientific transition validity.

## Artifact-renderer boundary

The proposal can define a valid conversion while Phase-2 V1 still lacks a renderer for the resulting artifact. These are separate questions.

The current text-only V1 capability gate defaults to unsupported realization for:

- Simulation
- Video Clip
- Slide
- Authoring Tool

A proposal-valid `Converts_to()` can therefore still be blocked as `UNSUPPORTED_REALIZATION`. This does not redefine the proposal; it prevents false claims that a text generator produced a real multimedia/interactive artifact.

## Backward compatibility

- `compile_structural_content_plan()` preserves the Milestone-3 structural-plan behavior.
- M4 fields remain appended to the existing plan/request structures.
- the Milestone-3 lazy-import hotfix in `evolution/__init__.py` is **not** overwritten by this overlay.
- service/UI code should continue to use the existing engine/service APIs rather than planner internals.

## Test-generator warning

The deterministic test generator and accepting validator are test infrastructure only. Passing tests demonstrates contract/integration behavior; it is not scientific evidence that generated educational content satisfies the target GenoLOM genome.
