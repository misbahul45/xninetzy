from __future__ import annotations

VIDEO_BACKEND_UNAVAILABLE: str = "VIDEO_BACKEND_UNAVAILABLE"
VIDEO_BACKEND_TIMEOUT: str = "VIDEO_BACKEND_TIMEOUT"
VIDEO_BACKEND_NOT_CONFIGURED: str = "VIDEO_BACKEND_NOT_CONFIGURED"
VIDEO_CAPABILITY_MISMATCH: str = "VIDEO_CAPABILITY_MISMATCH"
VIDEO_FORMAT_UNSUPPORTED: str = "VIDEO_FORMAT_UNSUPPORTED"
VIDEO_INPUT_NOT_FOUND: str = "VIDEO_INPUT_NOT_FOUND"
VIDEO_INPUT_NOT_READABLE: str = "VIDEO_INPUT_NOT_READABLE"
VIDEO_INPUT_TOO_LARGE: str = "VIDEO_INPUT_TOO_LARGE"
VIDEO_DURATION_EXCEEDED: str = "VIDEO_DURATION_EXCEEDED"
VIDEO_DURATION_INVALID: str = "VIDEO_DURATION_INVALID"
VIDEO_CODEC_NOT_ALLOWED: str = "VIDEO_CODEC_NOT_ALLOWED"
VIDEO_OUTPUT_TOO_LARGE: str = "VIDEO_OUTPUT_TOO_LARGE"
VIDEO_OUTPUT_NOT_FOUND: str = "VIDEO_OUTPUT_NOT_FOUND"
VIDEO_OUTPUT_INVALID: str = "VIDEO_OUTPUT_INVALID"
VIDEO_GENERATION_FAILED: str = "VIDEO_GENERATION_FAILED"
VIDEO_CANCELLED: str = "VIDEO_CANCELLED"
VIDEO_JOB_NOT_FOUND: str = "VIDEO_JOB_NOT_FOUND"
VIDEO_JOB_EXPIRED: str = "VIDEO_JOB_EXPIRED"
VIDEO_PROVIDER_NOT_ALLOWED: str = "VIDEO_PROVIDER_NOT_ALLOWED"
VIDEO_REFERENCE_INVALID: str = "VIDEO_REFERENCE_INVALID"
VIDEO_IDEMPOTENCY_CONFLICT: str = "VIDEO_IDEMPOTENCY_CONFLICT"
VIDEO_BUDGET_EXCEEDED: str = "VIDEO_BUDGET_EXCEEDED"
VIDEO_INVALID_ARGUMENT: str = "VIDEO_INVALID_ARGUMENT"


_VIDEO_RETRYABLE: frozenset[str] = frozenset(
    {
        VIDEO_BACKEND_UNAVAILABLE,
        VIDEO_BACKEND_TIMEOUT,
        VIDEO_OUTPUT_NOT_FOUND,
    }
)


_VIDEO_TERMINAL: frozenset[str] = frozenset(
    {
        VIDEO_INVALID_ARGUMENT,
        VIDEO_INPUT_NOT_FOUND,
        VIDEO_INPUT_NOT_READABLE,
        VIDEO_INPUT_TOO_LARGE,
        VIDEO_DURATION_INVALID,
        VIDEO_DURATION_EXCEEDED,
        VIDEO_CODEC_NOT_ALLOWED,
        VIDEO_FORMAT_UNSUPPORTED,
        VIDEO_CAPABILITY_MISMATCH,
        VIDEO_PROVIDER_NOT_ALLOWED,
        VIDEO_REFERENCE_INVALID,
        VIDEO_OUTPUT_INVALID,
        VIDEO_BUDGET_EXCEEDED,
    }
)


class VideoError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        job_id: str | None = None,
        provider: str | None = None,
        retryable: bool | None = None,
        backend: str | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.job_id = job_id
        self.provider = provider
        self.backend = backend
        if retryable is None:
            self.retryable = code in _VIDEO_RETRYABLE
        else:
            self.retryable = bool(retryable)
        self.details = dict(details or {})

    def to_dict(self) -> dict:
        payload = {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "terminal": self.code in _VIDEO_TERMINAL,
        }
        if self.job_id:
            payload["job_id"] = self.job_id
        if self.provider:
            payload["provider"] = self.provider
        if self.backend:
            payload["backend"] = self.backend
        if self.details:
            payload["details"] = self.details
        return payload


def is_retryable(code: str) -> bool:
    return code in _VIDEO_RETRYABLE


def is_terminal(code: str) -> bool:
    return code in _VIDEO_TERMINAL
