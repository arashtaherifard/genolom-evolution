from __future__ import annotations

"""Provider-independent factual judging and deterministic claim extraction."""

from dataclasses import dataclass, field
from typing import Any, Protocol
import json
import re

from .generator import LocalTextModelBackend
from .grounding import GroundingContext
from .prompts import (
    DEFAULT_PROMPT_REGISTRY,
    GENOLOM_CLAIM_JUDGE_V1,
    PromptRegistry,
)

SUPPORTED = "SUPPORTED"
UNSUPPORTED = "UNSUPPORTED"
CONTRADICTED = "CONTRADICTED"
UNCERTAIN = "UNCERTAIN"
CLAIM_LABELS = (SUPPORTED, UNSUPPORTED, CONTRADICTED, UNCERTAIN)

ENTAILMENT = "ENTAILMENT"
CONTRADICTION = "CONTRADICTION"
NEUTRAL = "NEUTRAL"
NLI_LABELS = (ENTAILMENT, CONTRADICTION, NEUTRAL)


@dataclass(frozen=True, slots=True)
class ClaimUnit:
    claim_id: str
    text: str

    def to_dict(self) -> dict[str, str]:
        return {"claim_id": self.claim_id, "text": self.text}


class DeterministicClaimExtractor:
    """V1 deterministic sentence/simple-clause claim segmentation.

    Questions are not treated as factual assertions. This is deliberately a
    simple reproducible implementation; it can later be swapped for deterministic
    spaCy segmentation without changing the validation interface.
    """

    def extract(self, content: str) -> tuple[ClaimUnit, ...]:
        sentences = [
            part.strip()
            for part in re.split(r"(?<=[.!?])\s+|\n+", content)
            if part.strip()
        ]
        claims: list[ClaimUnit] = []
        for sentence in sentences:
            if sentence.endswith("?"):
                continue
            clauses = [part.strip() for part in re.split(r"\s*;\s*", sentence) if part.strip()]
            for clause in clauses:
                if len(re.findall(r"\b\w+\b", clause)) < 3:
                    continue
                claims.append(ClaimUnit(f"claim_{len(claims)+1:03d}", clause))
        return tuple(claims)


@dataclass(frozen=True, slots=True)
class NLIResult:
    label: str
    score: float | None = None
    model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.label not in NLI_LABELS:
            raise ValueError(f"Invalid NLI label: {self.label!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "score": self.score,
            "model": self.model,
            "metadata": dict(self.metadata),
        }


class NLIAnalyzer(Protocol):
    name: str

    def evaluate(self, evidence: str, claim: str) -> NLIResult: ...


class TopicSimilarityChecker(Protocol):
    name: str

    def score(self, source_content: str, candidate_content: str) -> float: ...


@dataclass(frozen=True, slots=True)
class JudgeRequest:
    candidate_content: str
    grounding_context: GroundingContext
    prompt_template_id: str
    prompt_version: str
    prompt_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_prompt_payload(self) -> dict[str, Any]:
        # Intentionally no target_genome: factual judging is independent of the
        # evolutionary objective.
        return {
            "candidate_content": self.candidate_content,
            "trusted_evidence": self.grounding_context.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class JudgeClaim:
    text: str
    label: str
    rationale: str = ""

    def __post_init__(self) -> None:
        if self.label not in CLAIM_LABELS:
            raise ValueError(f"Invalid factual-support label: {self.label!r}")

    def to_dict(self) -> dict[str, str]:
        return {"text": self.text, "label": self.label, "rationale": self.rationale}


@dataclass(frozen=True, slots=True)
class JudgeResult:
    overall_label: str
    claims: tuple[JudgeClaim, ...]
    provider: str
    model: str
    model_version: str | None = None
    rationale: str = ""
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.overall_label not in CLAIM_LABELS:
            raise ValueError(f"Invalid factual-support label: {self.overall_label!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_label": self.overall_label,
            "claims": [claim.to_dict() for claim in self.claims],
            "provider": self.provider,
            "model": self.model,
            "model_version": self.model_version,
            "rationale": self.rationale,
            "raw_metadata": dict(self.raw_metadata),
        }


class ContentJudge(Protocol):
    name: str

    def judge(self, request: JudgeRequest) -> JudgeResult: ...


class LocalLLMJudge:
    name = "local-llm-independent-claim-judge"

    def __init__(
        self,
        backend: LocalTextModelBackend,
        *,
        prompt_registry: PromptRegistry = DEFAULT_PROMPT_REGISTRY,
    ) -> None:
        self.backend = backend
        self.prompt_registry = prompt_registry

    def judge(self, request: JudgeRequest) -> JudgeResult:
        template = self.prompt_registry.get(GENOLOM_CLAIM_JUDGE_V1)
        if request.prompt_template_id != template.template_id:
            raise ValueError("Claim judging must use the frozen judge prompt.")
        if request.prompt_version != template.version or request.prompt_hash != template.prompt_hash:
            raise ValueError("Claim judge prompt version/hash mismatch.")
        raw = self.backend.complete(template.render(request.to_prompt_payload()), seed=None)
        parsed = json.loads(raw)
        overall = str(parsed.get("overall_label", "UNCERTAIN")).upper()
        claims_payload = parsed.get("claims", [])
        if not isinstance(claims_payload, list):
            raise ValueError("Claim judge 'claims' must be an array.")
        claims = tuple(
            JudgeClaim(
                text=str(item.get("text", "")),
                label=str(item.get("label", "UNCERTAIN")).upper(),
                rationale=str(item.get("rationale", "")),
            )
            for item in claims_payload
            if isinstance(item, dict)
        )
        return JudgeResult(
            overall_label=overall,
            claims=claims,
            provider=getattr(self.backend, "provider_name", "local-llm"),
            model=getattr(self.backend, "model_name", "local-model"),
            model_version=getattr(self.backend, "model_version", None),
            rationale=str(parsed.get("rationale", "")),
            raw_metadata={"target_genome_visible": False},
        )


def build_judge_request(
    candidate_content: str,
    grounding_context: GroundingContext,
    *,
    prompt_registry: PromptRegistry = DEFAULT_PROMPT_REGISTRY,
    metadata: dict[str, Any] | None = None,
) -> JudgeRequest:
    template = prompt_registry.get(GENOLOM_CLAIM_JUDGE_V1)
    return JudgeRequest(
        candidate_content=candidate_content,
        grounding_context=grounding_context,
        prompt_template_id=template.template_id,
        prompt_version=template.version,
        prompt_hash=template.prompt_hash,
        metadata={} if metadata is None else dict(metadata),
    )


__all__ = [
    "SUPPORTED", "UNSUPPORTED", "CONTRADICTED", "UNCERTAIN", "CLAIM_LABELS",
    "ENTAILMENT", "CONTRADICTION", "NEUTRAL", "NLI_LABELS",
    "ClaimUnit", "DeterministicClaimExtractor",
    "NLIResult", "NLIAnalyzer", "TopicSimilarityChecker",
    "JudgeRequest", "JudgeClaim", "JudgeResult", "ContentJudge",
    "LocalLLMJudge", "build_judge_request",
]
