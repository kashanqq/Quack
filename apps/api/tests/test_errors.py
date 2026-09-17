"""Status, code and message of every frozen application error."""

import pytest

from app.errors import (
    AppError,
    Conflict,
    Forbidden,
    LLMUnavailable,
    NotFound,
    SearchUnavailable,
    TooManyRequests,
    Unauthorized,
    UnsupportedMediaType,
    ValidationFailed,
)


@pytest.mark.parametrize(
    ("error_type", "code", "status"),
    [
        (ValidationFailed, "validation_failed", 400),
        (Unauthorized, "unauthorized", 401),
        (Forbidden, "forbidden", 403),
        (NotFound, "not_found", 404),
        (Conflict, "conflict", 409),
        (UnsupportedMediaType, "unsupported_media_type", 415),
        (TooManyRequests, "too_many_requests", 429),
        (LLMUnavailable, "llm_unavailable", 503),
        (SearchUnavailable, "search_unavailable", 503),
    ],
)
def test_error_contract(error_type, code, status):
    message = "program not found"

    with pytest.raises(AppError) as caught:
        raise error_type(message)

    error = caught.value
    assert isinstance(error, Exception)
    assert error.code == code
    assert error.status == status
    assert error.message == message
    assert str(error) == message
    assert error.args == (message,)
