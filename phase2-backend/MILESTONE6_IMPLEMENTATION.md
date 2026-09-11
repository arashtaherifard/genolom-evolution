# Milestone 6 — Structural Evolution Operators

## Scope

M6 implements the structural operator layer on top of the clean M5A checkpoint:

- Fusion
- Defusion
- Composition
- Decomposition

Real local-LLM selection/calibration (M5B) is deliberately deferred until after M8A coding, so M6 must not fabricate real Fusion/Defusion content.

## Proposal-defined basis

The proposal states that:

- metadata traits are represented as DNA-like genes;
- Fusion combines two or more DNA sequences using binary AND, OR, XOR and NAND operators;
- Defusion acts on one DNA sequence and should yield at least two viable sequences;
- Composition concatenates/combines learning objects while keeping original parents independently identifiable and requires layout/morphology information;
- Decomposition extracts content that is identifiable in the compound parent;
- Table 2 represents age with 7 bits (0–120) and typical learning time with 6 bits (0–45), while description and keywords are not binary-coded fields.

Appendix D is the proposal's crossover matrix; Appendix E provides an expert-panel metamorphosis/co-occurrence relation map. They are retained as proposal context but are not silently converted into extra M6 algorithms.

## Explicit V1 operationalizations

### Fusion

- Table-2 categorical cells are encoded one-hot.
- Invalid one-hot output after a bitwise operator is a failed Fusion attempt.
- No LLM repairs invalid DNA.
- Current `18+` fixed age metadata is encoded by its lower bound (18); values decoded away from the frozen metadata are rejected by normal genome validation.
- Both Phase 1 and the proposal use **minutes** for `typicalLearningTime` (the proposal example shows `15 Min`). Table 2 does not specify how fractional minutes map into its 6-bit 0–45 field, so M6 uses a documented DNA-boundary quantization: nearest whole minute, with positive sub-minute values represented as 1 minute. The source genome keeps its original fractional value and every normalization is logged as `OUR_OPERATIONALIZATION`.
- Learning-resource-type vocabulary mismatches are handled through an explicit DNA adapter rather than by editing Generation 0: current `Question` maps to Table-2 `Questionnaire`; `Headline` maps to Table-2 `Narrative Text` for Fusion encoding based on the proposal Appendix-E Text → Paragraph → Headline hierarchy. If both parents are `Headline`, the decoded child preserves `Headline`; the mapping is otherwise a deliberate coarse-graining and is logged.
- Table 2 and later proposal appendices disagree on parts of `learningResourceType`. Values not representable in Table 2 fail Fusion cleanly instead of receiving an invented code.
- `description` and `keywords` do not participate in bitwise Fusion. Description gets an auditable provenance description; keywords use stable ordered union.

### Defusion

The proposal does not provide a sufficiently precise general inverse for arbitrary bitwise Fusion. V1 Defusion therefore only applies to Fusion-derived objects with stored parent snapshots. It recovers those parent target genomes and creates pending Defusion targets for later structural content realization.

This restriction is **OUR_OPERATIONALIZATION**, not claimed as a fully specified proposal algorithm.

### Composition

Composition is deterministic and structural. It:

- preserves exact parent content;
- stores parent IDs, order, roles, source metadata and exact rendered content spans;
- uses source-row order only when parents share a source and numeric source-row IDs are available, otherwise selection order;
- performs no LLM rewriting.

The proposal does not specify a single GenoLOM genome for the compound container. V1 therefore uses the first ordered component genome as a nonsemantic compatibility envelope while storing every component genome losslessly.

### Decomposition

V1 only decomposes Composition-V1 objects with stored component boundaries. It recreates each component exactly, with original content and genome. Unstructured multimedia/slides/video decomposition is deferred because boundary suggestion/rendering would require additional validated machinery.

## Content-realization boundary

Fusion and Defusion create **pending target genomes**, not fake accepted text. The generic single-source content operator is explicitly blocked for these children. Real Fusion/Defusion realization remains part of deferred M5B.

Composition and Decomposition are accepted deterministic structural artifacts because they do not synthesize or rewrite educational content.

## Service boundary

`Phase2Engine` UI contract v1.2 exposes:

- `session_apply_fusion(...)`
- `session_apply_defusion(...)`
- `session_apply_composition(...)`
- `session_apply_decomposition(...)`

The UI still does not access low-level operator modules directly.
