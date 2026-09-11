from __future__ import annotations
from dataclasses import dataclass
from ..models.genome import GenoLOMGenome
from ..models.genome_roles import TargetGenome
from ..models.individual import Individual


@dataclass(slots=True)
class OffspringIdAllocator:
    generation: int
    next_index: int = 1

    def next_id(self) -> str:
        value = f"G{self.generation}_LO_{self.next_index:04d}"
        self.next_index += 1
        return value


def create_offspring(
    *,
    allocator: OffspringIdAllocator,
    generation: int,
    parent_ids: tuple[str, ...],
    created_by: str,
    target_genome: GenoLOMGenome,
    content: str,
    content_status: str = "pending_generation",
    source_type: str = "",
    source_page: str = "",
    source_row_id: str = "",
    source_genome: GenoLOMGenome | None = None,
) -> Individual:
    if generation < 1:
        raise ValueError("Offspring generation must be >= 1")

    # ``genome`` remains the currently realized/provisional genome for backward
    # compatibility. A pending child carries its evolutionary intent separately
    # in target_genome and has no realized_genome yet.
    current_genome = source_genome if source_genome is not None else target_genome
    return Individual(
        individual_id=allocator.next_id(),
        content=content,
        genome=current_genome,
        source_type=source_type,
        source_page=source_page,
        source_row_id=source_row_id,
        generation_created=generation,
        parent_ids=tuple(parent_ids),
        created_by=created_by,
        age=0,
        longevity_chance=None,
        alive=True,
        reproduction_count=0,
        content_status=content_status,
        target_genome=TargetGenome(target_genome),
        realized_genome=None,
    )
