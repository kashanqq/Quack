"""Frozen application error contract."""


class AppError(Exception):
    code: str
    message: str
    status: int

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationFailed(AppError):
    code = "validation_failed"
    status = 400


class Unauthorized(AppError):
    code = "unauthorized"
    status = 401


class Forbidden(AppError):
    code = "forbidden"
    status = 403


class NotFound(AppError):
    code = "not_found"
    status = 404


class Conflict(AppError):
    code = "conflict"
    status = 409


class UnsupportedMediaType(AppError):
    code = "unsupported_media_type"
    status = 415


class TooManyRequests(AppError):
    code = "too_many_requests"
    status = 429


class LLMUnavailable(AppError):
    code = "llm_unavailable"
    status = 503


class SearchUnavailable(AppError):
    code = "search_unavailable"
    status = 503
