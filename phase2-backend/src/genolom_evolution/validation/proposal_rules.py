INTERACTIVITY_TYPES = {"Active", "Expositive", "Mixed"}
INTERACTIVITY_LEVELS = {"Very Low", "Low", "Medium", "High", "Very High"}
SEMANTIC_DENSITIES = {"Very Low", "Low", "Medium", "High", "Very High"}
DIFFICULTIES = {"Very Easy", "Easy", "Medium", "Difficult", "Very Difficult"}

# Vocabulary is retained, but learningResourceType transition coverage is intentionally not solved here.
LEARNING_RESOURCE_TYPES = {
    "Headline", "Narrative Text", "Figure", "Diagram", "Graph", "Table", "Slide",
    "Question", "Exercise", "Problem Statement", "Self-Assessment", "Exam", "Experiment",
    "Simulation", "Video Clip", "Hypertext Document", "Formula", "Lecture", "Questionnaire",
    "Authoring Tool",
}

FIXED_METADATA = {
    "intendedEndUserRole": "Learner",
    "context": "Higher Education",
    "typicalAgeRange": "18+",
}

ALLOWED_INTERACTIVITY_LEVELS = {
    "Expositive": {"Very Low"},
    "Mixed": {"Low"},
    "Active": {"Medium", "High", "Very High"},
}

FORBIDDEN_SEMANTIC_DIFFICULTY = {
    ("Very Low", "Difficult"),
    ("Very Low", "Very Difficult"),
    ("Low", "Very Difficult"),
    ("High", "Very Easy"),
    ("Very High", "Very Easy"),
    ("Very High", "Easy"),
}
