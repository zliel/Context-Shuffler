"""Typed exception hierarchy for LLM provider errors."""


class LLMError(Exception):
    """Base exception for all LLM provider errors."""
    pass


class LLMConnectionError(LLMError):
    """Server unreachable, DNS failure, connection refused."""
    pass


class LLMTimeoutError(LLMError):
    """Request exceeded timeout."""
    pass


class LLMRateLimitError(LLMError):
    """Server returned 429 or 503 rate-limit response."""
    pass


class LLMBadResponseError(LLMError):
    """Server returned 200 but response is malformed or missing fields."""
    pass


class LLMEmptyResponseError(LLMError):
    """Server returned successfully but response text is empty."""
    pass
