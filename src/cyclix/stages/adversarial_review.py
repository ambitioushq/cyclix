"""The minimal adversarial review: it records itself as skipped."""

from cyclix.stages.base import StageResult


class AdversarialReview:
    name = "adversarial_review"

    def run(self, ctx):
        return StageResult("skipped", "minimal stage")
