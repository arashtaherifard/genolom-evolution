# Milestone 3 — Target/Realized Genome + Orchestration Foundation

This bundle is an overlay patch for `phase2-backend`. Copy the contained
`src/` and `tests/` paths over the current Phase-2 backend.

## What this milestone implements

1. **Target Genome vs Realized Genome**
   - `Individual.target_genome` stores what evolution intended.
   - `Individual.realized_genome` stores what accepted generated content was
     independently reported to realize.
   - The legacy `Individual.genome` field remains for backward compatibility
     and represents the current/provisional genome. Pending session offspring
     keep their source/base genome there; after acceptance it is promoted to
     the explicit realized genome.

2. **Deterministic GenomeDiff**
   - `GenomeDiff.between(source, target)` compares every GenoLOM field in Python.
   - Ordinal changes use the frozen V1 definition:
     `n = abs(target_index - source_index)`.
   - No LLM/model participates.

3. **Structural ContentPlan**
   - M3 compiles a deterministic structural plan containing the GenomeDiff,
     controlled changed traits, and any fixed-trait changes.
   - `proposal_native_steps` is intentionally empty in M3.
   - Mapping to Pack / Expand / Unpack / Cognitive-Level / Add-Actions /
     resource conversion is **deferred to Milestone 4**, so this patch does not
     silently invent proposal rules.

4. **Content realization contract**
   - `GenerationRequest` now carries `source_genome` and `content_plan`.
   - `ContentValidationResult` can return `realized_genome`.
   - Session acceptance requires an explicit realized genome and checks the
     exact frozen V1 target↔realized traits controlled by the current plan plus
     fixed traits.
   - The deterministic test validator explicitly marks its assumption
     `test_double_assumes_target_realization=True` and remains
     `not_for_scientific_use=True`.

5. **Archive / library / rejected-attempt separation**
   - `active_population`
   - `historical_archive`
   - `variant_library`
   - `rejected_attempts`
   - Rejected attempts never enter the usable variant library.

6. **Generation snapshots**
   - Every completed generation creates a serializable `m3-v1` snapshot.
   - `RunStore.write_generation_snapshot()` persists immutable generation files.
   - Rejected attempts can be persisted to JSONL scientific logs.

7. **Multi-generation orchestration**
   - `experiments.orchestration.run_generations()` provides a complete
     generation-transition loop.
   - It *requires* an explicit `generation_step` callback supplied by the
     experiment. It does not invent mutation/crossover/operator budgets or
     stopping rules.

8. **Randomness separation**
   - Evolution retains its own RNG stream.
   - Content realization gets stable event-specific seeds derived with SHA-256
     from run seed + generation + individual + operator + purpose.
   - This avoids Python's randomized process hash and avoids coupling content
     randomness to evolutionary RNG draws.

## Scientific-rule status

### Proposal/frozen-design defined
- Evolution target and realized artifact metadata are separate.
- GenomeDiff is deterministic.
- Ordinal distance `n` is absolute index distance.
- Fixed traits remain fixed.
- Controlled categorical/ordinal traits require target↔realized agreement.
- Rejected attempts are logs, not usable library items.
- Intermediate accepted variants remain valuable.
- Evolution/content randomness are separated.

### Our operationalization
- `TargetGenome` and `RealizedGenome` are nominal typing roles over the existing
  `GenoLOMGenome`, preserving runtime compatibility.
- `Individual.genome` remains the legacy/current genome field while the two new
  explicit fields carry intent and realization.
- M3 archive/library stores serialized snapshots keyed by individual ID.
- Content event seeds use the first 64 bits of a SHA-256 digest.
- Multi-generation orchestration takes an explicit generation policy callback.

### Deferred
- Proposal-native transformation compilation (Milestone 4).
- Grounded-context implementation and unsupported multimedia realizers (M4).
- Real local-LLM metadata annotator, MPNet, NLI, independent judge,
  retry/repair, and prompt/version tracking (M5).
- `typicalLearningTime` direction-consistency gating once a real realized-time
  estimator is present (M5).
- Fusion / Defusion / Composition / Decomposition execution (M6).
- Macro convergence/stopping and complete library query/export metrics (M7).

## Compatibility

Existing constructor field order is preserved by appending new optional fields.
Existing service methods do not need to import low-level modules: the UI can
continue using `Phase2Engine.session_snapshot()`, which now surfaces the M3
archive/library/snapshot state through the existing service boundary.
