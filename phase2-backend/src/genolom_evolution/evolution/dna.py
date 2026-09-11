from __future__ import annotations

"""Proposal-traceable binary DNA encoding used by Milestone 6 Fusion.

Scientific provenance
---------------------
PROPOSAL_DEFINED
    Proposal Table 2 (p. 66): categorical metadata are represented as
    category cells, typicalAgeRange uses a 7-bit binary code (0..120), and
    typicalLearningTime uses a 6-bit binary code (0..45). Description and
    Keywords are free-text rather than binary-coded fields.

OUR_OPERATIONALIZATION
    * Categorical Table-2 cells are encoded one-hot, matching the frozen V1
      Team-405 design.
    * The current Phase-1 protocol stores typicalAgeRange as ``18+``. For the
      fixed Generation-0 protocol we encode its lower bound (18). A decoded 18
      is mapped back to ``18+``; other decoded values remain numeric strings
      and will subsequently fail the fixed-metadata validator.
    * Proposal Table 2 and the Phase-1 annotation vocabulary disagree on a
      small number of learningResourceType labels. V1 therefore uses an
      explicit, logged compatibility adapter at the DNA boundary rather than
      rewriting Generation 0. In particular, ``Question`` is encoded by the
      Table-2 ``Questionnaire`` cell, and ``Headline`` is coarse-grained to
      ``Narrative Text`` following the proposal's Appendix-E Text → Paragraph
      → Headline hierarchy. The original Phase-1 label is not changed.
    * Both the proposal and Phase 1 use MINUTES for typicalLearningTime.
      Table 2 only specifies a 6-bit 0..45 representation and does not state
      how fractional minutes should be encoded. V1 therefore quantizes only
      at the Fusion-DNA boundary to the nearest whole proposal minute, with
      any positive sub-minute duration encoded as 1 minute. The source genome
      retains its original fractional value. This is explicitly
      OUR_OPERATIONALIZATION, not a claim that the proposal specified
      fractional encoding.
"""

from dataclasses import dataclass
from enum import Enum
import re
from typing import Iterable, Mapping

from ..models.genome import GenoLOMGenome


DNA_SCHEMA_VERSION = "proposal-table2-onehot-v1"


# Ordered exactly as represented in proposal Table 2, normalized to the
# canonical title casing used by the current codebase.
TABLE2_CATEGORICAL_VOCABS: dict[str, tuple[str, ...]] = {
    "interactivityType": ("Active", "Expositive", "Mixed"),
    "learningResourceType": (
        "Exercise",
        "Simulation",
        "Questionnaire",
        "Diagram",
        "Figure",
        "Graph",
        "Index",
        "Slide",
        "Table",
        "Narrative Text",
        "Experiment",
        "Problem Statement",
        "Self-Assessment",
        "Lecture",
        "Exam",
        "Authoring Tool",
        "Essay",
        "Video Clip",
        "Hypertext Document",
        "Formula",
        "Hypertext Document with an applet",
    ),
    "interactivityLevel": ("Very Low", "Low", "Medium", "High", "Very High"),
    "semanticDensity": ("Very Low", "Low", "Medium", "High", "Very High"),
    "intendedEndUserRole": ("Teacher", "Author", "Learner", "Manager"),
    "context": ("School", "Higher Education", "Training", "Other"),
    "difficulty": ("Very Easy", "Easy", "Medium", "Difficult", "Very Difficult"),
    # Proposal Table 2 lists language codes. We expose canonical strings to the
    # GenoLOM model while encoding their codes one-hot below.
    "language": (
        "Arabic (ar)",
        "German (de)",
        "English (en)",
        "Spanish (es)",
        "Persian (fa)",
        "French (fr)",
        "Hindi (hi)",
        "Italian (it)",
        "Japanese (ja)",
        "Turkish (tr)",
        "Chinese (zh)",
        "Reserved (Res)",
    ),
}


# Compatibility aliases between the current Phase-1 canonical vocabulary and
# proposal Table 2. These aliases are used ONLY at the Fusion DNA boundary;
# Generation-0 metadata itself remains frozen.
LRT_DNA_ALIASES: dict[str, str] = {
    # Table 2 says Questionnaire, while proposal Appendices B/E and Phase 1 use
    # Question. Treat them as the same proposal DNA cell in V1.
    "Question": "Questionnaire",
    # Headline is absent from Table 2, but Appendix E places Headline under
    # Paragraph under Text. Narrative Text is therefore the closest explicit
    # Table-2 cell. This is a deliberate coarse-graining for Fusion only.
    "Headline": "Narrative Text",
}

# Current-code canonicalization on decode. Table-2 Questionnaire is normalized
# to Question because M4 transition rules and Generation 0 use Question.
TABLE2_LRT_TO_CURRENT: dict[str, str] = {
    "Questionnaire": "Question",
}


_LANGUAGE_ALIASES = {
    "ar": "Arabic (ar)",
    "de": "German (de)",
    "en": "English (en)",
    "es": "Spanish (es)",
    "fa": "Persian (fa)",
    "fr": "French (fr)",
    "hi": "Hindi (hi)",
    "it": "Italian (it)",
    "ja": "Japanese (ja)",
    "tr": "Turkish (tr)",
    "zh": "Chinese (zh)",
    "res": "Reserved (Res)",
}


class FusionBinaryOperator(str, Enum):
    AND = "AND"
    OR = "OR"
    XOR = "XOR"
    NAND = "NAND"

    @classmethod
    def parse(cls, value: str | "FusionBinaryOperator") -> "FusionBinaryOperator":
        if isinstance(value, cls):
            return value
        text = str(value).strip().upper()
        try:
            return cls(text)
        except ValueError as exc:
            raise ValueError(f"Unsupported Fusion binary operator: {value!r}") from exc


@dataclass(frozen=True, slots=True)
class DnaIssue:
    code: str
    field: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "field": self.field, "message": self.message}


@dataclass(frozen=True, slots=True)
class DnaNormalization:
    field: str
    source_value: object
    dna_value: object
    policy: str

    def to_dict(self) -> dict[str, object]:
        return {
            "field": self.field,
            "source_value": self.source_value,
            "dna_value": self.dna_value,
            "policy": self.policy,
        }


@dataclass(frozen=True, slots=True)
class EncodedGenomeDNA:
    schema_version: str
    blocks: tuple[tuple[str, tuple[int, ...]], ...]

    @property
    def bitstring(self) -> str:
        return "".join(str(bit) for _, bits in self.blocks for bit in bits)

    def block_map(self) -> dict[str, tuple[int, ...]]:
        return dict(self.blocks)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "blocks": {name: list(bits) for name, bits in self.blocks},
            "bitstring": self.bitstring,
            "bit_length": len(self.bitstring),
        }


@dataclass(frozen=True, slots=True)
class DnaEncodeResult:
    encoded: EncodedGenomeDNA | None
    issues: tuple[DnaIssue, ...]
    normalizations: tuple[DnaNormalization, ...] = ()

    @property
    def ok(self) -> bool:
        return self.encoded is not None and not self.issues

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "encoded": None if self.encoded is None else self.encoded.to_dict(),
            "issues": [issue.to_dict() for issue in self.issues],
            "normalizations": [item.to_dict() for item in self.normalizations],
        }


@dataclass(frozen=True, slots=True)
class DnaDecodeResult:
    genome: GenoLOMGenome | None
    issues: tuple[DnaIssue, ...]

    @property
    def ok(self) -> bool:
        return self.genome is not None and not self.issues

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "genome": None if self.genome is None else self.genome.to_dict(),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _canonical_language(value: str) -> str | None:
    text = str(value).strip()
    if text in TABLE2_CATEGORICAL_VOCABS["language"]:
        return text
    lower = text.lower()
    if lower in _LANGUAGE_ALIASES:
        return _LANGUAGE_ALIASES[lower]
    match = re.search(r"\(([A-Za-z]+)\)\s*$", text)
    if match:
        return _LANGUAGE_ALIASES.get(match.group(1).lower())
    return None


def _one_hot(value: str, vocabulary: tuple[str, ...]) -> tuple[int, ...] | None:
    try:
        idx = vocabulary.index(value)
    except ValueError:
        return None
    return tuple(1 if i == idx else 0 for i in range(len(vocabulary)))


def _binary_bits(value: int, width: int) -> tuple[int, ...]:
    return tuple(int(ch) for ch in f"{value:0{width}b}")


def _parse_age_lower_bound(value: str) -> int | None:
    text = str(value).strip()
    match = re.fullmatch(r"(\d+)\+?", text)
    if not match:
        return None
    return int(match.group(1))



def _canonical_lrt_for_dna(value: str) -> str | None:
    text = str(value).strip()
    mapped = LRT_DNA_ALIASES.get(text, text)
    if mapped in TABLE2_CATEGORICAL_VOCABS["learningResourceType"]:
        return mapped
    return None


def _quantize_learning_time_minutes(value: float) -> int | None:
    """Map Phase-1 minute estimates to proposal's 6-bit whole-minute DNA.

    The proposal itself uses minutes (Figure 16 shows ``15 Min``) and Table 2
    gives 0..45 in six bits, but does not define fractional encoding. V1 uses
    nearest-minute quantization only at the DNA boundary. Positive sub-minute
    values are represented as one minute so non-empty learning objects do not
    collapse to zero-time solely because of quantization.
    """

    if not 0.0 <= value <= 45.0:
        return None
    if value == 0.0:
        return 0
    # Deterministic round-half-up for non-negative values.
    whole = int(value + 0.5)
    return max(1, min(45, whole))

def encode_genome_dna(genome: GenoLOMGenome) -> DnaEncodeResult:
    issues: list[DnaIssue] = []
    normalizations: list[DnaNormalization] = []
    blocks: list[tuple[str, tuple[int, ...]]] = []

    for field, vocab in TABLE2_CATEGORICAL_VOCABS.items():
        raw = getattr(genome, field)
        if field == "language":
            value = _canonical_language(raw)
        elif field == "learningResourceType":
            value = _canonical_lrt_for_dna(str(raw))
            if value is not None and str(raw) != value:
                normalizations.append(
                    DnaNormalization(
                        field=field,
                        source_value=str(raw),
                        dna_value=value,
                        policy="phase1_to_proposal_table2_lrt_adapter_v1",
                    )
                )
        else:
            value = raw
        bits = None if value is None else _one_hot(str(value), vocab)
        if bits is None:
            issues.append(
                DnaIssue(
                    "unsupported_proposal_dna_value",
                    field,
                    f"{raw!r} is not representable in proposal Table-2 DNA vocabulary.",
                )
            )
        else:
            blocks.append((field, bits))

    age = _parse_age_lower_bound(genome.typicalAgeRange)
    if age is None or not 0 <= age <= 120:
        issues.append(
            DnaIssue(
                "unsupported_age_encoding",
                "typicalAgeRange",
                "Proposal DNA requires an age value in 0..120; current V1 accepts forms such as '18+'.",
            )
        )
    else:
        blocks.append(("typicalAgeRange", _binary_bits(age, 7)))

    learning_time = float(genome.typicalLearningTime)
    encoded_minutes = _quantize_learning_time_minutes(learning_time)
    if encoded_minutes is None:
        issues.append(
            DnaIssue(
                "learning_time_out_of_proposal_range",
                "typicalLearningTime",
                "Proposal Table 2 restricts learning time DNA to 0..45 minutes.",
            )
        )
    else:
        if learning_time != float(encoded_minutes):
            normalizations.append(
                DnaNormalization(
                    field="typicalLearningTime",
                    source_value=learning_time,
                    dna_value=float(encoded_minutes),
                    policy="fractional_minutes_to_nearest_proposal_minute_v1",
                )
            )
        blocks.append(("typicalLearningTime", _binary_bits(encoded_minutes, 6)))

    if issues:
        return DnaEncodeResult(None, tuple(issues), tuple(normalizations))
    return DnaEncodeResult(
        EncodedGenomeDNA(DNA_SCHEMA_VERSION, tuple(blocks)),
        (),
        tuple(normalizations),
    )


def apply_binary_operator(
    a: EncodedGenomeDNA,
    b: EncodedGenomeDNA,
    operator: str | FusionBinaryOperator,
) -> EncodedGenomeDNA:
    op = FusionBinaryOperator.parse(operator)
    if a.schema_version != b.schema_version:
        raise ValueError("Fusion DNA schema versions must match.")
    if tuple(name for name, _ in a.blocks) != tuple(name for name, _ in b.blocks):
        raise ValueError("Fusion DNA block layouts must match.")

    out: list[tuple[str, tuple[int, ...]]] = []
    for (name_a, bits_a), (name_b, bits_b) in zip(a.blocks, b.blocks):
        if name_a != name_b or len(bits_a) != len(bits_b):
            raise ValueError("Fusion DNA block layouts must match.")
        fused: list[int] = []
        for x, y in zip(bits_a, bits_b):
            if op is FusionBinaryOperator.AND:
                bit = x & y
            elif op is FusionBinaryOperator.OR:
                bit = x | y
            elif op is FusionBinaryOperator.XOR:
                bit = x ^ y
            else:
                bit = 1 - (x & y)
            fused.append(bit)
        out.append((name_a, tuple(fused)))
    return EncodedGenomeDNA(a.schema_version, tuple(out))


def _decode_one_hot(field: str, bits: tuple[int, ...]) -> tuple[str | None, DnaIssue | None]:
    vocab = TABLE2_CATEGORICAL_VOCABS[field]
    ones = [i for i, bit in enumerate(bits) if bit == 1]
    if len(bits) != len(vocab) or len(ones) != 1:
        return None, DnaIssue(
            "invalid_one_hot_block",
            field,
            f"Fusion produced {len(ones)} active cells; exactly one is required.",
        )
    return vocab[ones[0]], None


def _bits_to_int(bits: Iterable[int]) -> int:
    return int("".join(str(bit) for bit in bits), 2)


def decode_genome_dna(
    encoded: EncodedGenomeDNA,
    *,
    parent_a: GenoLOMGenome,
    parent_b: GenoLOMGenome,
) -> DnaDecodeResult:
    if encoded.schema_version != DNA_SCHEMA_VERSION:
        return DnaDecodeResult(
            None,
            (DnaIssue("dna_schema_mismatch", "dna", f"Unsupported schema {encoded.schema_version!r}."),),
        )

    block_map = encoded.block_map()
    values: dict[str, object] = {}
    issues: list[DnaIssue] = []
    for field in TABLE2_CATEGORICAL_VOCABS:
        bits = block_map.get(field)
        if bits is None:
            issues.append(DnaIssue("missing_dna_block", field, "DNA block is missing."))
            continue
        value, issue = _decode_one_hot(field, bits)
        if issue is not None:
            issues.append(issue)
        else:
            values[field] = value

    # Normalize the proposal Table-2 token into the canonical vocabulary used
    # by Phase 1 / M4. Preserve Headline when BOTH parents were Headline: the
    # DNA representation deliberately coarse-grains Headline to Narrative Text
    # only for bitwise Fusion and should not force a gratuitous type mutation
    # when both sources had the same more-specific type.
    decoded_lrt = values.get("learningResourceType")
    if isinstance(decoded_lrt, str):
        if (
            decoded_lrt == "Narrative Text"
            and parent_a.learningResourceType == "Headline"
            and parent_b.learningResourceType == "Headline"
        ):
            values["learningResourceType"] = "Headline"
        else:
            values["learningResourceType"] = TABLE2_LRT_TO_CURRENT.get(decoded_lrt, decoded_lrt)

    age_bits = block_map.get("typicalAgeRange")
    if age_bits is None or len(age_bits) != 7:
        issues.append(DnaIssue("missing_dna_block", "typicalAgeRange", "7-bit age block is missing."))
    else:
        age = _bits_to_int(age_bits)
        if not 0 <= age <= 120:
            issues.append(DnaIssue("decoded_age_out_of_range", "typicalAgeRange", f"Decoded age {age} is outside 0..120."))
        else:
            # Frozen Phase-1 metadata uses 18+; other values are left explicit
            # so normal fixed-metadata validation can reject them.
            values["typicalAgeRange"] = "18+" if age == 18 else str(age)

    time_bits = block_map.get("typicalLearningTime")
    if time_bits is None or len(time_bits) != 6:
        issues.append(DnaIssue("missing_dna_block", "typicalLearningTime", "6-bit learning-time block is missing."))
    else:
        learning_time = _bits_to_int(time_bits)
        if not 0 <= learning_time <= 45:
            issues.append(
                DnaIssue(
                    "decoded_learning_time_out_of_range",
                    "typicalLearningTime",
                    f"Decoded learning time {learning_time} is outside proposal range 0..45.",
                )
            )
        else:
            values["typicalLearningTime"] = float(learning_time)

    if issues:
        return DnaDecodeResult(None, tuple(issues))

    # Description and Keywords do not participate in bitwise Fusion. V1 keeps
    # this deterministic and auditable: description is an explicit provenance
    # description and keywords are the stable ordered union of both parents.
    keywords: list[str] = []
    seen: set[str] = set()
    for keyword in (*parent_a.keywords, *parent_b.keywords):
        if keyword not in seen:
            seen.add(keyword)
            keywords.append(keyword)

    genome = GenoLOMGenome(
        interactivityType=str(values["interactivityType"]),
        learningResourceType=str(values["learningResourceType"]),
        interactivityLevel=str(values["interactivityLevel"]),
        semanticDensity=str(values["semanticDensity"]),
        intendedEndUserRole=str(values["intendedEndUserRole"]),
        context=str(values["context"]),
        typicalAgeRange=str(values["typicalAgeRange"]),
        difficulty=str(values["difficulty"]),
        typicalLearningTime=float(values["typicalLearningTime"]),
        description=(
            "Fusion target derived deterministically from two parent GenoLOM genomes; "
            "description itself was excluded from bitwise DNA."
        ),
        language=str(values["language"]),
        keywords=tuple(keywords),
    )
    return DnaDecodeResult(genome, ())


__all__ = [
    "DNA_SCHEMA_VERSION",
    "TABLE2_CATEGORICAL_VOCABS",
    "LRT_DNA_ALIASES",
    "TABLE2_LRT_TO_CURRENT",
    "FusionBinaryOperator",
    "DnaIssue",
    "DnaNormalization",
    "EncodedGenomeDNA",
    "DnaEncodeResult",
    "DnaDecodeResult",
    "encode_genome_dna",
    "apply_binary_operator",
    "decode_genome_dna",
]
