class InstagramAutomationError(Exception):
    """Base exception for Instagram automation failures."""


class InstagramAuthError(InstagramAutomationError):
    """Raised when authentication fails."""


class InstagramRateLimitError(InstagramAutomationError):
    """Raised when Instagram throttles or blocks requests."""


class PostDownloadError(InstagramAutomationError):
    """Raised when media cannot be downloaded or resolved."""


class SessionNotFoundError(InstagramAutomationError):
    """Raised when a session does not exist or is expired."""
