from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Protocol
import json

from ..models.genome import GenoLOMGenome
from .grounding import GroundingContext
from .planning import ContentPlan
from .prompts import DEFAULT_PROMPT_REGISTRY, PromptRegistry


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    source_content: str
    target_genome: GenoLOMGenome
    operator_name: str
    prompt_template_id: str
    seed: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Appended for backward-compatible positional construction.
    source_genome: GenoLOMGenome | None = None
    content_plan: ContentPlan | None = None
    grounding_context: GroundingContext | None = None

    # M5 reproducibility/retry fields.  These are appended so existing callers
    # that construct GenerationRequest positionally continue to work.
    prompt_version: str | None = None
    prompt_hash: str | None = None
    attempt_index: int = 1
    validator_feedback: tuple[dict[str, Any], ...] = ()
    previous_candidate_content: str | None = None

    def to_prompt_payload(self) -> dict[str, Any]:
        """Return the structured payload visible to a content generator.

        Unlike the blind annotator, the content generator is intentionally
        allowed to see the target: evolution has already decided WHAT and the
        generator performs HOW.
        """
        return {
            "source_content": self.source_content,
            "source_genome": None if self.source_genome is None else self.source_genome.to_dict(),
            "target_genome": self.target_genome.to_dict(),
            "content_plan": None if self.content_plan is None else self.content_plan.to_dict(),
            "grounding_context": None if self.grounding_context is None else self.grounding_context.to_dict(),
            "operator_name": self.operator_name,
            "generation_info": self.metadata.get("generation_info", {}),
            "attempt_index": self.attempt_index,
            "validator_feedback": list(self.validator_feedback),
            "previous_candidate_content": self.previous_candidate_content,
        }


@dataclass(frozen=True, slots=True)
class GenerationResponse:
    content: str
    provider: str
    model: str
    model_version: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    # M5 structured-generation contract; appended for compatibility.
    status: str = "ok"
    added_claims: tuple[str, ...] = ()

    def to_dict(self):
        data = asdict(self)
        data["added_claims"] = list(self.added_claims)
        return data


class ContentGenerator(Protocol):
    provider_name: str

    def generate(self, request: GenerationRequest) -> GenerationResponse: ...


class LocalTextModelBackend(Protocol):
    """Provider-independent local/open-weight text backend.

    The core project does not choose a specific runtime (Transformers, llama.cpp,
    Ollama, vLLM, etc.) at this milestone.  A backend only needs to implement
    this small interface, so no paid API is required or assumed.
    """

    provider_name: str
    model_name: str
    model_version: str | None

    def complete(self, prompt: str, *, seed: int | None = None) -> str: ...


class LocalLLMGenerator:
    provider_name = "local-llm"

    def __init__(
        self,
        backend: LocalTextModelBackend,
        *,
        prompt_registry: PromptRegistry = DEFAULT_PROMPT_REGISTRY,
    ) -> None:
        self.backend = backend
        self.prompt_registry = prompt_registry

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        template = self.prompt_registry.get(request.prompt_template_id)
        if request.prompt_version not in (None, template.version):
            raise ValueError("GenerationRequest prompt_version does not match frozen registry.")
        if request.prompt_hash not in (None, template.prompt_hash):
            raise ValueError("GenerationRequest prompt_hash does not match frozen registry.")

        prompt = template.render(request.to_prompt_payload())
        raw = self.backend.complete(prompt, seed=request.seed)
        try:
            parsed = json.loads(raw)
        except Exception as exc:  # strict JSON is part of the frozen protocol
            return GenerationResponse(
                content="",
                provider=getattr(self.backend, "provider_name", self.provider_name),
                model=getattr(self.backend, "model_name", "local-model"),
                model_version=getattr(self.backend, "model_version", None),
                parameters={"seed": request.seed},
                raw_metadata={
                    "parse_error": type(exc).__name__,
                    "raw_output": raw,
                    "prompt_template_id": template.template_id,
                    "prompt_version": template.version,
                    "prompt_hash": template.prompt_hash,
                },
                status="malformed",
            )

        status = str(parsed.get("status", "malformed")).strip().lower()
        content = str(parsed.get("content", ""))
        claims = parsed.get("added_claims", [])
        if not isinstance(claims, list):
            claims = []
            status = "malformed"

        # Grounded mode cannot silently introduce ungrounded claims.
        if (
            request.grounding_context is not None
            and request.grounding_context.mode == "grounded"
            and claims
        ):
            status = "malformed"

        return GenerationResponse(
            content=content,
            provider=getattr(self.backend, "provider_name", self.provider_name),
            model=getattr(self.backend, "model_name", "local-model"),
            model_version=getattr(self.backend, "model_version", None),
            parameters={"seed": request.seed},
            raw_metadata={
                "prompt_template_id": template.template_id,
                "prompt_version": template.version,
                "prompt_hash": template.prompt_hash,
                "notes": parsed.get("notes", []),
                "structured_output": parsed,
            },
            status=status,
            added_claims=tuple(str(item) for item in claims),
        )



@dataclass(frozen=True, slots=True)
class DirectBaselineRequest:
    source_content: str
    grounding_context: GroundingContext
    prompt_template_id: str
    prompt_version: str
    prompt_hash: str
    seed: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_prompt_payload(self) -> dict[str, Any]:
        # Deliberately no evolutionary TargetGenome.
        return {
            "source_content": self.source_content,
            "grounding_context": self.grounding_context.to_dict(),
            "baseline": "direct_llm_no_evolutionary_target",
        }


class LocalDirectLLMBaselineGenerator:
    provider_name = "local-direct-llm-baseline"

    def __init__(
        self,
        backend: LocalTextModelBackend,
        *,
        prompt_registry: PromptRegistry = DEFAULT_PROMPT_REGISTRY,
    ) -> None:
        self.backend = backend
        self.prompt_registry = prompt_registry

    def generate(self, request: DirectBaselineRequest) -> GenerationResponse:
        from .prompts import GENOLOM_DIRECT_LLM_BASELINE_V1

        template = self.prompt_registry.get(GENOLOM_DIRECT_LLM_BASELINE_V1)
        if request.prompt_template_id != template.template_id:
            raise ValueError("Direct baseline must use the frozen direct-LLM prompt.")
        if request.prompt_version != template.version or request.prompt_hash != template.prompt_hash:
            raise ValueError("Direct baseline prompt version/hash mismatch.")
        raw = self.backend.complete(template.render(request.to_prompt_payload()), seed=request.seed)
        try:
            parsed = json.loads(raw)
        except Exception as exc:
            return GenerationResponse(
                content="",
                provider=getattr(self.backend, "provider_name", self.provider_name),
                model=getattr(self.backend, "model_name", "local-model"),
                model_version=getattr(self.backend, "model_version", None),
                parameters={"seed": request.seed},
                raw_metadata={"parse_error": type(exc).__name__, "raw_output": raw},
                status="malformed",
            )
        claims = parsed.get("added_claims", [])
        if not isinstance(claims, list):
            claims = []
        return GenerationResponse(
            content=str(parsed.get("content", "")),
            provider=getattr(self.backend, "provider_name", self.provider_name),
            model=getattr(self.backend, "model_name", "local-model"),
            model_version=getattr(self.backend, "model_version", None),
            parameters={"seed": request.seed},
            raw_metadata={
                "prompt_template_id": template.template_id,
                "prompt_version": template.version,
                "prompt_hash": template.prompt_hash,
                "baseline": "direct_llm",
            },
            status=str(parsed.get("status", "malformed")).lower(),
            added_claims=tuple(str(item) for item in claims),
        )


def build_direct_baseline_request(
    source_content: str,
    *,
    source_id: str,
    grounding_context: GroundingContext | None = None,
    seed: int | None = None,
    prompt_registry: PromptRegistry = DEFAULT_PROMPT_REGISTRY,
) -> DirectBaselineRequest:
    from .prompts import GENOLOM_DIRECT_LLM_BASELINE_V1

    context = grounding_context or GroundingContext.from_source(source_id, source_content)
    template = prompt_registry.get(GENOLOM_DIRECT_LLM_BASELINE_V1)
    return DirectBaselineRequest(
        source_content=source_content,
        grounding_context=context,
        prompt_template_id=template.template_id,
        prompt_version=template.version,
        prompt_hash=template.prompt_hash,
        seed=seed,
        metadata={"source_id": source_id},
    )


__all__ = [
    "GenerationRequest",
    "GenerationResponse",
    "ContentGenerator",
    "LocalTextModelBackend",
    "LocalLLMGenerator",
    "DirectBaselineRequest",
    "LocalDirectLLMBaselineGenerator",
    "build_direct_baseline_request",
]
