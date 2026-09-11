from .eligibility import EligibilityResult, check_parent_eligibility
from .mutation import MutationResult, MutationOption, mutate_individual, viable_mutation_options
from .crossover import CrossoverResult, crossover_individuals
from .offspring import OffspringIdAllocator, create_offspring
from .lifecycle import (
    LongevityPolicy,
    initialize_longevity,
    age_survivors,
    update_longevity_end_of_generation,
    apply_perish,
)
from .fusion_defusion import (
    FusionDefusionThreshold,
    FusionResult,
    DefusionResult,
    fuse_genomes,
    recover_defusion_components,
)
from .dna import FusionBinaryOperator, encode_genome_dna
from .composition import (
    CompositionResult,
    DecompositionResult,
    compose_individuals,
    recover_composition_components,
)

__all__ = [
    "EligibilityResult",
    "check_parent_eligibility",
    "MutationResult",
    "MutationOption",
    "mutate_individual",
    "viable_mutation_options",
    "CrossoverResult",
    "crossover_individuals",
    "OffspringIdAllocator",
    "create_offspring",
    "LongevityPolicy",
    "initialize_longevity",
    "age_survivors",
    "update_longevity_end_of_generation",
    "apply_perish",
    "FusionDefusionThreshold",
    "FusionResult",
    "DefusionResult",
    "fuse_genomes",
    "recover_defusion_components",
    "FusionBinaryOperator",
    "encode_genome_dna",
    "CompositionResult",
    "DecompositionResult",
    "compose_individuals",
    "recover_composition_components",
    "PriorityEvolutionSession",
    "AppliedOperatorResult",
    "AppliedStructuralOperatorResult",
]


# Importing ``session`` eagerly creates a cycle once M3 content planning imports
# ``evolution.operator_rules``:
#
# content.generator -> content.planning -> evolution package -> session
# -> content.operators -> content.generator
#
# Keep the established public API (``from genolom_evolution.evolution import
# PriorityEvolutionSession``) but resolve these two session-level symbols only
# when a caller actually asks for them.
def __getattr__(name: str):
    if name in {"PriorityEvolutionSession", "AppliedOperatorResult", "AppliedStructuralOperatorResult"}:
        from .session import (
            AppliedOperatorResult,
            AppliedStructuralOperatorResult,
            PriorityEvolutionSession,
        )

        exports = {
            "PriorityEvolutionSession": PriorityEvolutionSession,
            "AppliedOperatorResult": AppliedOperatorResult,
            "AppliedStructuralOperatorResult": AppliedStructuralOperatorResult,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
