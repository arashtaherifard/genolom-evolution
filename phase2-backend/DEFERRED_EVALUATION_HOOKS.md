# Deferred Evaluation Hooks

These studies are intentionally postponed until framework development is complete, but Phase 2 remains compatible with them.

## Expert validation of Cohesion / Dependence

`evaluation/human.py` provides rating records with stable LO IDs. The operational Dependence proxy can later be correlated with blinded expert judgments without modifying the evolution engine.

## Held-out chapters / multiple chapters / second textbook

Dataset loading is manifest-driven and core models do not hard-code Chapter 1. `dataset_id`, `source_name`, `domain`, and `ontology_name` remain explicit.

## Another domain / ontology

Fitness depends on ontology protocols rather than CSO internals. Coverage additionally uses the reference-ontology provider contract. CSO is one adapter, not the architecture itself.

## Expert content evaluation and inter-rater reliability

Human-rating contracts store evaluator IDs, item IDs, dimensions, scores, and blinded conditions. Content generator and validator interfaces are separate so an LLM is not forced to judge its own output.

## Learner study

`evaluation/learner.py` remains decoupled from evolution state so later pre/post-test observations can be joined to exported materials/runs.
