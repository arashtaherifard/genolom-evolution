from copy import deepcopy
from pathlib import Path

from genolom_evolution.config import load_config
from genolom_evolution.evolution.session import PriorityEvolutionSession
from genolom_evolution.experiments.orchestration import run_generations
from genolom_evolution.tracking.run_store import RunStore

ROOT = Path(__file__).resolve().parents[1]


def test_explicit_multi_generation_orchestration_persists_snapshots(
    generation0,
    tmp_path,
):
    population = [deepcopy(x) for x in generation0[:4]]
    config = load_config(ROOT / "configs" / "development.yaml")
    config["evolution"]["maturity_age"] = 0
    session = PriorityEvolutionSession(population, config, seed=23)
    store = RunStore(tmp_path, run_id="m3-run")

    called = []

    def explicit_generation_policy(current_session, generation):
        # No operator schedule is invented by the orchestrator. This test uses
        # an explicit no-op policy to exercise generation transitions only.
        called.append((current_session.generation, generation))

    records = run_generations(
        session,
        generation_count=2,
        generation_step=explicit_generation_policy,
        store=store,
    )

    assert [r.generation for r in records] == [1, 2]
    assert called == [(0, 1), (1, 2)]
    assert len(session.generation_snapshots) == 2
    assert (store.path / "generations" / "generation_0001.json").exists()
    assert (store.path / "generations" / "generation_0002.json").exists()
