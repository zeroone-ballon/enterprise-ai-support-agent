"""Storage errors shared by lifecycle repository adapters."""


class DuplicateRecommendationError(ValueError):
    """Raised when a recommendation identifier already exists."""


class RecommendationNotFoundError(LookupError):
    """Raised when an unknown recommendation is requested."""
