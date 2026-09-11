"""Deterministic test doubles for local/unit tests only.

These are intentionally unsuitable for final paper experiments. They let the
backend and future UI exercise the complete content-operator contract without
requiring network credentials or a particular model provider.
"""
from __future__ import annotations
from .generator import GenerationRequest, GenerationResponse
from .validators import ContentValidationResult


class DeterministicTestGenerator:
    provider_name = "deterministic-test"
    # Explicit M4 compatibility hook. This generator is a unit-test double only;
    # it may exercise orchestration through a proposal-blocked plan so legacy M3
    # state/archival tests remain independent of scientific realization support.
    test_only_allow_blocked_plan = True
    # M5 compatibility hook: when this explicit non-scientific test double is
    # used through ContentOperator.execute(), preserve the pre-M5 operator-level
    # prompt identifier (e.g. elaboration-v1). Scientific/local-LLM execution
    # continues to use the frozen M5 prompt registry IDs.
    test_only_preserve_legacy_operator_prompt_id = True

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        prefix = {
            "abstraction": "[ABSTRACTED] ",
            "elaboration": "[ELABORATED] ",
            "probing": "[PROBING] ",
        }.get(request.operator_name, "[GENERATED] ")
        return GenerationResponse(
            content=prefix + request.source_content,
            provider=self.provider_name,
            model="test-double",
            model_version="1",
            parameters={"seed": request.seed},
            raw_metadata={"not_for_scientific_use": True},
        )


class AcceptingTestValidator:
    name = "accepting-test-validator"

    def validate(self, request: GenerationRequest, response: GenerationResponse) -> ContentValidationResult:
        accepted = bool(response.content.strip())
        return ContentValidationResult(
            accepted=accepted,
            genome_agreement=1.0 if accepted else 0.0,
            faithfulness=1.0 if accepted else 0.0,
            factuality=None,
            reasons=() if accepted else ("empty_content",),
            metadata={
                "not_for_scientific_use": True,
                # Explicit test-double behavior. This is never evidence that a
                # scientific generator really realized its target metadata.
                "test_double_assumes_target_realization": True,
            },
            realized_genome=request.target_genome if accepted else None,
        )

# ---------------------------------------------------------------------------
# M5 deterministic test doubles. None are valid scientific validators/models.
# ---------------------------------------------------------------------------

import json as _json

from .annotation import MetadataAnnotation
from .judging import (
    ENTAILMENT,
    SUPPORTED,
    JudgeResult,
    NLIResult,
)


class RecordingLocalBackend:
    """Scriptable local-backend double that records every rendered prompt."""

    provider_name = "deterministic-local-backend"
    model_name = "scripted-test-model"
    model_version = "1"

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.prompts = []
        self.seeds = []

    def complete(self, prompt: str, *, seed=None) -> str:
        self.prompts.append(prompt)
        self.seeds.append(seed)
        if not self.outputs:
            raise RuntimeError("No scripted backend output remains.")
        output = self.outputs.pop(0)
        return output if isinstance(output, str) else _json.dumps(output)


class DeterministicTestAnnotator:
    name = "deterministic-test-annotator"

    def __init__(self, genome):
        self.genome = genome
        self.requests = []

    def annotate(self, request):
        self.requests.append(request)
        return MetadataAnnotation(
            learningResourceType=self.genome.learningResourceType,
            interactivityType=self.genome.interactivityType,
            interactivityLevel=self.genome.interactivityLevel,
            semanticDensity=self.genome.semanticDensity,
            difficulty=self.genome.difficulty,
            typicalLearningTime=self.genome.typicalLearningTime,
            provider="deterministic-test",
            model="test-annotator",
            raw_metadata={"not_for_scientific_use": True},
        )


class ConstantTopicSimilarity:
    name = "constant-test-topic-similarity"

    def __init__(self, score: float = 1.0):
        self.value = float(score)

    def score(self, source_content: str, candidate_content: str) -> float:
        return self.value


class EntailingTestNLI:
    name = "entailing-test-nli"

    def evaluate(self, evidence: str, claim: str) -> NLIResult:
        return NLIResult(
            label=ENTAILMENT,
            score=1.0,
            model="test-nli",
            metadata={"not_for_scientific_use": True},
        )


class SupportedTestJudge:
    name = "supported-test-judge"

    def __init__(self, label: str = SUPPORTED):
        self.label = label
        self.requests = []

    def judge(self, request):
        self.requests.append(request)
        return JudgeResult(
            overall_label=self.label,
            claims=(),
            provider="deterministic-test",
            model="test-judge",
            raw_metadata={"not_for_scientific_use": True},
        )
