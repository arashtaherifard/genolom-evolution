# M7 Test Status — Complete Genome Evolution

Baseline supplied by the user was the verified M6 package:

```text
145 passed
```

M7 adds tests for:

- Proposal Figure-14 Metamorphosis Matrix;
- Proposal Figure-15 Composition Matrix;
- frozen generation macro metrics;
- genome-only offspring admission without content realization;
- complete multi-generation run/export contract.

Current suite:

```text
151 passed
```

A separate non-scientific execution smoke test also completed the full 50-generation orchestration path using an exact-keyword test ontology (not CSO and not paper evidence):

```text
requested_final_generation: 50
completed_final_generation: 50
extinct: false
```

Real scientific runs must use the CSO-backed CLI and calibrated/frozen parameters.
