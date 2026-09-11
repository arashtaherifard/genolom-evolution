# Milestone 5 Hotfix 1 — Legacy operator prompt contract

## Problem

M5 introduced frozen/versioned scientific prompt IDs on `GenerationRequest`, while the pre-M5 content-operator contract tests expect operator-level IDs such as `elaboration-v1` when running with the explicit deterministic test generator.

## Fix

- Scientific/local-LLM execution is unchanged and still uses the registered M5 prompt ID/version/hash.
- `DeterministicTestGenerator` now declares an explicit test-only compatibility marker.
- `BaseContentOperator.execute()` preserves the old operator-level prompt ID only when that non-scientific test double is used.
- The corresponding scientific M5 prompt identity is retained in request metadata for traceability.
- The compatibility request is marked `scientific_use_allowed=False`.

This is an API/test compatibility fix only. It does not alter proposal rules, content planning, blind annotation, validation gates, retry policy, or scientific prompt identities.
