# Phase 2 Backend - GenoLOM Evolution

Research-grade, UI-aware backend for Phase 2 of the GenoLOM evolutionary educational-content project.

## Status

This package is **Milestone 2: Priority (Blue-Row) Operators & Variables**. It keeps all Milestone-1 architecture and implements the updated task-sheet priority scope plus required dependencies.

Implemented now:

- frozen Generation 0 + SHA256 manifest;
- proposal-aware GenoLOM validation;
- Cohesion;
- canonical **Dependence** proxy (with legacy `coherence` alias for compatibility);
- weighted Micro Fitness;
- Selection workflow: fitness -> descending rank -> probability mapping -> stochastic selection;
- fitness-proportionate main selection + random baseline;
- Parent Eligibility and Maturity Age dependency;
- Mutation Rules + Mutation Rate + executable Mutation;
- Crossover Rules + Crossover Rate + executable Crossover;
- target-genome validation and integrity repair;
- offspring creation;
- Abstraction, Elaboration, and Probing content-operator contracts/execution;
- Age, Longevity Chance, and Perish;
- Fusion/Defusion History and Threshold state/policy;
- generation-level Coverage Span + Coverage Threshold + required Coverage Rate;
- operator events and full lineage tracking;
- reproducible stateful priority evolution session;
- UI-facing service facade with serializable query/preview/session methods;
- future-study hooks for the deferred paper-strength items;
- **63 automated tests**.

Actual Fusion/Defusion transformations, Composition/Decomposition, full macro Coherency/Recall/Precision/F1, and the complete multi-generation experiment loop remain later milestones. They are not fabricated merely to make the checklist look complete.

See `PRIORITY_SCOPE.md` for the exact blue-row mapping and dependency rationale.

## Canonical input

`data/generation_0.xlsx` is the frozen strict Phase-1 `ch01_cso_main.xlsx`. Its checksum is stored in `data/generation_0.sha256` and `data/dataset_manifest.json`.

## Quick start

```bash
cd phase2-backend
python3.12 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/preflight.py
python scripts/smoke_service.py
python scripts/smoke_priority.py
```

Expected test result for this package:

```text
63 passed
```

### Real CSO-backed analysis

```bash
python scripts/preflight.py --with-ontology
python scripts/smoke_priority.py --with-cso
```

The first CSO run may download/build ontology resources through `cso-classifier`.

`smoke_priority.py` without `--with-cso` deliberately uses an offline ontology test double and deterministic content test double. That mode is only for backend verification and **must not be used as scientific evidence**.

## Configuration policy

`configs/default.yaml` intentionally leaves unresolved scientific parameters such as final mutation/crossover rates and longevity values as `null`. We do not guess final research settings.

`configs/development.yaml` contains clearly labeled development-only values so the workflow can be smoke-tested end to end. Final experiment values will later be frozen in a separate final protocol config.

## UI-awareness rule

Phase 3 should use:

```text
UI -> Phase2Engine -> evolution / fitness / evaluation / content
```

The UI must not import low-level operators, CSO code, or workbook loaders directly. `Phase2Engine` returns JSON-serializable DTOs and owns session-level orchestration. A content generator/validator is injected into the backend service, not into the UI.

See `UI_CONTRACT.md`, `TECHNICAL_SPEC.md`, `PAPER_TRACEABILITY.md`, and `DEFERRED_EVALUATION_HOOKS.md`.
