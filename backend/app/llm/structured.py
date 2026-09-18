"""Shared structured-output parsing/retry logic for LLMClient and FakeLLMClient.

Extracted from ``LLMClient.structured`` so both clients parse and retry
identically: strip code fences by slicing to the outermost ``{...}``, validate
against the target schema, and on failure produce the same retry message.
"""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from app.schemas.llm import LLMMessage


def parse_structured_output[T: BaseModel](
    raw_text: str, schema: type[T]
) -> tuple[T | None, str | None]:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = raw_text[start : end + 1]
    else:
        candidate = raw_text
    try:
        return schema.model_validate_json(candidate), None
    except ValidationError as exc:
        return None, str(exc)


def structured_validation_retry_message(error: str) -> LLMMessage:
    return LLMMessage(
        role="user",
        content=(f"Ответ не прошёл валидацию: {error}. Верни только JSON по схеме."),
    )
