# Phase 2 — Milestone 5: Content Realization + Blind Validation

## Scope

Milestone 5 implements the provider-independent realization and validation architecture that follows the proposal-exact Milestone-4 ContentPlan.

The proposal remains authoritative for WHAT content transformations mean. In particular, the proposal methodology defines the three high-level evolution processes (abstraction/condensation, elaboration, and questioning) and their GenoLOM effects on pp. 68–69, while Appendices A–C provide the detailed rule tables already encoded in Milestone 4.

The LLM/prompt/validation machinery in this milestone is **OUR_OPERATIONALIZATION**, frozen by the Team-405 architecture. It is not claimed to be specified by the proposal.

## Implemented architecture

### 1. Frozen prompt registry

The six frozen V1 prompt roles are registered and hashed:

- `GENOLOM_CONTENT_GENERATOR_GROUNDED_V1`
- `GENOLOM_CONTENT_GENERATOR_PARAMETRIC_V1`
- `GENOLOM_REALIZED_GENOME_ANNOTATOR_V1`
- `GENOLOM_CLAIM_JUDGE_V1`
- `GENOLOM_CONTENT_REPAIR_V1`
- `GENOLOM_DIRECT_LLM_BASELINE_V1`

Every prompt has a version and SHA-256 hash. Scientific requests record prompt ID/version/hash.

### 2. Provider-independent local content realization

`LocalLLMGenerator` depends only on a `LocalTextModelBackend` protocol. A generic lazy `TransformersLocalTextBackend` is included so an open-weight local model can be supplied later without redesigning the content pipeline.

No paid API dependency is introduced.

Grounded mode:

- target is predefined and visible to the generator;
- generator receives SourceGenome, TargetGenome, ContentPlan, grounding evidence, and generation info;
- factual claims must be supported by supplied evidence;
- `added_claims` must be empty;
- generator may return `status=impossible` instead of inventing evidence.

Parametric mode:

- same target/plan contract;
- newly introduced claims must be listed in `added_claims`;
- M5 does not silently accept these claims until an external validation source is frozen.

### 3. Blind realized-genome annotation

`AnnotationRequest` deliberately has **no `target_genome` field and no ContentPlan field**.

The blind annotator infers:

- learningResourceType
- interactivityType
- interactivityLevel
- semanticDensity
- difficulty
- typicalLearningTime

Deterministic features are extracted separately:

- language
- word count
- sentence count
- question markers
- detectable interactive markers

Rule reconciliation then constructs the realized genome. Objectively detectable information takes priority or produces a visible conflict. Keywords are freshly re-extracted from the generated artifact rather than copied from the target/source.

### 4. Validation pipeline

The scientific validator follows ordered gates, never a mysterious weighted average:

1. hard deterministic rules
2. blind realized-genome inference
3. Target ↔ Realized agreement
4. semantic topic similarity
5. deterministic claim extraction + NLI
6. independent factual judge
7. accept / retry / reject

Controlled categorical/ordinal target traits exact-match according to the frozen M4 rules. Fixed traits remain fixed. Typical learning time is directional rather than exact-match.

### 5. Local validation-model adapters

Lazy adapters are provided for the frozen initial choices:

- topic similarity: `sentence-transformers/all-mpnet-base-v2`
- NLI: `cross-encoder/nli-deberta-v3-large`

They do not download/load weights on ordinary imports. Optional local dependencies are only needed when scientific validation is actually executed.

### 6. Topic threshold calibration

A raw arbitrary threshold is not accepted as a scientific calibration object. `TopicSimilarityCalibration` requires:

- threshold
- pilot-set ID
- calibration method
- frozen status

The intended procedure is to choose the threshold on pilot topic-preserving/topic-drifted pairs, freeze it, and never tune it on final experimental results.

### 7. Independent judge vs self-judge

The independent judge can gate acceptance.

The self-judge is stored only as a diagnostic. It cannot add an acceptance failure even if it disagrees with the independent judge.

### 8. Frozen three-attempt repair protocol

At most three generation attempts are allowed.

- Attempt 1: normal grounded/parametric generation prompt.
- Attempt 2: frozen repair prompt + structured validator feedback + previous candidate.
- Attempt 3: same repair protocol.
- If the third attempt remains invalid, the result is rejected and `retries_exhausted` is recorded.

Each retry receives a deterministic seed derived from the original event seed and attempt index. All responses/validations from all attempts are serialized; completed scientific outputs are not regenerated later.

### 9. Direct-LLM baseline request

A separate direct-baseline request/generator path is included. Its request contains no evolutionary TargetGenome, preserving the intended baseline distinction.

## Scientific boundaries / deferred work

The following are intentionally **not** invented in M5:

- a default open-weight generator model (model selection must be benchmarked/frozen separately);
- a topic-similarity threshold (requires pilot calibration);
- external validation rules for new parametric-mode claims;
- human/expert evaluation thresholds;
- paid OpenAI/Anthropic API implementations;
- renderer support for multimedia types already marked `UNSUPPORTED_REALIZATION` in M4.

The deterministic keyword extractor in M5 is a reproducible plumbing implementation, not a replacement for final CSO/topic extraction. It is clearly separated from the acceptance objective.
