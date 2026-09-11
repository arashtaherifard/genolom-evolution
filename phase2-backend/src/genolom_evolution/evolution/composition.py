from __future__ import annotations

"""Deterministic V1 Composition / Decomposition.

Proposal p. 62 distinguishes Composition from Fusion because parent learning
objects remain independently identifiable in the compound output. It also says
Composition needs layout/morphology fields. The proposal does not fully specify
those fields, so Team-405 V1 uses an auditable structural envelope and does not
rewrite component content.
"""

from dataclasses import dataclass
from typing import Any, Sequence

from ..models.genome import GenoLOMGenome
from ..models.individual import Individual


COMPOUND_FORMAT_VERSION = "genolom-compound-v1"


@dataclass(frozen=True, slots=True)
class CompoundComponent:
    component_id: str
    source_parent_id: str
    order: int
    role: str
    content: str
    genome: GenoLOMGenome
    source_type: str
    source_page: str
    source_row_id: str
    rendered_content_start: int
    rendered_content_end: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "source_parent_id": self.source_parent_id,
            "order": self.order,
            "role": self.role,
            "content": self.content,
            "genome": self.genome.to_dict(),
            "source_type": self.source_type,
            "source_page": self.source_page,
            "source_row_id": self.source_row_id,
            "rendered_content_start": self.rendered_content_start,
            "rendered_content_end": self.rendered_content_end,
        }


@dataclass(frozen=True, slots=True)
class CompositionResult:
    content: str
    components: tuple[CompoundComponent, ...]
    container_genome: GenoLOMGenome
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "components": [component.to_dict() for component in self.components],
            "container_genome": self.container_genome.to_dict(),
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class DecompositionResult:
    success: bool
    components: tuple[CompoundComponent, ...]
    reasons: tuple[str, ...]
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "components": [component.to_dict() for component in self.components],
            "reasons": list(self.reasons),
            "provenance": dict(self.provenance),
        }


def _source_row_number(individual: Individual) -> int | None:
    text = str(individual.source_row_id).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _ordered_parents(parents: Sequence[Individual]) -> tuple[Individual, ...]:
    """Use source order when safely available, otherwise selection order."""

    rows = [_source_row_number(parent) for parent in parents]
    same_source = len({(p.source_type, p.source_page) for p in parents}) == 1
    if same_source and all(row is not None for row in rows):
        return tuple(
            parent
            for _, parent in sorted(
                zip((int(row) for row in rows if row is not None), parents),
                key=lambda item: item[0],
            )
        )
    return tuple(parents)


def compose_individuals(
    parents: Sequence[Individual],
    *,
    roles: Sequence[str] | None = None,
) -> CompositionResult:
    if len(parents) < 2:
        raise ValueError("Composition requires at least two parent learning objects.")
    ids = [parent.individual_id for parent in parents]
    if len(ids) != len(set(ids)):
        raise ValueError("Composition requires distinct parent individuals.")

    ordered = _ordered_parents(parents)
    role_by_id: dict[str, str] = {}
    if roles is not None:
        if len(roles) != len(parents):
            raise ValueError("roles must have the same length as parents.")
        role_by_id = {
            parent.individual_id: str(role).strip() or f"component_{idx + 1}"
            for idx, (parent, role) in enumerate(zip(parents, roles))
        }

    parts: list[str] = [f"[{COMPOUND_FORMAT_VERSION}]\n"]
    components: list[CompoundComponent] = []
    cursor = len(parts[0])
    for index, parent in enumerate(ordered, start=1):
        role = role_by_id.get(parent.individual_id, f"component_{index}")
        header = (
            f'<component id="{parent.individual_id}" order="{index}" role="{role}">\n'
        )
        parts.append(header)
        cursor += len(header)
        start = cursor
        parts.append(parent.content)
        cursor += len(parent.content)
        end = cursor
        footer = "\n</component>\n"
        parts.append(footer)
        cursor += len(footer)
        components.append(
            CompoundComponent(
                component_id=f"component_{index}",
                source_parent_id=parent.individual_id,
                order=index,
                role=role,
                content=parent.content,
                genome=parent.genome,
                source_type=parent.source_type,
                source_page=parent.source_page,
                source_row_id=parent.source_row_id,
                rendered_content_start=start,
                rendered_content_end=end,
            )
        )

    content = "".join(parts)
    # The proposal defines structural composition but not how a compound
    # container gets a single GenoLOM genome. V1 inherits the first ordered
    # component genome solely as an envelope/backward-compatibility field; all
    # component genomes are stored losslessly and macro evaluation can treat the
    # object as compound.
    container_genome = ordered[0].genome
    return CompositionResult(
        content=content,
        components=tuple(components),
        container_genome=container_genome,
        provenance={
            "provenance_class": "MIXED_PROPOSAL_AND_OPERATIONALIZATION",
            "proposal_defined": [
                "multiple LOs form one compound LO",
                "original components remain identifiable",
                "layout/morphology metadata is required",
            ],
            "our_operationalization": [
                "deterministic text structural envelope",
                "source-row ordering only when all parents share a source and numeric row ids",
                "selection order fallback",
                "first ordered component genome used as nonsemantic container envelope",
                "no LLM rewriting",
            ],
            "format_version": COMPOUND_FORMAT_VERSION,
            "parent_ids": [parent.individual_id for parent in ordered],
        },
    )


def recover_composition_components(compound: Individual) -> DecompositionResult:
    if compound.created_by != "composition":
        return DecompositionResult(False, (), ("not_composition_derived",), {})
    payload = compound.extra.get("composition")
    if not isinstance(payload, dict):
        return DecompositionResult(False, (), ("missing_composition_provenance",), {})
    raw_components = payload.get("components")
    if not isinstance(raw_components, list) or not raw_components:
        return DecompositionResult(False, (), ("missing_compound_components",), payload)

    components: list[CompoundComponent] = []
    for raw in raw_components:
        try:
            components.append(
                CompoundComponent(
                    component_id=str(raw["component_id"]),
                    source_parent_id=str(raw["source_parent_id"]),
                    order=int(raw["order"]),
                    role=str(raw["role"]),
                    content=str(raw["content"]),
                    genome=GenoLOMGenome.from_mapping(dict(raw["genome"])),
                    source_type=str(raw.get("source_type", "")),
                    source_page=str(raw.get("source_page", "")),
                    source_row_id=str(raw.get("source_row_id", "")),
                    rendered_content_start=int(raw["rendered_content_start"]),
                    rendered_content_end=int(raw["rendered_content_end"]),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            return DecompositionResult(
                False,
                (),
                (f"invalid_compound_component_provenance:{exc}",),
                payload,
            )

    return DecompositionResult(
        True,
        tuple(sorted(components, key=lambda component: component.order)),
        (),
        {
            "provenance_class": "MIXED_PROPOSAL_AND_OPERATIONALIZATION",
            "proposal_defined": "Decomposition recovers components identifiable in the compound parent.",
            "our_operationalization": "Only stored Composition-V1 boundaries are executable; unstructured multimedia decomposition is deferred.",
            "source_compound_id": compound.individual_id,
        },
    )


__all__ = [
    "COMPOUND_FORMAT_VERSION",
    "CompoundComponent",
    "CompositionResult",
    "DecompositionResult",
    "compose_individuals",
    "recover_composition_components",
]
