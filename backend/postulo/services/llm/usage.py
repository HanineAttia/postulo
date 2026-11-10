"""Record every AI call in `llm_usage` and count today's calls."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from datetime import time as dtime

from sqlalchemy import func
from sqlmodel import Session, select

from postulo.db.models import LLMUsage
from postulo.db.session import get_engine
from postulo.services.llm.base import LLMError, LLMErrorKind, LLMProvider, parse_task


def record_usage(provider: str, task: str, duration_ms: int, error: LLMError | None) -> None:
    with Session(get_engine()) as session:
        session.add(
            LLMUsage(
                provider=provider,
                task=task,
                duration_ms=duration_ms,
                success=error is None,
                error_kind=error.kind.value if error else None,
            )
        )
        session.commit()


async def tracked_complete(
    provider: LLMProvider, prompt: str, *, web: bool = False, timeout: int = 300
) -> str:
    """Call the provider and log the call, whatever the outcome."""
    started = time.perf_counter()
    error: LLMError | None = None
    try:
        return await provider.complete(prompt, web=web, timeout=timeout)
    except LLMError as exc:
        error = exc
        raise
    except Exception as exc:
        error = LLMError(LLMErrorKind.UNKNOWN, detail=repr(exc))
        raise error from exc
    finally:
        elapsed = int((time.perf_counter() - started) * 1000)
        record_usage(provider.name, parse_task(prompt), elapsed, error)


def calls_today(now: datetime | None = None) -> int:
    """Number of AI calls since local midnight."""
    local_now = (now or datetime.now(UTC)).astimezone()
    midnight = datetime.combine(local_now.date(), dtime.min, tzinfo=local_now.tzinfo)
    with Session(get_engine()) as session:
        stmt = (
            select(func.count())
            .select_from(LLMUsage)
            .where(LLMUsage.created_at >= midnight.astimezone(UTC))
        )
        return int(session.exec(stmt).one())
