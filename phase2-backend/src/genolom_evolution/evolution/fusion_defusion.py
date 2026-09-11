from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

from ..models.genome import GenoLOMGenome
from ..models.individual import Individual
from ..validation.genome_validator import validate_genome
from .dna import (
    DNA_SCHEMA_VERSION,
    FusionBinaryOperator,
    apply_binary_operator,
    decode_genome_dna,
    encode_genome_dna,
)


@dataclass(frozen=True, slots=True)
class FusionDefusionThreshold:
    """Allowed operation-count interval for Fusion/Defusion history."""

    minimum: int = 0
    maximum: int | None = None

    def __post_init__(self):
        if self.minimum < 0:
            raise ValueError("minimum must be >= 0")
        if self.maximum is not None and self.maximum < self.minimum:
            raise ValueError("maximum must be >= minimum")

    def allows_another(self, count: int) -> bool:
        return self.maximum is None or count < self.maximum

    def meets_minimum(self, count: int) -> bool:
        return count >= self.minimum

    def can_fuse(self, individual: Individual) -> bool:
        return self.allows_another(individual.fusion_count)

    def can_defuse(self, individual: Individual) -> bool:
        return self.allows_another(individual.defusion_count)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FusionResult:
    success: bool
    binary_operator: str
    target_genome: GenoLOMGenome | None
    reasons: tuple[dict[str, Any], ...]
    parent_a_dna: dict[str, Any] | None = None
    parent_b_dna: dict[str, Any] | None = None
    fused_dna: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "binary_operator": self.binary_operator,
            "target_genome": None if self.target_genome is None else self.target_genome.to_dict(),
            "reasons": [dict(x) for x in self.reasons],
            "parent_a_dna": self.parent_a_dna,
            "parent_b_dna": self.parent_b_dna,
            "fused_dna": self.fused_dna,
            "provenance": self.provenance,
        }


@dataclass(frozen=True, slots=True)
class DefusionComponent:
    source_parent_id: str
    target_genome: GenoLOMGenome
    original_content: str
    source_metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_parent_id": self.source_parent_id,
            "target_genome": self.target_genome.to_dict(),
            "original_content": self.original_content,
            "source_metadata": dict(self.source_metadata),
        }


@dataclass(frozen=True, slots=True)
class DefusionResult:
    success: bool
    components: tuple[DefusionComponent, ...]
    reasons: tuple[str, ...]
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "components": [component.to_dict() for component in self.components],
            "reasons": list(self.reasons),
            "provenance": dict(self.provenance),
        }


def record_fusion_participation(individual: Individual, event_id: str, threshold: FusionDefusionThreshold) -> None:
    if not threshold.can_fuse(individual):
        raise ValueError("Fusion threshold does not allow another fusion participation.")
    individual.record_fusion(event_id)


def record_defusion_participation(individual: Individual, event_id: str, threshold: FusionDefusionThreshold) -> None:
    if not threshold.can_defuse(individual):
        raise ValueError("Defusion threshold does not allow another defusion participation.")
    individual.record_defusion(event_id)


def fuse_genomes(
    parent_a: Individual,
    parent_b: Individual,
    *,
    binary_operator: str | FusionBinaryOperator,
) -> FusionResult:
    """Apply proposal binary Fusion to parent GenoLOM DNA.

    Invalid one-hot DNA or a genome that fails ordinary GenoLOM validation is a
    failed Fusion attempt. No LLM repair is performed.
    """

    op = FusionBinaryOperator.parse(binary_operator)
    a_encoded = encode_genome_dna(parent_a.genome)
    b_encoded = encode_genome_dna(parent_b.genome)
    encoding_reasons: list[dict[str, Any]] = []
    for label, result in (("parent_a", a_encoded), ("parent_b", b_encoded)):
        for issue in result.issues:
            item = issue.to_dict()
            item["parent"] = label
            encoding_reasons.append(item)
    if encoding_reasons:
        return FusionResult(False, op.value, None, tuple(encoding_reasons))

    assert a_encoded.encoded is not None and b_encoded.encoded is not None
    fused = apply_binary_operator(a_encoded.encoded, b_encoded.encoded, op)
    decoded = decode_genome_dna(
        fused,
        parent_a=parent_a.genome,
        parent_b=parent_b.genome,
    )
    if not decoded.ok:
        return FusionResult(
            False,
            op.value,
            None,
            tuple(issue.to_dict() for issue in decoded.issues),
            a_encoded.encoded.to_dict(),
            b_encoded.encoded.to_dict(),
            fused.to_dict(),
        )

    assert decoded.genome is not None
    validation_issues = validate_genome(decoded.genome)
    if validation_issues:
        return FusionResult(
            False,
            op.value,
            None,
            tuple(issue.to_dict() for issue in validation_issues),
            a_encoded.encoded.to_dict(),
            b_encoded.encoded.to_dict(),
            fused.to_dict(),
        )

    provenance = {
        "provenance_class": "MIXED_PROPOSAL_AND_OPERATIONALIZATION",
        "dna_schema_version": DNA_SCHEMA_VERSION,
        "proposal_defined": [
            "binary Fusion",
            "AND/OR/XOR/NAND operators",
            "7-bit age",
            "6-bit learning time",
        ],
        "our_operationalization": [
            "one-hot categorical DNA",
            "strict invalid-one-hot rejection",
            "18+ age lower-bound encoding",
            "Phase-1/Table-2 learning-resource-type compatibility adapter",
            "fractional learning time quantized at DNA boundary in minutes",
            "description excluded and replaced by deterministic provenance text",
            "keywords excluded and carried as ordered union",
        ],
        "parent_ids": [parent_a.individual_id, parent_b.individual_id],
        "parent_snapshots": [
            {
                "individual_id": parent_a.individual_id,
                "content": parent_a.content,
                "genome": parent_a.genome.to_dict(),
                "source_type": parent_a.source_type,
                "source_page": parent_a.source_page,
                "source_row_id": parent_a.source_row_id,
            },
            {
                "individual_id": parent_b.individual_id,
                "content": parent_b.content,
                "genome": parent_b.genome.to_dict(),
                "source_type": parent_b.source_type,
                "source_page": parent_b.source_page,
                "source_row_id": parent_b.source_row_id,
            },
        ],
        "excluded_from_bitwise_fusion": ["description", "keywords"],
        "parent_a_dna_normalizations": [x.to_dict() for x in a_encoded.normalizations],
        "parent_b_dna_normalizations": [x.to_dict() for x in b_encoded.normalizations],
    }
    return FusionResult(
        True,
        op.value,
        decoded.genome,
        (),
        a_encoded.encoded.to_dict(),
        b_encoded.encoded.to_dict(),
        fused.to_dict(),
        provenance,
    )


def recover_defusion_components(fused: Individual) -> DefusionResult:
    """Recover component target genomes from stored Fusion provenance.

    The proposal does not define a general invertible Defusion algorithm.
    Team-405 V1 therefore allows Defusion only for fusion-derived artifacts with
    stored parent provenance. This is explicitly OUR_OPERATIONALIZATION.
    """

    if fused.created_by != "fusion":
        return DefusionResult(False, (), ("not_fusion_derived",), {})
    provenance = fused.extra.get("fusion_provenance")
    if not isinstance(provenance, dict):
        return DefusionResult(False, (), ("missing_fusion_provenance",), {})
    snapshots = provenance.get("parent_snapshots")
    if not isinstance(snapshots, list) or len(snapshots) < 2:
        return DefusionResult(False, (), ("incomplete_fusion_parent_provenance",), provenance)

    components: list[DefusionComponent] = []
    for snapshot in snapshots:
        try:
            genome = GenoLOMGenome.from_mapping(dict(snapshot["genome"]))
            source_parent_id = str(snapshot["individual_id"])
            content = str(snapshot["content"])
        except (KeyError, TypeError, ValueError) as exc:
            return DefusionResult(
                False,
                (),
                (f"invalid_fusion_parent_provenance:{exc}",),
                provenance,
            )
        components.append(
            DefusionComponent(
                source_parent_id=source_parent_id,
                target_genome=genome,
                original_content=content,
                source_metadata={
                    "source_type": str(snapshot.get("source_type", "")),
                    "source_page": str(snapshot.get("source_page", "")),
                    "source_row_id": str(snapshot.get("source_row_id", "")),
                },
            )
        )

    return DefusionResult(
        True,
        tuple(components),
        (),
        {
            "provenance_class": "OUR_OPERATIONALIZATION",
            "policy": "recover_stored_fusion_parent_targets_v1",
            "fusion_provenance": provenance,
        },
    )


__all__ = [
    "FusionDefusionThreshold",
    "FusionResult",
    "DefusionComponent",
    "DefusionResult",
    "record_fusion_participation",
    "record_defusion_participation",
    "fuse_genomes",
    "recover_defusion_components",
]
