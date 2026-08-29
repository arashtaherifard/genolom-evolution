from .base import BaseContentOperator


class ProbingOperator(BaseContentOperator):
    name = "probing"
    prompt_template_id = "probing-v1"
    instruction = (
        "Transform the learning object into a probing educational prompt/question that tests or elicits understanding "
        "of the source concepts. Preserve factual faithfulness and satisfy the supplied target GenoLOM genome."
    )
