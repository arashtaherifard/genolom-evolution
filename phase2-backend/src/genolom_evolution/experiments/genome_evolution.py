from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
from typing import Any, Iterable

from ..dataio.generation0 import load_generation0
from ..dataio.manifest import load_manifest, verify_manifest_dataset
from ..evaluation.diversity import population_diversity
from ..evaluation.macro import calculate_generation_macro_metrics
from ..evaluation.reference import ReferenceConceptSet, build_reference_concept_set
from ..evolution.lifecycle import LongevityPolicy, initialize_longevity
from ..evolution.scheduling import GenomeGenerationPolicy
from ..evolution.session import PriorityEvolutionSession
from ..tracking.evolution_exports import (
    build_genome_library,
    flatten_individual,
    lineage_edge_rows,
    lineage_node_rows,
    write_csv,
    write_graphml,
)
from ..tracking.run_store import RunStore


@dataclass(frozen=True, slots=True)
class GenomeEvolutionRunResult:
    run_id: str
    run_path: str
    requested_final_generation: int
    completed_final_generation: int
    final_population_size: int
    archive_size: int
    unique_genome_count: int
    extinct: bool
    reference_checksum: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _git_commit(root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _micro_summary(population) -> dict[str, float | int | None]:
    values = [float(i.micro_fitness) for i in population if i.micro_fitness is not None]
    cohesions = [float(i.cohesion) for i in population if i.cohesion is not None]
    dependences = [float(i.dependence) for i in population if i.dependence is not None]
    return {
        "mean_micro_fitness": statistics.fmean(values) if values else None,
        "median_micro_fitness": statistics.median(values) if values else None,
        "max_micro_fitness": max(values) if values else None,
        "min_micro_fitness": min(values) if values else None,
        "mean_cohesion": statistics.fmean(cohesions) if cohesions else None,
        "mean_dependence": statistics.fmean(dependences) if dependences else None,
    }


def _refresh_archive(session: PriorityEvolutionSession) -> None:
    for individual in session.population:
        session.historical_archive[individual.individual_id] = deepcopy(individual.to_dict())
    if session.genome_only_mode:
        for individual in session.population:
            if individual.generation_created > 0:
                session.variant_library[individual.individual_id] = deepcopy(individual.to_dict())


def _snapshot_for_export(session: PriorityEvolutionSession, generation: int) -> dict[str, Any]:
    return {
        "snapshot_version": "genome-evolution-v1",
        "generation": generation,
        "run_seed": session.seed,
        "genome_only_mode": session.genome_only_mode,
        "active_population_size": len(session.active_population),
        "total_individuals_created_so_far": len(session.population),
        "active_population": [deepcopy(i.to_dict()) for i in session.active_population],
    }


def _generation_metric_row(macro, diversity, micro, policy_summary=None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "generation": macro.generation,
        "population_size": macro.population_size,
        "reference_topic_count": macro.reference_topic_count,
        "keyword_occurrence_count": macro.keyword_occurrence_count,
        "coherent_keyword_occurrence_count": macro.coherent_keyword_occurrence_count,
        "unresolved_keyword_occurrence_count": macro.unresolved_keyword_occurrence_count,
        "coherency_rate": macro.coherency_rate,
        "covered_reference_topic_count": macro.covered_reference_topic_count,
        "coverage_span": macro.coverage_span,
        "recall": macro.recall,
        "precision": macro.precision,
        "generation_f1": macro.generation_f1,
        "precision_component_count": macro.precision_component_count,
        "precision_subgraph_node_count": macro.precision_subgraph_node_count,
        **micro,
        **diversity,
    }
    for threshold, value in sorted(macro.coverage_rates.items()):
        row[f"coverage_rate_at_{threshold}"] = value
        row[f"threshold_covered_topic_count_at_{threshold}"] = (
            macro.threshold_covered_topic_counts[threshold]
        )
    if policy_summary is not None:
        row["operator_attempt_budget"] = policy_summary.requested_attempts
        for operator, count in sorted(policy_summary.attempted_by_operator.items()):
            row[f"attempted_{operator}"] = count
        for operator, count in sorted(policy_summary.successful_by_operator.items()):
            row[f"successful_{operator}"] = count
        for operator, count in sorted(policy_summary.offspring_by_operator.items()):
            row[f"offspring_{operator}"] = count
        for operator, count in sorted(policy_summary.skipped_by_operator.items()):
            row[f"skipped_{operator}"] = count
    return row


class CompleteGenomeEvolutionRunner:
    """Run the genetic side from frozen Generation 0 to the requested horizon.

    No content generator, annotator, judge, embedding model, NLI model, or LLM
    is called.  Offspring genomes are admitted based on genetic/proposal rules
    only and are marked ``content_status='unrealized'``.
    """

    def __init__(self, config: dict[str, Any], ontology):
        self.config = deepcopy(config)
        self.ontology = ontology

    def run(
        self,
        project_root: str | Path,
        *,
        generation_count: int | None = None,
        seed: int | None = None,
        run_id: str | None = None,
    ) -> GenomeEvolutionRunResult:
        root = Path(project_root).resolve()
        dataset_path = root / self.config["dataset"]["path"]
        manifest_path = root / self.config["dataset"]["manifest"]
        if not verify_manifest_dataset(manifest_path, dataset_path):
            raise ValueError("Generation-0 dataset checksum does not match its frozen manifest.")
        manifest = load_manifest(manifest_path)
        generation0 = load_generation0(dataset_path)

        run_seed = int(
            self.config.get("reproducibility", {}).get("seed", 42)
            if seed is None
            else seed
        )
        generations = int(
            self.config.get("evolution", {}).get("max_generations", 50)
            if generation_count is None
            else generation_count
        )
        if generations < 0:
            raise ValueError("generation_count must be >= 0")

        self.config.setdefault("evolution", {})["genome_only_mode"] = True
        self.config.setdefault("reproducibility", {})["seed"] = run_seed
        self.config["evolution"]["max_generations"] = generations

        output_root = root / self.config.get("outputs", {}).get("root", "outputs/runs")
        store = RunStore(output_root, run_id=run_id)
        session = PriorityEvolutionSession(generation0, self.config, seed=run_seed)

        lcfg = self.config["evolution"]["longevity"]
        longevity_policy = LongevityPolicy(
            initial_chance=float(lcfg["initial_chance"]),
            reproduction_reward=float(lcfg["reproduction_reward"]),
            inactivity_penalty=float(lcfg["inactivity_penalty"]),
            perish_threshold=float(self.config["evolution"].get("perish", {}).get("threshold", 0.0)),
        )
        initialize_longevity(session.population, longevity_policy)

        reference: ReferenceConceptSet = build_reference_concept_set(generation0, self.ontology)
        if not reference.topics:
            raise ValueError("Frozen T_ref is empty; Generation-0 keywords did not resolve in the ontology.")

        coverage_thresholds = tuple(
            int(x)
            for x in self.config.get("coverage", {}).get("report_thresholds", [1, 2, 3, 5])
        )
        policy = GenomeGenerationPolicy(self.config)

        store.write_json_once("config.json", self.config)
        store.write_json_once("reference/t_ref.json", reference.to_dict())
        store.write_json_once(
            "run_manifest.json",
            {
                "schema_version": "genome-evolution-run-v1",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "genome_only": True,
                "content_generation_called": False,
                "requested_final_generation": generations,
                "seed": run_seed,
                "git_commit": _git_commit(root),
                "dataset_manifest": manifest,
                "dataset_sha256": _file_sha256(dataset_path),
                "t_ref_sha256": reference.checksum,
                "ontology_name": str(getattr(self.ontology, "name", type(self.ontology).__name__)),
                "scientific_status": self.config.get("project", {}).get("protocol_status"),
            },
        )

        generation_rows: list[dict[str, Any]] = []
        rank_rows: list[dict[str, Any]] = []
        policy_rows: list[dict[str, Any]] = []

        # Generation 0.
        session.compute_micro_fitness(self.ontology)
        _refresh_archive(session)
        macro = calculate_generation_macro_metrics(
            session.active_population,
            self.ontology,
            reference,
            generation=0,
            coverage_thresholds=coverage_thresholds,
        )
        diversity = population_diversity(session.active_population)
        micro = _micro_summary(session.active_population)
        generation_rows.append(_generation_metric_row(macro, diversity, micro))
        rank_rows.extend(
            {"generation": 0, **entry.to_dict()} for entry in macro.coherency_rank
        )
        store.write_generation_snapshot(0, _snapshot_for_export(session, 0))
        store.write_json_once("metrics/generation_0000.json", macro.to_dict())

        extinct = False
        completed_generation = 0
        for target_generation in range(1, generations + 1):
            if not session.active_population:
                extinct = True
                break

            # Fitness is always fresh before parent selection.
            session.compute_micro_fitness(self.ontology)
            policy_summary = policy.run(session, target_generation)
            lifecycle_summary = session.end_generation()

            # Evaluate the completed generation after offspring admission and
            # lifecycle updates, then refresh archive snapshots with the final
            # fitness values for that generation.
            session.compute_micro_fitness(self.ontology)
            _refresh_archive(session)
            macro = calculate_generation_macro_metrics(
                session.active_population,
                self.ontology,
                reference,
                generation=target_generation,
                coverage_thresholds=coverage_thresholds,
            )
            diversity = population_diversity(session.active_population)
            micro = _micro_summary(session.active_population)
            generation_rows.append(
                _generation_metric_row(macro, diversity, micro, policy_summary)
            )
            rank_rows.extend(
                {"generation": target_generation, **entry.to_dict()}
                for entry in macro.coherency_rank
            )
            policy_rows.append(
                {
                    **policy_summary.to_dict(),
                    "lifecycle_summary": lifecycle_summary,
                }
            )

            # Export a compact active-generation snapshot.  Historical state is
            # exported once in the archive, avoiding N x archive duplication.
            store.write_generation_snapshot(
                target_generation,
                _snapshot_for_export(session, target_generation),
            )
            store.write_json_once(
                f"metrics/generation_{target_generation:04d}.json",
                macro.to_dict(),
            )
            completed_generation = target_generation

        final_records = [deepcopy(i.to_dict()) for i in session.active_population]
        archive_records = [
            deepcopy(session.historical_archive[key])
            for key in sorted(session.historical_archive)
        ]
        final_active_ids = {str(item["individual_id"]) for item in final_records}
        library = build_genome_library(
            archive_records, final_active_ids=final_active_ids
        )

        # Canonical detailed JSON/JSONL artifacts.
        for record in final_records:
            store.append_jsonl("final_generation.jsonl", record)
        for record in archive_records:
            store.append_jsonl("archive/genome_archive.jsonl", record)
        for record in library:
            store.append_jsonl("library/genome_library.jsonl", record)
        for event in session.lineage.events:
            store.append_jsonl("logs/evolution_events.jsonl", event.to_dict())
        for attempt in session.rejected_attempts:
            store.append_jsonl("logs/rejected_genomes.jsonl", attempt)
        for row in policy_rows:
            store.append_jsonl("logs/generation_policy.jsonl", row)

        # Human/statistics-friendly tables.
        write_csv(store.path / "final_generation.csv", [flatten_individual(x) for x in final_records])
        write_csv(store.path / "archive/genome_archive.csv", [flatten_individual(x) for x in archive_records])
        write_csv(
            store.path / "library/genome_library.csv",
            [
                {
                    "genome_hash": row["genome_hash"],
                    "occurrence_count": row["occurrence_count"],
                    "first_seen_generation": row["first_seen_generation"],
                    "last_seen_generation": row["last_seen_generation"],
                    "best_micro_fitness": row["best_micro_fitness"],
                    "present_in_final_generation": row["present_in_final_generation"],
                    "individual_ids": "|".join(row["individual_ids"]),
                    **{f"genome.{key}": value for key, value in row["genome"].items() if key != "keywords"},
                    "genome.keywords": "|".join(row["genome"].get("keywords") or []),
                }
                for row in library
            ],
        )
        write_csv(store.path / "metrics/generation_metrics.csv", generation_rows)
        write_csv(store.path / "metrics/coherency_rank.csv", rank_rows)

        node_rows = lineage_node_rows(archive_records)
        edge_rows = lineage_edge_rows(session.lineage)
        write_csv(store.path / "lineage/nodes.csv", node_rows)
        write_csv(store.path / "lineage/edges.csv", edge_rows)
        write_graphml(store.path / "lineage/lineage.graphml", node_rows, edge_rows)
        store.write_json_once("lineage/lineage.json", session.lineage.to_dict())

        summary = GenomeEvolutionRunResult(
            run_id=store.run_id,
            run_path=str(store.path),
            requested_final_generation=generations,
            completed_final_generation=completed_generation,
            final_population_size=len(final_records),
            archive_size=len(archive_records),
            unique_genome_count=len(library),
            extinct=extinct,
            reference_checksum=reference.checksum,
        )
        store.write_json_once("summary.json", summary.to_dict())

        # Artifact checksums are written last.  Exclude the checksum file itself.
        checksums: dict[str, str] = {}
        for path in sorted(store.path.rglob("*")):
            if path.is_file() and path.name != "checksums.json":
                checksums[str(path.relative_to(store.path))] = _file_sha256(path)
        store.write_json_once("checksums.json", checksums)

        return summary


__all__ = ["GenomeEvolutionRunResult", "CompleteGenomeEvolutionRunner"]
