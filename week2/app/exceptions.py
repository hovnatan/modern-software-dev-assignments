from __future__ import annotations


class LLMUnavailableError(Exception):
    """Raised when Ollama is unreachable or returns an unusable response."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
