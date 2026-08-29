from .base import BaseContentOperator


class AbstractionOperator(BaseContentOperator):
    name = "abstraction"
    prompt_template_id = "abstraction-v1"
    instruction = (
        "Create a more abstract/concise learning object while preserving the source facts and core concepts. "
        "The result must satisfy the supplied target GenoLOM genome and must not introduce unsupported claims."
    )
