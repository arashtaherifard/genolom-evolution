# Paper-Strength Traceability

Frozen backend requirements mapped to the agreed paper-strength items.

- **1 Independent evaluation:** `evaluation/` remains separate from `fitness/`.
- **3 Baselines:** random parent selection is executable alongside fitness-proportionate selection.
- **4 Ablations:** operator/config feature flags remain modular.
- **5 Multiple seeds:** all stochastic priority operators accept controlled RNG/seed state.
- **6 Weight study:** Cohesion/Dependence weights are configurable and scenario-ready.
- **11 Content evaluation:** content generation and validation are separate interfaces; offspring are pending until validated.
- **15 Diversity:** Generation-0 diversity remains measured independently of fitness.
- **16 Micro vs Macro:** individual Micro Fitness and generation-level coverage are separated; later macro Coherency/Precision/Recall/F1 remain modular.
- **17 Statistics:** immutable run outputs and aggregation module remain available.
- **18 Stopping criteria:** config is frozen; full stopping execution belongs to the later multi-generation runner.
- **19 Sensitivity/grid scenarios:** rates, weights, maturity, longevity, thresholds, and seeds are config-driven rather than hard-coded.
- **20 No hand-tuning after final freeze:** default/development/final-protocol separation is preserved.
- **21 Lineage:** Mutation/Crossover/content/lifecycle events now populate executable lineage, not just a schema.
- **22 Reproducibility:** dataset checksum, seed, operator draws, target genomes, repair actions, events, and snapshots are serializable.
- **23 LLM versioning:** generation responses retain provider/model/version/parameters.
- **24 Hallucination/source drift:** validator contract retains faithfulness/factuality/hallucination dimensions.
- **25 LLM not sole judge:** generator and validator are independent dependencies.
- **26 RQs:** provisional RQs are not hard-coded into engine behavior.
- **27 Novelty:** GenoLOM genome, ontology-informed fitness, genetic operators, content operators, lifecycle, and evaluation remain distinct layers.
- **28 Experiment platform:** the priority session is a domain service, not a one-off script.
- **29 Frozen Generation 0:** SHA256 + manifest remain canonical.
- **30 Debug vs scientific outputs:** test doubles are explicitly labeled and final scientific settings are not substituted with development defaults.
