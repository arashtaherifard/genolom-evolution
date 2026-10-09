# Milestone 7.1 — Frozen Ecosystem Convergence Stop

M7.1 adds an optional convergence detector/stopper without changing the M7
operators, fitness definitions, ontology rules, lifecycle dynamics, or frozen
Generation 0.

## Frozen criterion (OUR_OPERATIONALIZATION)

At the earliest generation `G_t >= 10`, all of the following must hold over the
same five consecutive generations `G_(t-4)..G_t`:

- mean micro-fitness range <= `0.01`
- population range / window mean <= `0.05`
- unique-genome-ratio range <= `0.02`
- Recall range <= `0.02`

Precision, Coherency Rate, and F1 are not part of the stop rule because in the
first G0→G50 pilot Precision and Coherency were saturated at 1, while F1 was
largely driven by Recall.

## Modes

The convergence policy supports both:

- detection only: `enabled: true`, `stop_on_convergence: false`
- actual stopping: `enabled: true`, `stop_on_convergence: true`

The original M7 development config remains unchanged (`enabled: false`) so the
first G0→G50 pilot stays reproducible. Use
`configs/genome_evolution_convergence.yaml` for the M7.1 stop run.

The convergence config uses a safety ceiling of G100. If the ecosystem does not
converge by then, the run ends with `stop_reason=max_generations_reached` rather
than pretending convergence occurred.
