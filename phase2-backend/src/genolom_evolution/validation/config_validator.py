from __future__ import annotations


class ConfigurationError(ValueError):
    pass


def _require_number(value, path: str, *, minimum=None, maximum=None):
    if value is None:
        raise ConfigurationError(f"{path} is required for this operation and is currently null.")
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"{path} must be numeric.") from exc
    if minimum is not None and x < minimum:
        raise ConfigurationError(f"{path} must be >= {minimum}.")
    if maximum is not None and x > maximum:
        raise ConfigurationError(f"{path} must be <= {maximum}.")
    return x


def validate_mutation_runtime_config(config: dict) -> None:
    evolution = config.get("evolution", {})
    _require_number(evolution.get("mutation", {}).get("rate"), "evolution.mutation.rate", minimum=0, maximum=1)


def validate_crossover_runtime_config(config: dict) -> None:
    evolution = config.get("evolution", {})
    _require_number(evolution.get("crossover", {}).get("rate"), "evolution.crossover.rate", minimum=0, maximum=1)
    maturity = evolution.get("maturity_age")
    if maturity is not None and int(maturity) < 0:
        raise ConfigurationError("evolution.maturity_age must be >= 0")


def validate_priority_runtime_config(config: dict) -> None:
    validate_mutation_runtime_config(config)
    validate_crossover_runtime_config(config)


def validate_lifecycle_runtime_config(config: dict) -> None:
    longevity = config.get("evolution", {}).get("longevity", {})
    _require_number(longevity.get("initial_chance"), "evolution.longevity.initial_chance", minimum=0)
    _require_number(longevity.get("reproduction_reward"), "evolution.longevity.reproduction_reward", minimum=0)
    _require_number(longevity.get("inactivity_penalty"), "evolution.longevity.inactivity_penalty", minimum=0)
