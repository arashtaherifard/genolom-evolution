# UI Contract - v1.1

Phase 2 is backend-first and UI-aware.

## Boundary

```text
Phase 3 UI
    |
    v
Phase2Engine
    |
    +-- models / validation
    +-- fitness / evaluation
    +-- selection / evolution
    +-- content operators
    +-- lineage / run artifacts
```

The UI must not import low-level mutation, crossover, ontology, workbook, or LLM-provider code directly.

## Current service capabilities

Read/query operations:

- `capabilities()`
- `dataset_info()`
- `preflight()`
- `population_summary()`
- `get_individual(id)`
- `compute_priority_metrics()`
- `eligibility(id, operator)`
- `fusion_defusion_status(id)`
- `content_operator_contracts()`

Pure previews:

- `preview_mutation(id, rate, seed)`
- `preview_crossover(parent_a, parent_b, rate, seed)`

Stateful session operations:

- `start_priority_session(seed)`
- `session_apply_mutation(parent_id, ...)`
- `session_apply_crossover(parent_a_id, parent_b_id, ...)`
- `session_apply_content_operator(child_id, operator_name, ...)`
- `session_lineage(individual_id)`
- `session_snapshot()`
- `session_end_generation()`

All service responses use `ServiceResult` and are JSON-serializable.

## Content-provider boundary

The UI never sends a Python model client into an operator. A `ContentGenerator` and `ContentValidator` are injected when the backend service is constructed. Later a web/API composition layer can provide an OpenAI/other adapter while the Phase-3 UI continues to call the same service methods.

## Future compatibility

The service boundary is intentionally compatible with later:

- generation progress/event streaming;
- experiment run launch/cancel/status;
- lineage visualizations;
- parameter scenario/grid controls;
- human-evaluation export/import;
- held-out dataset switching;
- additional ontology adapters.
