from __future__ import annotations

"""Frozen/versioned prompt specifications for Phase-2 content realization.

These prompts are an implementation operationalization, not text copied from the
proposal.  Their IDs and required roles are frozen by the Team-405 architecture.
Scientific runs refer to a registered prompt by ID/version/hash; callers do not
supply ad-hoc prompt text.
"""

from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Mapping
import json


GENOLOM_CONTENT_GENERATOR_GROUNDED_V1 = "GENOLOM_CONTENT_GENERATOR_GROUNDED_V1"
GENOLOM_CONTENT_GENERATOR_PARAMETRIC_V1 = "GENOLOM_CONTENT_GENERATOR_PARAMETRIC_V1"
GENOLOM_REALIZED_GENOME_ANNOTATOR_V1 = "GENOLOM_REALIZED_GENOME_ANNOTATOR_V1"
GENOLOM_CLAIM_JUDGE_V1 = "GENOLOM_CLAIM_JUDGE_V1"
GENOLOM_CONTENT_REPAIR_V1 = "GENOLOM_CONTENT_REPAIR_V1"
GENOLOM_DIRECT_LLM_BASELINE_V1 = "GENOLOM_DIRECT_LLM_BASELINE_V1"


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    template_id: str
    version: str
    body: str
    purpose: str
    origin: str = "OUR_OPERATIONALIZATION"

    @property
    def prompt_hash(self) -> str:
        return sha256(self.body.encode("utf-8")).hexdigest()

    def render(self, payload: Mapping) -> str:
        # Stable JSON serialization keeps prompt construction reproducible.
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return f"{self.body}\n\nINPUT_JSON:\n{encoded}"

    def to_dict(self) -> dict[str, str]:
        return {
            "prompt_template_id": self.template_id,
            "prompt_version": self.version,
            "prompt_hash": self.prompt_hash,
            "purpose": self.purpose,
            "origin": self.origin,
        }


_GROUNDED = PromptTemplate(
    template_id=GENOLOM_CONTENT_GENERATOR_GROUNDED_V1,
    version="1",
    purpose="grounded_content_realization",
    body=(
        "You are the GenoLOM content realizer. The evolutionary target has already been chosen; "
        "do not change or optimize the target metadata. Execute only the supplied deterministic "
        "ContentPlan. Use only the supplied source content and approved grounding evidence for "
        "factual claims. If the requested realization cannot be supported by that evidence, return "
        "status='impossible' rather than inventing information. Return strict JSON with keys: "
        "status ('ok' or 'impossible'), content (string), added_claims (array; must be empty in "
        "grounded mode), and notes (array)."
    ),
)

_PARAMETRIC = PromptTemplate(
    template_id=GENOLOM_CONTENT_GENERATOR_PARAMETRIC_V1,
    version="1",
    purpose="parametric_content_realization",
    body=(
        "You are the GenoLOM content realizer. The evolutionary target has already been chosen; "
        "do not alter it. Execute only the supplied deterministic ContentPlan. You may use supplied "
        "evidence and well-established model knowledge. Every factual claim introduced beyond the "
        "supplied evidence must be listed verbatim in added_claims. Return strict JSON with keys: "
        "status ('ok' or 'impossible'), content (string), added_claims (array), and notes (array)."
    ),
)

_ANNOTATOR = PromptTemplate(
    template_id=GENOLOM_REALIZED_GENOME_ANNOTATOR_V1,
    version="1",
    purpose="blind_realized_genome_annotation",
    body=(
        "Act as a blind educational-metadata annotator. Classify only the candidate artifact that "
        "you are shown. You are not given, and must not infer from hidden intent, any target genome. "
        "Return strict JSON with exactly these educational fields: learningResourceType, "
        "interactivityType, interactivityLevel, semanticDensity, difficulty, "
        "typicalLearningTime. Use only the GenoLOM/IEEE-LOM vocabulary supplied in the input."
    ),
)

_JUDGE = PromptTemplate(
    template_id=GENOLOM_CLAIM_JUDGE_V1,
    version="1",
    purpose="independent_factual_support_judging",
    body=(
        "Judge factual support only. Compare the candidate educational content against the trusted "
        "evidence. Do not judge whether it matches an evolutionary target. Independently identify "
        "factual claims and label support using only SUPPORTED, UNSUPPORTED, CONTRADICTED, or "
        "UNCERTAIN. Return strict JSON with keys overall_label, claims, and rationale."
    ),
)

_REPAIR = PromptTemplate(
    template_id=GENOLOM_CONTENT_REPAIR_V1,
    version="1",
    purpose="structured_content_repair",
    body=(
        "Repair the previous GenoLOM candidate using only the supplied structured validator "
        "failures. Preserve properties that did not fail. The target genome and deterministic "
        "ContentPlan are fixed and must not be changed. In grounded mode use only approved evidence; "
        "if repair is impossible, return status='impossible'. Return the same strict JSON schema as "
        "the content generator: status, content, added_claims, notes."
    ),
)

_DIRECT = PromptTemplate(
    template_id=GENOLOM_DIRECT_LLM_BASELINE_V1,
    version="1",
    purpose="direct_llm_baseline",
    body=(
        "Generate a diverse educational variant directly from the supplied trusted source material. "
        "This is the Direct-LLM baseline: no evolutionary target genome or evolutionary trajectory "
        "is available. Return strict JSON with status, content, added_claims, and notes."
    ),
)


class PromptRegistry:
    def __init__(self, templates: tuple[PromptTemplate, ...]):
        by_id = {template.template_id: template for template in templates}
        if len(by_id) != len(templates):
            raise ValueError("Prompt template IDs must be unique.")
        self._templates = MappingProxyType(by_id)

    def get(self, template_id: str) -> PromptTemplate:
        try:
            return self._templates[template_id]
        except KeyError as exc:
            raise KeyError(f"Unknown frozen prompt template: {template_id!r}") from exc

    def to_dict(self) -> dict[str, dict[str, str]]:
        return {key: value.to_dict() for key, value in self._templates.items()}


DEFAULT_PROMPT_REGISTRY = PromptRegistry(
    (_GROUNDED, _PARAMETRIC, _ANNOTATOR, _JUDGE, _REPAIR, _DIRECT)
)


def generation_prompt_id(grounding_mode: str) -> str:
    if grounding_mode == "grounded":
        return GENOLOM_CONTENT_GENERATOR_GROUNDED_V1
    if grounding_mode == "parametric":
        return GENOLOM_CONTENT_GENERATOR_PARAMETRIC_V1
    raise ValueError(f"Unsupported grounding mode: {grounding_mode!r}")


__all__ = [
    "PromptTemplate",
    "PromptRegistry",
    "DEFAULT_PROMPT_REGISTRY",
    "generation_prompt_id",
    "GENOLOM_CONTENT_GENERATOR_GROUNDED_V1",
    "GENOLOM_CONTENT_GENERATOR_PARAMETRIC_V1",
    "GENOLOM_REALIZED_GENOME_ANNOTATOR_V1",
    "GENOLOM_CLAIM_JUDGE_V1",
    "GENOLOM_CONTENT_REPAIR_V1",
    "GENOLOM_DIRECT_LLM_BASELINE_V1",
]
