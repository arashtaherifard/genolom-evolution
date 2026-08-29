# Team405 — Phase 1: Chapter 1 Annotation and CSO Classification

This folder contains the corrected, proposal-aligned Phase 1 pipeline for Chapter 1 of the textbook.

Phase 1 has three stages:

1. Segment the chapter into Learning Objects.
2. Annotate each Learning Object with GenoLOM educational metadata.
3. Extract Computer Science Ontology (CSO) topics and ontology depth.

The corrected output contains 298 Learning Objects and is ready to be used as Generation 0 in Phase 2.

## Repository structure

```text
phase1/
├── data/
│   ├── ch01_annotated.xlsx
│   ├── ch01_cso_main.xlsx
│   └── ch01_cso_extended.xlsx
├── source/
│   └── chapter01_source.pdf
├── src/
│   ├── cso_common.py
│   ├── cso_main.py
│   ├── cso_with_extended.py
│   └── validate_phase1.py
├── CHANGELOG.md
├── README.md
└── requirements.txt
```

## File naming

The old filenames were long and difficult to use in a repository. The current names are intentionally short and descriptive.

| Purpose | Current filename |
|---|---|
| Final educational annotation before CSO | `data/ch01_annotated.xlsx` |
| Main/strict CSO output used by Phase 2 | `data/ch01_cso_main.xlsx` |
| CSO output with semantic/enhanced topics | `data/ch01_cso_extended.xlsx` |
| Main/strict CSO script | `src/cso_main.py` |
| Extended CSO script | `src/cso_with_extended.py` |
| Shared CSO + proposal-alignment logic | `src/cso_common.py` |
| Phase-1 validator | `src/validate_phase1.py` |

`cso_main.py` is the default pipeline because Phase 2 uses only direct/syntactic CSO topics. `cso_with_extended.py` is retained for comparison and sensitivity analyses.

Python files use lowercase `snake_case` rather than hyphenated names such as `CSO-main.py`, because snake_case is standard Python naming and allows the files to be imported as modules.

## Proposal-alignment corrections

The Phase-1 metadata has been corrected to match the proposal settings used by this experiment.

### Fixed chapter-level GenoLOM fields

All 298 Learning Objects now use:

```text
intendedEndUserRole = Learner
context = Higher Education
typicalAgeRange = 18+
```

These are treated as fixed experiment-level values rather than independently inferred for each paragraph.

### interactivityType / interactivityLevel constraint

The following proposal relationship is enforced:

```text
Expositive -> Very Low
Mixed      -> Low
Active     -> Medium / High / Very High
```

The previous Phase-1 annotation contained 180 rows that violated this dependency. They were corrected with a minimum-change rule:

```text
Expositive + Low       -> Expositive + Very Low   (57 rows)
Expositive + Medium    -> Expositive + Very Low   (72 rows)
Active + Low           -> Active + Medium         (50 rows)
Mixed + Medium         -> Mixed + Low              (1 row)
```

Already-valid `Active + Medium`, `Active + High`, and `Active + Very High` rows remain unchanged.

### semanticDensity / difficulty validity

The six proposal-defined impossible semantic-density/difficulty combinations are checked by the validator. The current Chapter 1 data contains zero such violations.

### learningResourceType

The Phase-2 issue concerning incomplete proposal transition rules for some `learningResourceType` source values is intentionally **not changed in Phase 1**. It will be handled separately in Phase 2.

## Canonical Phase-1 metadata columns

The cleaned annotation workbook uses the proposal/GenoLOM field names directly:

```text
Paragraph #
Type
Raw Text
Page #
interactivityType
learningResourceType
interactivityLevel
semanticDensity
intendedEndUserRole
context
typicalAgeRange
difficulty
typicalLearningTime
description
language
```

The CSO outputs additionally contain:

```text
keywords
Depth
simple_matches
matched_phrases
```

The extended output also contains:

```text
extended_matches
```

`Depth` is a project-derived ontology field rather than an original GenoLOM gene.

## Annotation rules for future chapters

When annotating new Learning Objects, use the same allowed vocabularies as before, with the following mandatory dependency added to the annotation process:

```text
If interactivityType = Expositive:
    interactivityLevel must be Very Low

If interactivityType = Mixed:
    interactivityLevel must be Low

If interactivityType = Active:
    interactivityLevel must be Medium, High, or Very High
```

This constraint must be applied during annotation so future datasets do not require the same normalization step.

The fixed experiment metadata should also be set to:

```text
intendedEndUserRole = Learner
context = Higher Education
typicalAgeRange = 18+
```

## CSO variants

### `cso_main.py`

This is the main/strict classifier and the output used by Phase 2.

It uses only direct CSO syntactic matches. The final `keywords` field contains at most 7 syntactic topics. It does not create an `extended_matches` column.

Output:

```text
data/ch01_cso_main.xlsx
```

Current Chapter 1 result: 188 of 298 Learning Objects have at least one selected keyword.

### `cso_with_extended.py`

This comparison variant uses syntactic matches first and, when fewer than 7 syntactic topics are available, fills remaining keyword positions with additional semantic/enhanced CSO topics.

Output:

```text
data/ch01_cso_extended.xlsx
```

Current Chapter 1 result: 223 of 298 Learning Objects have at least one selected keyword.

## What `cso_common.py` does

The shared module contains the common implementation used by both CSO variants. It:

- normalizes legacy metadata headers to canonical GenoLOM names;
- enforces the fixed `Learner`, `Higher Education`, and `18+` metadata;
- enforces the proposal relationship between `interactivityType` and `interactivityLevel`;
- removes stale CSO-result columns before a rerun;
- creates the canonical `keywords` and project-derived `Depth` columns;
- runs CSO classification;
- calculates ontology depth from the root topic `computer science`;
- validates proposal constraints before saving the output.

## Environment

Python 3.12 is recommended.

```bash
python3.12 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Run the main Phase-1 classifier

From the Phase-1 project root:

```bash
python src/cso_main.py
```

This reads:

```text
data/ch01_annotated.xlsx
```

and writes:

```text
data/ch01_cso_main.xlsx
```

## Run the extended comparison classifier

```bash
python src/cso_with_extended.py
```

This writes:

```text
data/ch01_cso_extended.xlsx
```

## Validate Phase 1

Run:

```bash
python src/validate_phase1.py
```

The validator checks, without changing the files:

- exactly 298 Learning Objects;
- fixed chapter-level metadata;
- the proposal `interactivityType` / `interactivityLevel` relationship;
- the six impossible `semanticDensity` / `difficulty` combinations;
- absence of `extended_matches` from the main output;
- presence of `extended_matches` in the extended output.

The `learningResourceType` transition-rule issue is deliberately not checked here because it belongs to Phase 2.

## Phase-2 handoff

The canonical Generation-0 source for Phase 2 is:

```text
data/ch01_cso_main.xlsx
```

Use this file rather than the extended CSO output when calculating the Phase-2 Cohesion, Coherence, and Micro Fitness metrics.
