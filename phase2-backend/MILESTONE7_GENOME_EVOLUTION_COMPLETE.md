# Milestone 7 — Complete Genome-Only Evolution

## Purpose

This milestone completes the genetic/evolutionary side of Phase 2 independently of content realization.

A run can now start from the frozen Generation 0, evolve through all configured generations, preserve every intermediate generation, and export the final active generation, complete historical individual archive, deduplicated genome library, lineage graph, event logs, and generation-level metrics.

Content generation is **not** called by this pipeline. Newly evolved genomes are marked `content_status = unrealized` and remain genetically active when `evolution.genome_only_mode = true`.

## Proposal-defined rules implemented here

- Figure 14 Metamorphosis Matrix as an explicit directed eligibility matrix.
- Figure 15 Composition Matrix as an explicit pairwise compatibility matrix.
- mutation, crossover, Fusion, Defusion, Composition, Decomposition;
- Age, Longevity and Perish;
- Coverage Span / Recall, Coherency Rate, Coherency Rank, Precision, F1 and Coverage Rate.

## Frozen Team-405 operationalizations implemented here

- `T_ref` = all unique Generation-0 keywords that successfully resolve to CSO, frozen once per run with SHA256.
- Coverage Span and Recall use direct reference-concept coverage and are equal in V1.
- Coherency Rate is LO-level keyword-occurrence based; duplicates within one LO are counted once, recurrence across LOs is retained.
- Coherency Rank scores a resolved keyword by the number of frozen reference concepts it covers through self + descendants.
- Precision connects only covered ancestor/descendant pairs through directed shortest hierarchy paths; unrelated branches are not joined through a broad common ancestor.
- Coverage Rate counts distinct LOs directly covering each reference concept and uses `count >= threshold`.
- Generation F1 is evaluation-only. It does not feed parent selection.
- Genome evolution is independent of content realization.
- Figure-14-allowed genome transitions may exist even when Appendix B does not yet define a content-realization procedure.

## Automatic generation policy

The proposal defines operators but does not fix one final operator scheduling probability/budget. M7 therefore makes scheduling fully configurable under `genome_evolution`.

`configs/genome_evolution_development.yaml` contains development-only smoke values. They are **not paper/final settings**.

Final values are to be selected using the already-frozen staged calibration protocol (5 -> 20 -> 30 -> 50 generations) and then copied into a frozen final config.

## Canonical run command

```bash
cd phase2-backend
python -m pip install -r requirements.txt
python scripts/run_genome_evolution.py \
  --config configs/genome_evolution_development.yaml \
  --generations 50 \
  --seed 42
```

The CLI uses the real `CSOOntologyAdapter`. No LLM/API is needed.

## Run artifact layout

Each run is written under `outputs/evolution/<run_id>/`:

```text
run_manifest.json
config.json
checksums.json
summary.json
reference/
  t_ref.json
generations/
  generation_0000.json
  generation_0001.json
  ...
  generation_0050.json
final_generation.jsonl
final_generation.csv
archive/
  genome_archive.jsonl
  genome_archive.csv
library/
  genome_library.jsonl
  genome_library.csv
lineage/
  nodes.csv
  edges.csv
  lineage.json
  lineage.graphml
metrics/
  generation_metrics.csv
  coherency_rank.csv
  generation_0000.json
  ...
logs/
  evolution_events.jsonl
  generation_policy.jsonl
  rejected_genomes.jsonl   # created only if needed
```

### Meaning of the three main outputs

- **Generation snapshot**: all active individuals in that generation.
- **Historical genome archive**: every individual that ever existed, including later-perished individuals.
- **Genome library**: unique full GenoLOM genome variants, deduplicated by canonical SHA256, with occurrence/final-presence metadata.

## Scientific-run warning

A successful 50-generation execution with the development config proves the software path works; it is not the final paper result. Final scientific runs begin only after genetic parameter calibration and protocol freeze.
