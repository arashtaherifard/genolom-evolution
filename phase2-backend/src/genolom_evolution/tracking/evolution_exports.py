from __future__ import annotations

from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..models.individual import Individual


def canonical_genome_hash(genome: dict[str, Any]) -> str:
    payload = json.dumps(
        genome,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_genome_library(
    archive_records: Iterable[dict[str, Any]],
    *,
    final_active_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    final_active_ids = set() if final_active_ids is None else set(final_active_ids)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    genome_by_hash: dict[str, dict[str, Any]] = {}

    for record in archive_records:
        genome = dict(record["genome"])
        digest = canonical_genome_hash(genome)
        groups[digest].append(record)
        genome_by_hash.setdefault(digest, genome)

    library: list[dict[str, Any]] = []
    for digest in sorted(groups):
        records = groups[digest]
        ids = sorted(str(record["individual_id"]) for record in records)
        generations = sorted({int(record.get("generation_created", 0)) for record in records})
        fitnesses = [
            float(record["micro_fitness"])
            for record in records
            if record.get("micro_fitness") is not None
        ]
        library.append(
            {
                "genome_hash": digest,
                "genome": genome_by_hash[digest],
                "individual_ids": ids,
                "occurrence_count": len(records),
                "first_seen_generation": min(generations) if generations else 0,
                "last_seen_generation": max(generations) if generations else 0,
                "generations_created": generations,
                "created_by": sorted({str(record.get("created_by", "")) for record in records}),
                "best_micro_fitness": max(fitnesses) if fitnesses else None,
                "present_in_final_generation": any(item in final_active_ids for item in ids),
                "final_active_individual_ids": sorted(final_active_ids.intersection(ids)),
            }
        )
    return library


def flatten_individual(record: dict[str, Any]) -> dict[str, Any]:
    genome = dict(record.get("genome") or {})
    return {
        "individual_id": record.get("individual_id"),
        "generation_created": record.get("generation_created"),
        "alive": record.get("alive"),
        "content_status": record.get("content_status"),
        "created_by": record.get("created_by"),
        "parent_ids": "|".join(record.get("parent_ids") or []),
        "age": record.get("age"),
        "longevity_chance": record.get("longevity_chance"),
        "reproduction_count": record.get("reproduction_count"),
        "cohesion": record.get("cohesion"),
        "dependence": record.get("dependence"),
        "micro_fitness": record.get("micro_fitness"),
        "interactivityType": genome.get("interactivityType"),
        "learningResourceType": genome.get("learningResourceType"),
        "interactivityLevel": genome.get("interactivityLevel"),
        "semanticDensity": genome.get("semanticDensity"),
        "intendedEndUserRole": genome.get("intendedEndUserRole"),
        "context": genome.get("context"),
        "typicalAgeRange": genome.get("typicalAgeRange"),
        "difficulty": genome.get("difficulty"),
        "typicalLearningTime": genome.get("typicalLearningTime"),
        "description": genome.get("description"),
        "language": genome.get("language"),
        "keywords": "|".join(genome.get("keywords") or []),
        "genome_hash": canonical_genome_hash(genome),
    }


def write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def lineage_node_rows(archive_records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in archive_records:
        rows.append(
            {
                "individual_id": record.get("individual_id"),
                "generation_created": record.get("generation_created"),
                "created_by": record.get("created_by"),
                "alive": record.get("alive"),
                "micro_fitness": record.get("micro_fitness"),
                "learningResourceType": (record.get("genome") or {}).get("learningResourceType"),
            }
        )
    return sorted(rows, key=lambda row: (int(row["generation_created"] or 0), str(row["individual_id"])))


def lineage_edge_rows(lineage) -> list[dict[str, Any]]:
    event_by_child: dict[str, list[Any]] = defaultdict(list)
    for event in lineage.events:
        for child in event.individual_ids:
            event_by_child[str(child)].append(event)

    rows: list[dict[str, Any]] = []
    for child, parents in sorted(lineage.parents.items()):
        events = event_by_child.get(child, [])
        creation_event = next(
            (
                event
                for event in events
                if event.event_type
                in {
                    "mutation",
                    "crossover",
                    "fusion_target_created",
                    "defusion_targets_created",
                    "composition",
                    "decomposition",
                }
            ),
            events[0] if events else None,
        )
        for parent in parents:
            rows.append(
                {
                    "parent_id": parent,
                    "child_id": child,
                    "generation": None if creation_event is None else creation_event.generation,
                    "event_type": None if creation_event is None else creation_event.event_type,
                    "event_id": None if creation_event is None else creation_event.event_id,
                }
            )
    return rows


def write_graphml(path: Path, node_rows: Sequence[dict[str, Any]], edge_rows: Sequence[dict[str, Any]]) -> None:
    """Write a small dependency-free GraphML representation of lineage."""

    import xml.etree.ElementTree as ET

    graphml = ET.Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")
    ET.SubElement(graphml, "key", id="generation", **{"for": "node", "attr.name": "generation", "attr.type": "int"})
    ET.SubElement(graphml, "key", id="created_by", **{"for": "node", "attr.name": "created_by", "attr.type": "string"})
    ET.SubElement(graphml, "key", id="operator", **{"for": "edge", "attr.name": "operator", "attr.type": "string"})
    graph = ET.SubElement(graphml, "graph", edgedefault="directed")
    for row in node_rows:
        node = ET.SubElement(graph, "node", id=str(row["individual_id"]))
        ET.SubElement(node, "data", key="generation").text = str(row.get("generation_created") or 0)
        ET.SubElement(node, "data", key="created_by").text = str(row.get("created_by") or "")
    for index, row in enumerate(edge_rows, start=1):
        edge = ET.SubElement(
            graph,
            "edge",
            id=f"e{index}",
            source=str(row["parent_id"]),
            target=str(row["child_id"]),
        )
        ET.SubElement(edge, "data", key="operator").text = str(row.get("event_type") or "")
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(graphml).write(path, encoding="utf-8", xml_declaration=True)


__all__ = [
    "canonical_genome_hash",
    "build_genome_library",
    "flatten_individual",
    "write_csv",
    "lineage_node_rows",
    "lineage_edge_rows",
    "write_graphml",
]
