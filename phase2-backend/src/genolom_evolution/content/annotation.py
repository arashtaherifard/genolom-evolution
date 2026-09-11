from __future__ import annotations

"""Blind realized-genome annotation and deterministic reconciliation."""

from dataclasses import dataclass, field
from collections import Counter
from typing import Any, Protocol
import json
import re

from ..models.genome import GenoLOMGenome
from .generator import LocalTextModelBackend
from .prompts import (
    DEFAULT_PROMPT_REGISTRY,
    GENOLOM_REALIZED_GENOME_ANNOTATOR_V1,
    PromptRegistry,
)


INTERACTIVITY_TYPES = ("Active", "Expositive", "Mixed")
LEARNING_RESOURCE_TYPES = (
    "Headline", "Narrative Text", "Figure", "Diagram", "Graph", "Table", "Slide",
    "Question", "Exercise", "Problem Statement", "Self-Assessment", "Exam",
    "Experiment", "Simulation", "Video Clip", "Hypertext Document", "Formula",
    "Lecture", "Questionnaire", "Authoring Tool",
)
INTERACTIVITY_LEVELS = ("Very Low", "Low", "Medium", "High", "Very High")
SEMANTIC_DENSITY_LEVELS = ("Very Low", "Low", "Medium", "High", "Very High")
DIFFICULTY_LEVELS = ("Very Easy", "Easy", "Medium", "Difficult", "Very Difficult")


@dataclass(frozen=True, slots=True)
class DeterministicArtifactFeatures:
    language: str
    word_count: int
    sentence_count: int
    question_count: int
    has_question_marker: bool
    interactive_markers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "question_count": self.question_count,
            "has_question_marker": self.has_question_marker,
            "interactive_markers": list(self.interactive_markers),
        }


class DeterministicFeatureExtractor:
    """Objectively checkable text features used before/after blind annotation."""

    _interactive_terms = (
        "click", "drag", "drop", "hotspot", "text input", "navigate", "animation"
    )

    def extract(self, content: str) -> DeterministicArtifactFeatures:
        words = re.findall(r"\b[\w'-]+\b", content, flags=re.UNICODE)
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", content) if part.strip()]
        question_count = content.count("?")
        lower = content.lower()
        markers = tuple(term for term in self._interactive_terms if term in lower)

        alpha = [ch for ch in content if ch.isalpha()]
        if not alpha:
            language = "Unknown"
        else:
            latin = sum(("a" <= ch.lower() <= "z") for ch in alpha)
            language = "English (en)" if latin / len(alpha) >= 0.85 else "Unknown"

        return DeterministicArtifactFeatures(
            language=language,
            word_count=len(words),
            sentence_count=len(sentences),
            question_count=question_count,
            has_question_marker=question_count > 0,
            interactive_markers=markers,
        )


class DeterministicKeywordExtractor:
    """Small reproducible V1 lexical re-extractor; not a CSO replacement."""

    _stop = frozenset(
        "a an the and or but if then to of in on for from with by is are was were be been being "
        "this that these those it its as at into about can may will would should could".split()
    )

    def extract(self, content: str, *, max_keywords: int = 8) -> tuple[str, ...]:
        tokens = [
            token.lower()
            for token in re.findall(r"\b[A-Za-z][A-Za-z0-9'-]{2,}\b", content)
            if token.lower() not in self._stop
        ]
        counts = Counter(tokens)
        return tuple(word for word, _ in counts.most_common(max_keywords))


@dataclass(frozen=True, slots=True)
class AnnotationRequest:
    """Input to the blind annotator.

    Deliberately contains no target_genome and no ContentPlan. This structural
    absence is the primary guard against target leakage.
    """

    candidate_content: str
    source_id: str
    deterministic_features: DeterministicArtifactFeatures
    prompt_template_id: str
    prompt_version: str
    prompt_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_prompt_payload(self) -> dict[str, Any]:
        return {
            "candidate_content": self.candidate_content,
            "source_id": self.source_id,
            "deterministic_features": self.deterministic_features.to_dict(),
            "allowed_vocabulary": {
                "interactivityType": list(INTERACTIVITY_TYPES),
                "learningResourceType": list(LEARNING_RESOURCE_TYPES),
                "interactivityLevel": list(INTERACTIVITY_LEVELS),
                "semanticDensity": list(SEMANTIC_DENSITY_LEVELS),
                "difficulty": list(DIFFICULTY_LEVELS),
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.to_prompt_payload(),
            "prompt_template_id": self.prompt_template_id,
            "prompt_version": self.prompt_version,
            "prompt_hash": self.prompt_hash,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class MetadataAnnotation:
    learningResourceType: str
    interactivityType: str
    interactivityLevel: str
    semanticDensity: str
    difficulty: str
    typicalLearningTime: float
    provider: str
    model: str
    model_version: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "learningResourceType": self.learningResourceType,
            "interactivityType": self.interactivityType,
            "interactivityLevel": self.interactivityLevel,
            "semanticDensity": self.semanticDensity,
            "difficulty": self.difficulty,
            "typicalLearningTime": self.typicalLearningTime,
            "provider": self.provider,
            "model": self.model,
            "model_version": self.model_version,
            "raw_metadata": dict(self.raw_metadata),
        }




def validate_metadata_annotation(annotation: MetadataAnnotation) -> None:
    allowed = {
        "learningResourceType": LEARNING_RESOURCE_TYPES,
        "interactivityType": INTERACTIVITY_TYPES,
        "interactivityLevel": INTERACTIVITY_LEVELS,
        "semanticDensity": SEMANTIC_DENSITY_LEVELS,
        "difficulty": DIFFICULTY_LEVELS,
    }
    for field_name, values in allowed.items():
        value = getattr(annotation, field_name)
        if value not in values:
            raise ValueError(f"Blind annotation value {value!r} is invalid for {field_name}.")
    if float(annotation.typicalLearningTime) < 0:
        raise ValueError("typicalLearningTime must be non-negative.")


class MetadataAnnotator(Protocol):
    name: str

    def annotate(self, request: AnnotationRequest) -> MetadataAnnotation: ...


class LocalLLMAnnotator:
    name = "local-llm-blind-metadata-annotator"

    def __init__(
        self,
        backend: LocalTextModelBackend,
        *,
        prompt_registry: PromptRegistry = DEFAULT_PROMPT_REGISTRY,
    ) -> None:
        self.backend = backend
        self.prompt_registry = prompt_registry

    def annotate(self, request: AnnotationRequest) -> MetadataAnnotation:
        template = self.prompt_registry.get(GENOLOM_REALIZED_GENOME_ANNOTATOR_V1)
        if request.prompt_template_id != template.template_id:
            raise ValueError("Blind annotation must use the frozen annotator prompt.")
        if request.prompt_version != template.version or request.prompt_hash != template.prompt_hash:
            raise ValueError("Blind annotation prompt version/hash mismatch.")

        # AnnotationRequest has no TargetGenome field; this payload cannot leak it.
        raw = self.backend.complete(template.render(request.to_prompt_payload()), seed=None)
        parsed = json.loads(raw)
        required = (
            "learningResourceType", "interactivityType", "interactivityLevel",
            "semanticDensity", "difficulty", "typicalLearningTime",
        )
        missing = [key for key in required if key not in parsed]
        if missing:
            raise ValueError(f"Blind annotation missing fields: {missing}")

        return MetadataAnnotation(
            learningResourceType=str(parsed["learningResourceType"]),
            interactivityType=str(parsed["interactivityType"]),
            interactivityLevel=str(parsed["interactivityLevel"]),
            semanticDensity=str(parsed["semanticDensity"]),
            difficulty=str(parsed["difficulty"]),
            typicalLearningTime=float(parsed["typicalLearningTime"]),
            provider=getattr(self.backend, "provider_name", "local-llm"),
            model=getattr(self.backend, "model_name", "local-model"),
            model_version=getattr(self.backend, "model_version", None),
            raw_metadata={"blind_target_access": False},
        )


def build_blind_annotation_request(
    candidate_content: str,
    *,
    source_id: str,
    feature_extractor: DeterministicFeatureExtractor | None = None,
    prompt_registry: PromptRegistry = DEFAULT_PROMPT_REGISTRY,
) -> AnnotationRequest:
    extractor = feature_extractor or DeterministicFeatureExtractor()
    template = prompt_registry.get(GENOLOM_REALIZED_GENOME_ANNOTATOR_V1)
    return AnnotationRequest(
        candidate_content=candidate_content,
        source_id=source_id,
        deterministic_features=extractor.extract(candidate_content),
        prompt_template_id=template.template_id,
        prompt_version=template.version,
        prompt_hash=template.prompt_hash,
        metadata={"blind_target_access": False},
    )


def reconcile_realized_genome(
    *,
    source_genome: GenoLOMGenome,
    candidate_content: str,
    annotation: MetadataAnnotation,
    deterministic_features: DeterministicArtifactFeatures,
    keyword_extractor: DeterministicKeywordExtractor | None = None,
) -> tuple[GenoLOMGenome, tuple[str, ...]]:
    """Reconcile blind annotation with deterministic/objective observations.

    Deterministic language takes precedence when detectable. Fixed role/context/
    age are carried from the source because M5 has no objective artifact-level
    detector for those metadata fields. Keywords are freshly extracted from the
    candidate rather than copied from the target/source.
    """

    validate_metadata_annotation(annotation)

    conflicts: list[str] = []
    language = source_genome.language
    if deterministic_features.language != "Unknown":
        language = deterministic_features.language
        if language != source_genome.language:
            conflicts.append("language")

    # Objectively detectable question structure can contradict an annotator that
    # labels a simple question as purely narrative. We flag rather than silently
    # rewriting the educational type because compound/question-like artifacts
    # can be more nuanced.
    if (
        deterministic_features.has_question_marker
        and deterministic_features.sentence_count <= max(1, deterministic_features.question_count)
        and annotation.learningResourceType == "Narrative Text"
    ):
        conflicts.append("question_structure_vs_learningResourceType")

    keywords = (keyword_extractor or DeterministicKeywordExtractor()).extract(candidate_content)
    realized = GenoLOMGenome(
        interactivityType=annotation.interactivityType,
        learningResourceType=annotation.learningResourceType,
        interactivityLevel=annotation.interactivityLevel,
        semanticDensity=annotation.semanticDensity,
        intendedEndUserRole=source_genome.intendedEndUserRole,
        context=source_genome.context,
        typicalAgeRange=source_genome.typicalAgeRange,
        difficulty=annotation.difficulty,
        typicalLearningTime=float(annotation.typicalLearningTime),
        # Description is not a controlled M5 acceptance trait. Using the exact
        # artifact text avoids inventing a second unvalidated semantic summary.
        description=candidate_content.strip(),
        language=language,
        keywords=keywords,
    )
    return realized, tuple(conflicts)


__all__ = [
    "INTERACTIVITY_TYPES",
    "LEARNING_RESOURCE_TYPES",
    "INTERACTIVITY_LEVELS",
    "SEMANTIC_DENSITY_LEVELS",
    "DIFFICULTY_LEVELS",
    "DeterministicArtifactFeatures",
    "DeterministicFeatureExtractor",
    "DeterministicKeywordExtractor",
    "AnnotationRequest",
    "MetadataAnnotation",
    "validate_metadata_annotation",
    "MetadataAnnotator",
    "LocalLLMAnnotator",
    "build_blind_annotation_request",
    "reconcile_realized_genome",
]
