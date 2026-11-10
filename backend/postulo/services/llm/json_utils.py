"""Robust JSON extraction and validation of AI answers (docs/SPEC.md section 5.1)."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError

from postulo.services.llm.base import LLMError, LLMErrorKind, LLMProvider
from postulo.services.llm.usage import tracked_complete

_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*\n(.*?)```", re.DOTALL)

FORMAT_REMINDER = (
    "\n\nRAPPEL DE FORMAT : ta réponse précédente n'était pas un JSON valide pour le "
    "schéma demandé. Réponds uniquement avec un objet JSON valide, sans texte autour.\n"
    "Erreur constatée : {error}\n"
)


class JSONExtractionError(ValueError):
    pass


def extract_json(text: str) -> Any:
    """Return the first JSON value found in `text`.

    Order: fenced ```json blocks, then every `{` or `[` from left to right. Uses a
    real JSON decoder, so braces inside strings are handled correctly.
    """
    decoder = json.JSONDecoder()
    for block in _FENCE_RE.findall(text):
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            continue
    for index, char in enumerate(text):
        if char in "{[":
            try:
                value, _end = decoder.raw_decode(text, index)
            except json.JSONDecodeError:
                continue
            return value
    raise JSONExtractionError("Aucun JSON valide trouvé dans la réponse.")


def parse_as[M: BaseModel](text: str, schema: type[M]) -> M:
    return schema.model_validate(extract_json(text))


async def complete_json[M: BaseModel](
    provider: LLMProvider,
    prompt: str,
    schema: type[M],
    *,
    web: bool = False,
    timeout: int = 300,
) -> M:
    """Ask for JSON, validate it with `schema`, retry once with a format reminder."""
    answer = await tracked_complete(provider, prompt, web=web, timeout=timeout)
    try:
        return parse_as(answer, schema)
    except (JSONExtractionError, ValidationError) as first_error:
        retry_prompt = prompt + FORMAT_REMINDER.format(error=_short(first_error))
        answer = await tracked_complete(provider, retry_prompt, web=web, timeout=timeout)
        try:
            return parse_as(answer, schema)
        except (JSONExtractionError, ValidationError) as second_error:
            raise LLMError(
                LLMErrorKind.INVALID_RESPONSE, detail=_short(second_error)
            ) from second_error


def _short(error: Exception, limit: int = 500) -> str:
    text = str(error)
    return text if len(text) <= limit else text[:limit] + "..."
