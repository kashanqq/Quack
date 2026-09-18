"""Phase 2 program extraction boundary; implementation belongs to B2."""

from typing import Any

from app.schemas.programs import Program


async def extract_program(llm: Any, html: str, url: str) -> Program:
    raise NotImplementedError("phase 2")
