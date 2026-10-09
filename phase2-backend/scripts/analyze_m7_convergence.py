#!/usr/bin/env python3

import csv
import json
import sys
from pathlib import Path

# FROZEN M7.1 CONVERGENCE CRITERION
MIN_GENERATION = 10
WINDOW = 5

FITNESS_RANGE_MAX = 0.01
POPULATION_REL_RANGE_MAX = 0.05
UNIQUE_GENOME_RATIO_RANGE_MAX = 0.02
RECALL_RANGE_MAX = 0.02


def f(row, key):
    return float(row[key])


def i(row, key):
    return int(float(row[key]))


def analyze_window(rows):
    fitness = [f(r, "mean_micro_fitness") for r in rows]
    population = [f(r, "population_size") for r in rows]
    unique_ratio = [f(r, "unique_genome_ratio") for r in rows]
    recall = [f(r, "recall") for r in rows]

    fitness_range = max(fitness) - min(fitness)

    pop_mean = sum(population) / len(population)
    population_rel_range = (
        (max(population) - min(population)) / pop_mean
        if pop_mean else float("inf")
    )

    unique_range = max(unique_ratio) - min(unique_ratio)
    recall_range = max(recall) - min(recall)

    return {
        "fitness_range": fitness_range,
        "fitness_stable": fitness_range <= FITNESS_RANGE_MAX,

        "population_relative_range": population_rel_range,
        "population_stable": population_rel_range <= POPULATION_REL_RANGE_MAX,

        "unique_genome_ratio_range": unique_range,
        "unique_stable": unique_range <= UNIQUE_GENOME_RATIO_RANGE_MAX,

        "recall_range": recall_range,
        "recall_stable": recall_range <= RECALL_RANGE_MAX,
    }


def main():
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        csv_path = Path(
            "results/pilot_g50_seed42/metrics/generation_metrics.csv"
        )

    if not csv_path.exists():
        raise SystemExit(f"Metrics file not found: {csv_path}")

    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    rows.sort(key=lambda r: i(r, "generation"))
    by_gen = {i(r, "generation"): r for r in rows}

    convergence_rows = []
    convergence_generation = None

    for g in sorted(by_gen):
        if g < MIN_GENERATION:
            continue

        start = g - WINDOW + 1
        gens = list(range(start, g + 1))

        if not all(x in by_gen for x in gens):
            continue

        window_rows = [by_gen[x] for x in gens]
        result = analyze_window(window_rows)

        converged = (
            result["fitness_stable"]
            and result["population_stable"]
            and result["unique_stable"]
            and result["recall_stable"]
        )

        record = {
            "generation": g,
            "window_start": start,
            "window_end": g,
            **result,
            "converged": converged,
        }

        convergence_rows.append(record)

        if converged and convergence_generation is None:
            convergence_generation = g

    print()
    print("=== FROZEN M7.1 CONVERGENCE CRITERION ===")
    print(f"Minimum generation:             G{MIN_GENERATION}")
    print(f"Rolling window:                 {WINDOW} generations")
    print(f"Mean micro-fitness range <=     {FITNESS_RANGE_MAX}")
    print(f"Population relative range <=    {POPULATION_REL_RANGE_MAX:.1%}")
    print(f"Unique-genome-ratio range <=    {UNIQUE_GENOME_RATIO_RANGE_MAX}")
    print(f"Recall range <=                 {RECALL_RANGE_MAX}")
    print("All conditions required:        YES")

    print()

    if convergence_generation is None:
        print("RESULT: No ecosystem convergence detected through G50.")
    else:
        print(
            f"RESULT: Earliest ecosystem convergence detected "
            f"at G{convergence_generation}."
        )

    endpoints = []

    if convergence_generation is not None:
        endpoints.append(("G_convergence", convergence_generation))

    for g in [40, 50]:
        if g in by_gen and all(existing != g for _, existing in endpoints):
            endpoints.append((f"G{g}", g))

    print()
    print("=== ENDPOINT COMPARISON ===")

    header = [
        "Endpoint",
        "Gen",
        "Population",
        "MeanFit",
        "Cohesion",
        "Dependence",
        "UniqueRatio",
        "Covered",
        "Recall",
        "Precision",
        "F1",
    ]

    print(
        f"{header[0]:<15}"
        f"{header[1]:>5}"
        f"{header[2]:>12}"
        f"{header[3]:>11}"
        f"{header[4]:>11}"
        f"{header[5]:>12}"
        f"{header[6]:>13}"
        f"{header[7]:>9}"
        f"{header[8]:>10}"
        f"{header[9]:>11}"
        f"{header[10]:>10}"
    )

    endpoint_output = []

    for label, g in endpoints:
        r = by_gen[g]

        values = {
            "endpoint": label,
            "generation": g,
            "population_size": i(r, "population_size"),
            "mean_micro_fitness": f(r, "mean_micro_fitness"),
            "mean_cohesion": f(r, "mean_cohesion"),
            "mean_dependence": f(r, "mean_dependence"),
            "unique_genome_ratio": f(r, "unique_genome_ratio"),
            "covered_reference_topic_count":
                i(r, "covered_reference_topic_count"),
            "recall": f(r, "recall"),
            "precision": f(r, "precision"),
            "generation_f1": f(r, "generation_f1"),
        }

        endpoint_output.append(values)

        print(
            f"{label:<15}"
            f"{g:>5}"
            f"{values['population_size']:>12}"
            f"{values['mean_micro_fitness']:>11.4f}"
            f"{values['mean_cohesion']:>11.4f}"
            f"{values['mean_dependence']:>12.4f}"
            f"{values['unique_genome_ratio']:>13.4f}"
            f"{values['covered_reference_topic_count']:>9}"
            f"{values['recall']:>10.4f}"
            f"{values['precision']:>11.4f}"
            f"{values['generation_f1']:>10.4f}"
        )

    if convergence_generation is not None:
        record = next(
            r for r in convergence_rows
            if r["generation"] == convergence_generation
        )

        print()
        print("=== CONVERGENCE WINDOW DIAGNOSTICS ===")
        print(
            f"G{record['window_start']}–G{record['window_end']}"
        )
        print(
            "Fitness range:              "
            f"{record['fitness_range']:.6f}"
        )
        print(
            "Population relative range:  "
            f"{record['population_relative_range']:.4%}"
        )
        print(
            "Unique-genome-ratio range:  "
            f"{record['unique_genome_ratio_range']:.6f}"
        )
        print(
            "Recall range:               "
            f"{record['recall_range']:.6f}"
        )

    outdir = Path(
        "results/pilot_g50_seed42/convergence_analysis"
    )
    outdir.mkdir(parents=True, exist_ok=True)

    with (outdir / "convergence_windows.csv").open(
        "w", newline="", encoding="utf-8"
    ) as fh:
        fields = list(convergence_rows[0].keys())
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(convergence_rows)

    with (outdir / "endpoint_comparison.csv").open(
        "w", newline="", encoding="utf-8"
    ) as fh:
        if endpoint_output:
            writer = csv.DictWriter(
                fh, fieldnames=list(endpoint_output[0].keys())
            )
            writer.writeheader()
            writer.writerows(endpoint_output)

    summary = {
        "criterion_status": "FROZEN_M7_1",
        "criterion_type": "OUR_OPERATIONALIZATION",
        "minimum_generation": MIN_GENERATION,
        "window": WINDOW,
        "fitness_range_max": FITNESS_RANGE_MAX,
        "population_relative_range_max":
            POPULATION_REL_RANGE_MAX,
        "unique_genome_ratio_range_max":
            UNIQUE_GENOME_RATIO_RANGE_MAX,
        "recall_range_max": RECALL_RANGE_MAX,
        "earliest_convergence_generation":
            convergence_generation,
    }

    (outdir / "convergence_criterion_and_result.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print()
    print("Saved analysis to:")
    print(outdir)


if __name__ == "__main__":
    main()
