from __future__ import annotations

"""Lazy adapters for the frozen initial local validation models.

No model weights are downloaded or imported at module import time. Scientific
runs instantiate these adapters explicitly. This keeps unit tests and UI/backend
imports lightweight while preserving the frozen local-model choices.
"""

import math
from typing import Any

from .judging import (
    CONTRADICTION,
    ENTAILMENT,
    NEUTRAL,
    NLIResult,
)


MPNET_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
DEBERTA_NLI_MODEL_NAME = "cross-encoder/nli-deberta-v3-large"


class MPNetTopicSimilarity:
    name = "mpnet-topic-similarity"

    def __init__(self, model: Any | None = None, *, model_name: str = MPNET_MODEL_NAME):
        self.model_name = model_name
        self._model = model

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "MPNetTopicSimilarity requires the optional 'sentence-transformers' "
                    "package for scientific local validation."
                ) from exc
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @staticmethod
    def _cosine(a, b) -> float:
        # Works for numpy arrays, tensors exposing.tolist(), or Python sequences.
        if hasattr(a, "tolist"):
            a = a.tolist()
        if hasattr(b, "tolist"):
            b = b.tolist()
        dot = sum(float(x) * float(y) for x, y in zip(a, b))
        na = math.sqrt(sum(float(x) ** 2 for x in a))
        nb = math.sqrt(sum(float(y) ** 2 for y in b))
        return 0.0 if na == 0.0 or nb == 0.0 else dot / (na * nb)

    def score(self, source_content: str, candidate_content: str) -> float:
        model = self._load()
        vectors = model.encode([source_content, candidate_content], normalize_embeddings=False)
        return float(self._cosine(vectors[0], vectors[1]))


class DebertaNLIAnalyzer:
    name = "deberta-v3-large-nli"

    def __init__(
        self,
        model: Any | None = None,
        tokenizer: Any | None = None,
        *,
        model_name: str = DEBERTA_NLI_MODEL_NAME,
    ) -> None:
        self.model_name = model_name
        self._model = model
        self._tokenizer = tokenizer

    def _load(self):
        if self._model is None or self._tokenizer is None:
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
            except ImportError as exc:
                raise RuntimeError(
                    "DebertaNLIAnalyzer requires the optional 'transformers' package "
                    "and its local model runtime for scientific validation."
                ) from exc
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        return self._model, self._tokenizer

    @staticmethod
    def _normalize_label(label: str) -> str:
        text = label.upper()
        if "ENTAIL" in text:
            return ENTAILMENT
        if "CONTRAD" in text:
            return CONTRADICTION
        if "NEUTRAL" in text:
            return NEUTRAL
        raise RuntimeError(f"Cannot map NLI model label {label!r} to frozen labels.")

    def evaluate(self, evidence: str, claim: str) -> NLIResult:
        model, tokenizer = self._load()
        inputs = tokenizer(evidence, claim, return_tensors="pt", truncation=True)
        outputs = model(**inputs)
        logits = outputs.logits[0]
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("DebertaNLIAnalyzer requires PyTorch.") from exc
        probs = torch.softmax(logits, dim=-1)
        index = int(torch.argmax(probs).item())
        id2label = getattr(model.config, "id2label", {}) or {}
        raw_label = str(id2label.get(index, f"LABEL_{index}"))
        label = self._normalize_label(raw_label)
        return NLIResult(
            label=label,
            score=float(probs[index].item()),
            model=self.model_name,
            metadata={"raw_label": raw_label},
        )



class TransformersLocalTextBackend:
    """Generic local/open-weight causal-LM backend for M5.

    A concrete model name/path is intentionally supplied by the experiment
    configuration rather than hard-coded here. This keeps the core architecture
    provider-independent and avoids assuming paid API access.
    """

    provider_name = "transformers-local"

    def __init__(
        self,
        model_name_or_path: str,
        *,
        model=None,
        tokenizer=None,
        device: str | None = None,
        max_new_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> None:
        if not model_name_or_path.strip():
            raise ValueError("model_name_or_path is required.")
        self.model_name = model_name_or_path
        self.model_version = None
        self._model = model
        self._tokenizer = tokenizer
        self.device = device
        self.max_new_tokens = int(max_new_tokens)
        self.temperature = float(temperature)

    def _load(self):
        if self._model is None or self._tokenizer is None:
            try:
                from transformers import AutoModelForCausalLM, AutoTokenizer
            except ImportError as exc:
                raise RuntimeError(
                    "TransformersLocalTextBackend requires the optional 'transformers' package."
                ) from exc
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForCausalLM.from_pretrained(self.model_name)
            if self.device is not None and hasattr(self._model, "to"):
                self._model = self._model.to(self.device)
        return self._model, self._tokenizer

    def complete(self, prompt: str, *, seed: int | None = None) -> str:
        model, tokenizer = self._load()
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("TransformersLocalTextBackend requires PyTorch.") from exc
        if seed is not None:
            torch.manual_seed(int(seed))
        inputs = tokenizer(prompt, return_tensors="pt")
        if self.device is not None:
            inputs = {key: value.to(self.device) for key, value in inputs.items()}
        input_length = int(inputs["input_ids"].shape[-1])
        kwargs = {
            "max_new_tokens": self.max_new_tokens,
            "do_sample": self.temperature > 0.0,
        }
        if self.temperature > 0.0:
            kwargs["temperature"] = self.temperature
        outputs = model.generate(**inputs, **kwargs)
        generated = outputs[0][input_length:]
        return tokenizer.decode(generated, skip_special_tokens=True).strip()


__all__ = [
    "MPNET_MODEL_NAME",
    "DEBERTA_NLI_MODEL_NAME",
    "MPNetTopicSimilarity",
    "DebertaNLIAnalyzer",
    "TransformersLocalTextBackend",
]
