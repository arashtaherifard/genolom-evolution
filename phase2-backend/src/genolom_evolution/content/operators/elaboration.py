from .base import BaseContentOperator


class ElaborationOperator(BaseContentOperator):
    name = "elaboration"
    prompt_template_id = "elaboration-v1"
    instruction = (
        "Elaborate the learning object with clearer explanation and educational detail while remaining faithful "
        "to the source. The result must satisfy the supplied target GenoLOM genome and avoid unsupported claims."
    )
