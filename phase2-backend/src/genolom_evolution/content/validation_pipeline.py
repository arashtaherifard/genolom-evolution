from __future__ import annotations

"""Frozen M5 validation gates for realized educational content.

The pipeline follows the project order:
1 hard deterministic rules -> 2 blind realized-genome inference ->
3 target/realized agreement -> 4 topic similarity -> 5 NLI ->
6 independent factual judge -> accept/retry/reject.

Scores are never collapsed into an unexplained weighted average.
"""

from dataclasses import dataclass
from typing import Any

from .annotation import (
    DeterministicFeatureExtractor,
    DeterministicKeywordExtractor,
    MetadataAnnotator,
    build_blind_annotation_request,
    reconcile_realized_genome,
)
from .generator import GenerationRequest, GenerationResponse
from .judging import (
    CONTRADICTED,
    CONTRADICTION,
    ENTAILMENT,
    NEUTRAL,
    SUPPORTED,
    UNCERTAIN,
    UNSUPPORTED,
    ContentJudge,
    DeterministicClaimExtractor,
    NLIAnalyzer,
    TopicSimilarityChecker,
    build_judge_request,
)
from .planning import (
    FIXED_TRAITS,
    target_realized_direction_mismatches,
    target_realized_mismatches,
)
from .validators import ContentValidationResult


@dataclass(frozen=True, slots=True)
class TopicSimilarityCalibration:
    """A frozen threshold chosen on a pilot set, never on final results."""

    threshold: float
    pilot_set_id: str
    method: str = "pilot_topic_preserving_vs_drifted_pairs"
    frozen: bool = True

    def __post_init__(self) -> None:
        if not (-1.0 <= float(self.threshold) <= 1.0):
            raise ValueError("Topic similarity threshold must be in [-1, 1].")
        if not self.pilot_set_id.strip():
            raise ValueError("pilot_set_id is required for calibrated scientific validation.")
        if not self.frozen:
            raise ValueError("Scientific topic calibration must be frozen before final experiments.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold": float(self.threshold),
            "pilot_set_id": self.pilot_set_id,
            "method": self.method,
            "frozen": self.frozen,
        }


class ScientificContentValidator:
    """Provider-independent gating validator for the primary grounded V1 mode."""

    name = "m5-scientific-content-validator"

    def __init__(
        self,
        *,
        annotator: MetadataAnnotator,
        topic_similarity: TopicSimilarityChecker,
        topic_calibration: TopicSimilarityCalibration,
        nli_analyzer: NLIAnalyzer,
        independent_judge: ContentJudge,
        self_judge: ContentJudge | None = None,
        feature_extractor: DeterministicFeatureExtractor | None = None,
        keyword_extractor: DeterministicKeywordExtractor | None = None,
        claim_extractor: DeterministicClaimExtractor | None = None,
    ) -> None:
        self.annotator = annotator
        self.topic_similarity = topic_similarity
        self.topic_calibration = topic_calibration
        self.nli_analyzer = nli_analyzer
        self.independent_judge = independent_judge
        self.self_judge = self_judge
        self.feature_extractor = feature_extractor or DeterministicFeatureExtractor()
        self.keyword_extractor = keyword_extractor or DeterministicKeywordExtractor()
        self.claim_extractor = claim_extractor or DeterministicClaimExtractor()

    @staticmethod
    def _failure(code: str, stage: str, **details: Any) -> dict[str, Any]:
        return {"code": code, "stage": stage, **details}

    @staticmethod
    def _evidence_texts(request: GenerationRequest) -> tuple[str, ...]:
        if request.grounding_context is None:
            return ()
        return tuple(item.text for item in request.grounding_context.evidence if item.text.strip())

    def validate(
        self,
        request: GenerationRequest,
        response: GenerationResponse,
    ) -> ContentValidationResult:
        failures: list[dict[str, Any]] = []
        metadata: dict[str, Any] = {
            "pipeline_version": "m5-v1",
            "gating_strategy": "ordered_gates_no_weighted_average",
            "topic_calibration": self.topic_calibration.to_dict(),
        }

        # 1. Hard deterministic rules.
        status = str(getattr(response, "status", "ok")).lower()
        if status == "impossible":
            failures.append(self._failure("generator_impossible", "hard_rules"))
            return self._result(
                accepted=False,
                realized=None,
                failures=failures,
                metadata={**metadata, "terminal_impossible": True},
                retryable=False,
            )
        if status != "ok":
            failures.append(self._failure("malformed_structured_output", "hard_rules", status=status))
        if not response.content.strip():
            failures.append(self._failure("empty_output", "hard_rules"))
        if request.content_plan is not None and not request.content_plan.executable:
            failures.append(self._failure("planning_not_executable", "hard_rules"))
        if request.grounding_context is None:
            failures.append(self._failure("missing_grounding_context", "hard_rules"))
        elif request.grounding_context.mode == "grounded" and response.added_claims:
            failures.append(
                self._failure(
                    "grounded_mode_added_claims_forbidden",
                    "hard_rules",
                    count=len(response.added_claims),
                )
            )
        elif request.grounding_context.mode == "parametric" and response.added_claims:
            # Parametric/free-memory mode is a secondary scenario. Until an
            # external support source is frozen, added claims are not silently
            # accepted as factual merely because the generator listed them.
            failures.append(
                self._failure(
                    "parametric_added_claims_require_external_validation",
                    "hard_rules",
                    count=len(response.added_claims),
                )
            )

        if failures:
            return self._result(
                accepted=False,
                realized=None,
                failures=failures,
                metadata=metadata,
                retryable=True,
            )

        # 2. Blind realized-genome inference. TargetGenome is structurally absent
        # from AnnotationRequest.
        source_id = str(request.metadata.get("source_individual_id", "unknown"))
        annotation_request = build_blind_annotation_request(
            response.content,
            source_id=source_id,
            feature_extractor=self.feature_extractor,
        )
        try:
            annotation = self.annotator.annotate(annotation_request)
            source_genome = request.source_genome
            if source_genome is None:
                raise ValueError("source_genome is required for realized-genome reconciliation")
            realized, reconciliation_conflicts = reconcile_realized_genome(
                source_genome=source_genome,
                candidate_content=response.content,
                annotation=annotation,
                deterministic_features=annotation_request.deterministic_features,
                keyword_extractor=self.keyword_extractor,
            )
        except Exception as exc:
            failures.append(
                self._failure(
                    "realized_genome_inference_failed",
                    "realized_genome",
                    error_type=type(exc).__name__,
                )
            )
            return self._result(
                accepted=False,
                realized=None,
                failures=failures,
                metadata=metadata,
                retryable=True,
            )

        metadata["blind_annotation"] = annotation.to_dict()
        metadata["annotation_request"] = annotation_request.to_dict()
        metadata["deterministic_features"] = annotation_request.deterministic_features.to_dict()
        metadata["reconciliation_conflicts"] = list(reconciliation_conflicts)
        for conflict in reconciliation_conflicts:
            failures.append(
                self._failure(
                    f"deterministic_reconciliation_conflict:{conflict}",
                    "realized_genome",
                )
            )

        # 3. Target <-> Realized agreement. Only controlled categorical/ordinal
        # traits exact-match; fixed traits always remain fixed; learning time is
        # directional rather than exact.
        controlled = () if request.content_plan is None else request.content_plan.controlled_traits
        mismatches = target_realized_mismatches(
            request.target_genome,
            realized,
            controlled_traits=controlled,
        )
        for field in mismatches:
            failures.append(
                self._failure(
                    f"target_realized_mismatch:{field}",
                    "target_realized_agreement",
                    field=field,
                )
            )
        if request.content_plan is not None:
            direction_mismatches = target_realized_direction_mismatches(
                request.content_plan, realized
            )
            for field in direction_mismatches:
                failures.append(
                    self._failure(
                        f"target_realized_direction_mismatch:{field}",
                        "target_realized_agreement",
                        field=field,
                    )
                )
        checked = tuple(dict.fromkeys((*controlled, *FIXED_TRAITS)))
        match_count = sum(
            getattr(request.target_genome, field) == getattr(realized, field)
            for field in checked
        )
        genome_agreement = 1.0 if not checked else match_count / len(checked)

        # 4. Semantic topic similarity using a threshold frozen on pilot data.
        topic_score = float(
            self.topic_similarity.score(request.source_content, response.content)
        )
        metadata["topic_similarity"] = {
            "score": topic_score,
            "checker": getattr(self.topic_similarity, "name", type(self.topic_similarity).__name__),
        }
        if topic_score < self.topic_calibration.threshold:
            failures.append(
                self._failure(
                    "topic_drift",
                    "topic_similarity",
                    score=topic_score,
                    threshold=self.topic_calibration.threshold,
                )
            )

        # 5. Deterministically extracted claim units -> NLI against trusted
        # evidence. The independent LLM is not allowed to define these NLI units.
        claims = self.claim_extractor.extract(response.content)
        evidence_texts = self._evidence_texts(request)
        nli_records: list[dict[str, Any]] = []
        aggregate_nli_labels: list[str] = []
        for claim in claims:
            per_evidence = [
                self.nli_analyzer.evaluate(evidence, claim.text)
                for evidence in evidence_texts
            ]
            labels = [item.label for item in per_evidence]
            if CONTRADICTION in labels:
                aggregate = CONTRADICTION
            elif ENTAILMENT in labels:
                aggregate = ENTAILMENT
            else:
                aggregate = NEUTRAL
            aggregate_nli_labels.append(aggregate)
            nli_records.append(
                {
                    "claim": claim.to_dict(),
                    "aggregate_label": aggregate,
                    "evidence_results": [item.to_dict() for item in per_evidence],
                }
            )
            if aggregate == CONTRADICTION:
                failures.append(
                    self._failure(
                        "nli_contradiction",
                        "nli",
                        claim_id=claim.claim_id,
                    )
                )
            elif aggregate == NEUTRAL:
                failures.append(
                    self._failure(
                        "nli_uncertain",
                        "nli",
                        claim_id=claim.claim_id,
                    )
                )
        metadata["nli"] = nli_records
        metadata["claim_extraction"] = [claim.to_dict() for claim in claims]

        # 6. Independent factual judge. It sees candidate + evidence, not target.
        judge_request = build_judge_request(
            response.content,
            request.grounding_context,
            metadata={"role": "independent_acceptance_judge"},
        )
        try:
            judge_result = self.independent_judge.judge(judge_request)
        except Exception as exc:
            failures.append(
                self._failure(
                    "independent_judge_failed",
                    "independent_judge",
                    error_type=type(exc).__name__,
                )
            )
            judge_result = None
        if judge_result is not None:
            metadata["independent_judge"] = judge_result.to_dict()
            if judge_result.overall_label == CONTRADICTED:
                failures.append(self._failure("judge_contradiction", "independent_judge"))
            elif judge_result.overall_label == UNSUPPORTED:
                failures.append(self._failure("judge_unsupported", "independent_judge"))
            elif judge_result.overall_label == UNCERTAIN:
                failures.append(self._failure("judge_uncertain", "independent_judge"))

        # Same-model/self judge is a metric only; it can never add an acceptance
        # failure. This preserves the frozen independence rule.
        if self.self_judge is not None:
            try:
                self_result = self.self_judge.judge(
                    build_judge_request(
                        response.content,
                        request.grounding_context,
                        metadata={"role": "self_judge_diagnostic_only"},
                    )
                )
                metadata["self_judge_diagnostic"] = self_result.to_dict()
            except Exception as exc:
                metadata["self_judge_diagnostic"] = {
                    "error_type": type(exc).__name__,
                    "acceptance_effect": "none",
                }

        accepted = not failures
        factuality = None
        if judge_result is not None:
            factuality = float(
                judge_result.overall_label == SUPPORTED
                and all(label == ENTAILMENT for label in aggregate_nli_labels)
            )
            # A claim-free artifact can still be judged supported; there are no
            # NLI claim units to contradict that result.
            if not aggregate_nli_labels and judge_result.overall_label == SUPPORTED:
                factuality = 1.0

        return self._result(
            accepted=accepted,
            realized=realized,
            failures=failures,
            metadata=metadata,
            retryable=not accepted,
            genome_agreement=genome_agreement,
            faithfulness=topic_score,
            factuality=factuality,
        )

    @staticmethod
    def _result(
        *,
        accepted: bool,
        realized,
        failures: list[dict[str, Any]],
        metadata: dict[str, Any],
        retryable: bool,
        genome_agreement: float | None = None,
        faithfulness: float | None = None,
        factuality: float | None = None,
    ) -> ContentValidationResult:
        reasons = tuple(item["code"] for item in failures)
        hallucination_flags = tuple(
            code
            for code in reasons
            if code.startswith("nli_")
            or code.startswith("judge_")
            or "added_claims" in code
        )
        return ContentValidationResult(
            accepted=accepted,
            genome_agreement=genome_agreement,
            faithfulness=faithfulness,
            factuality=factuality,
            hallucination_flags=hallucination_flags,
            reasons=reasons,
            metadata=metadata,
            realized_genome=realized,
            retryable=retryable,
            failure_details=tuple(failures),
        )


__all__ = ["TopicSimilarityCalibration", "ScientificContentValidator"]
