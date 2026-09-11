# M6 Test Status

Reconstructed baseline before M6:

- M5A + legacy-prompt hotfix
- 120 tests passing

M6 additions:

- proposal Table-2 DNA encoding and width
- Phase-1/Table-2 learning-resource compatibility mapping and logging
- fractional-minute learning-time quantization at the Fusion DNA boundary
- AND / OR valid Fusion cases
- XOR / NAND invalid-one-hot rejection
- invalid different-category Fusion handling
- Fusion session target/provenance/history behavior
- Fusion threshold enforcement
- generic content-realizer blocking for Fusion
- provenance-based Defusion recovery and session targets
- deterministic Composition ordering/roles/content spans
- exact Decomposition recovery
- service capability/UI-contract update

Final reconstructed suite:

```text
145 passed
```

`compileall` and overlay diff checks are run before packaging.
