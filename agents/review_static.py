"""Compatibility mixin combining static review stages."""

from agents.review_basic import ReviewBasicMixin
from agents.review_specialist import ReviewSpecialistMixin


class ReviewStaticMixin(ReviewBasicMixin, ReviewSpecialistMixin):
    """Implements review levels one through three."""
