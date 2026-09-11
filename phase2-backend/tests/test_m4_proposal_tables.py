from genolom_evolution.content.proposal_rules import (
    APPENDIX_A_CONTENT_OPERATIONS,
    APPENDIX_B_DOCUMENTED_ANOMALIES,
    DEFAULT_PROPOSAL_RULES,
    RULE_PROPOSAL_DEFINED,
    appendix_c_mutation_action,
)


def labels(templates, n=2):
    out = []
    for template in templates:
        if template.uses_n:
            out.append(f"{template.operation}({n})")
        elif template.argument is not None:
            out.append(f"{template.operation}({template.argument})")
        elif template.operation == "Export2HTML":
            out.append("Export2HTML()")
        else:
            out.append(template.operation)
    return tuple(out)


def test_appendix_a_narrative_text_row_is_transcribed():
    row = APPENDIX_A_CONTENT_OPERATIONS["Narrative Text"]
    assert labels(row["ilIncrease"]) == (
        "Add_Actions(Navigation)",
        "Add_Actions(Click)",
        "Add_Actions(Animation)",
        "Add_Actions(Hotspots)",
        "Add_Actions(TextInput)",
    )
    assert labels(row["ilDecrease"]) == ("NOP",)
    assert labels(row["sdDecrease"], n=3) == ("Expand(3)",)
    assert labels(row["sdIncrease"], n=3) == ("Pack(3)",)
    assert labels(row["diffDecrease"], n=3) == ("sdDecrease(3)",)
    assert labels(row["diffIncrease"], n=3) == ("sdIncrease(3)",)


def test_appendix_a_question_asymmetric_animation_entry_is_preserved():
    row = APPENDIX_A_CONTENT_OPERATIONS["Question"]
    assert labels(row["ilDecrease"]) == (
        "Remove_Actions(Adv_Click)",
        "Add_Actions(Animation)",
        "Remove_Actions(Drag&Drop)",
        "Remove_Actions(Adv_Drag&Drop)",
        "Export2HTML()",
    )


def test_appendix_a_hypertext_semantic_decrease_has_expand_and_unpack():
    row = APPENDIX_A_CONTENT_OPERATIONS["Hypertext Document"]
    assert labels(row["sdDecrease"], n=2) == (
        "Expand(2)",
        "Unpack(hints: text, voice, video, animation)",
    )


def test_appendix_b_exercise_rules_are_proposal_defaults():
    rules = DEFAULT_PROPOSAL_RULES
    assert rules.resource_type_rule("Exercise", "Question").operation == "is_Same_as"
    assert rules.resource_type_rule("Exercise", "Diagram").operation == "Drop"
    assert rules.resource_type_rule("Exercise", "Slide").operation == "Converts_to"
    assert rules.resource_type_rule("Exercise", "Narrative Text").operation == "Converts_to"
    assert rules.resource_type_rule("Exercise", "Question").origin == RULE_PROPOSAL_DEFINED


def test_appendix_b_question_rules_are_proposal_defaults():
    rules = DEFAULT_PROPOSAL_RULES
    assert rules.resource_type_rule("Question", "Exercise").operation == "is_Same_as"
    assert rules.resource_type_rule("Question", "Problem Statement").operation == "Drop"
    assert rules.resource_type_rule("Question", "Narrative Text").operation == "Drop"
    assert rules.resource_type_rule("Question", "Video Clip").operation == "Converts_to"


def test_appendix_b_problem_statement_rules_are_proposal_defaults():
    rules = DEFAULT_PROPOSAL_RULES
    assert rules.resource_type_rule("Problem Statement", "Exercise").operation == "is_Same_as"
    assert rules.resource_type_rule("Problem Statement", "Question").operation == "Drop"
    assert rules.resource_type_rule("Problem Statement", "Narrative Text").operation == "Converts_to"
    assert rules.resource_type_rule("Problem Statement", "Hypertext Document").operation == "Converts_to"


def test_appendix_b_index_anomaly_is_documented_but_not_made_a_valid_transition():
    assert {item["source"] for item in APPENDIX_B_DOCUMENTED_ANOMALIES} == {
        "Question",
        "Problem Statement",
    }
    assert all(item["target"] == "Index" for item in APPENDIX_B_DOCUMENTED_ANOMALIES)
    assert DEFAULT_PROPOSAL_RULES.resource_type_rule("Question", "Index") is None
    assert DEFAULT_PROPOSAL_RULES.resource_type_rule("Problem Statement", "Index") is None


def test_appendix_c_action_labels_follow_exact_direction_and_distance():
    assert appendix_c_mutation_action("interactivityLevel", "Very Low", "Very High") == "ilIncrease(4)"
    assert appendix_c_mutation_action("interactivityLevel", "High", "Low") == "ilDecrease(2)"
    assert appendix_c_mutation_action("semanticDensity", "Very High", "Low") == "sdDecrease(3)"
    assert appendix_c_mutation_action("difficulty", "Easy", "Very Difficult") == "diffIncrease(3)"
    assert appendix_c_mutation_action("difficulty", "Medium", "Medium") == "NOP"
