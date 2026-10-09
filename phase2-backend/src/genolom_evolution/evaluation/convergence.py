from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True, slots=True)
class ConvergencePolicy:
    """Frozen M7.1 ecosystem-convergence operationalization.

    This criterion is OUR_OPERATIONALIZATION, not a proposal-defined rule.
    All four stability conditions must hold over the same consecutive rolling
    window, at or after ``minimum_generation``.
    """

    enabled: bool = False
    stop_on_convergence: bool = False
    minimum_generation: int = 10
    window_generations: int = 5
    mean_micro_fitness_range_max: float = 0.01
    population_relative_range_max: float = 0.05
    unique_genome_ratio_range_max: float = 0.02
    recall_range_max: float = 0.02

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> "ConvergencePolicy":
        cfg = config.get("evolution", {}).get("convergence", {}) or {}
        policy = cls(
            enabled=bool(cfg.get("enabled", False)),
            stop_on_convergence=bool(cfg.get("stop_on_convergence", False)),
            minimum_generation=int(cfg.get("minimum_generation", 10)),
            window_generations=int(cfg.get("window_generations", cfg.get("window", 5))),
            mean_micro_fitness_range_max=float(
                cfg.get("mean_micro_fitness_range_max", 0.01)
            ),
            population_relative_range_max=float(
                cfg.get("population_relative_range_max", 0.05)
            ),
            unique_genome_ratio_range_max=float(
                cfg.get("unique_genome_ratio_range_max", 0.02)
            ),
            recall_range_max=float(cfg.get("recall_range_max", 0.02)),
        )
        policy.validate()
        return policy

    def validate(self) -> None:
        if self.minimum_generation < 0:
            raise ValueError("convergence.minimum_generation must be >= 0")
        if self.window_generations < 2:
            raise ValueError("convergence.window_generations must be >= 2")
        thresholds = {
            "mean_micro_fitness_range_max": self.mean_micro_fitness_range_max,
            "population_relative_range_max": self.population_relative_range_max,
            "unique_genome_ratio_range_max": self.unique_genome_ratio_range_max,
            "recall_range_max": self.recall_range_max,
        }
        for name, value in thresholds.items():
            if value < 0:
                raise ValueError(f"convergence.{name} must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ConvergenceCheck:
    generation: int
    window_start: int
    window_end: int
    fitness_range: float
    fitness_stable: bool
    population_relative_range: float
    population_stable: bool
    unique_genome_ratio_range: float
    unique_genome_ratio_stable: bool
    recall_range: float
    recall_stable: bool
    converged: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _metric_range(rows: Iterable[Mapping[str, Any]], key: str) -> float:
    values = [float(row[key]) for row in rows]
    return max(values) - min(values)


def evaluate_convergence(
    generation_rows: list[Mapping[str, Any]],
    policy: ConvergencePolicy,
) -> ConvergenceCheck | None:
    """Evaluate the latest completed generation against the frozen policy.

    Returns ``None`` when convergence detection is disabled or there is not yet
    a complete eligible consecutive window.
    """

    if not policy.enabled or not generation_rows:
        return None

    latest_generation = int(generation_rows[-1]["generation"])
    if latest_generation < policy.minimum_generation:
        return None
    if len(generation_rows) < policy.window_generations:
        return None

    window = generation_rows[-policy.window_generations :]
    generations = [int(row["generation"]) for row in window]
    expected = list(
        range(latest_generation - policy.window_generations + 1, latest_generation + 1)
    )
    if generations != expected:
        return None

    fitness_range = _metric_range(window, "mean_micro_fitness")

    populations = [float(row["population_size"]) for row in window]
    population_mean = sum(populations) / len(populations)
    population_relative_range = (
        (max(populations) - min(populations)) / population_mean
        if population_mean
        else float("inf")
    )

    unique_genome_ratio_range = _metric_range(window, "unique_genome_ratio")
    recall_range = _metric_range(window, "recall")

    fitness_stable = fitness_range <= policy.mean_micro_fitness_range_max
    population_stable = (
        population_relative_range <= policy.population_relative_range_max
    )
    unique_stable = (
        unique_genome_ratio_range <= policy.unique_genome_ratio_range_max
    )
    recall_stable = recall_range <= policy.recall_range_max

    return ConvergenceCheck(
        generation=latest_generation,
        window_start=expected[0],
        window_end=expected[-1],
        fitness_range=fitness_range,
        fitness_stable=fitness_stable,
        population_relative_range=population_relative_range,
        population_stable=population_stable,
        unique_genome_ratio_range=unique_genome_ratio_range,
        unique_genome_ratio_stable=unique_stable,
        recall_range=recall_range,
        recall_stable=recall_stable,
        converged=(
            fitness_stable
            and population_stable
            and unique_stable
            and recall_stable
        ),
    )


__all__ = ["ConvergencePolicy", "ConvergenceCheck", "evaluate_convergence"]
