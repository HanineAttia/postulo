"""Demonstration job: shows live progress with the same steps as a real application.

It always uses the MockProvider, so it works without any AI account or quota.
"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel

from postulo.services.jobs import JobContext, JobFunc
from postulo.services.llm.json_utils import complete_json
from postulo.services.llm.providers.mock import MockProvider

DEMO_JOB_TYPE = "demo"
# Keys only: the frontend translates them (Rédaction, Mise en page, Contrôle ATS, Jury, Correction).
DEMO_STEPS = ("draft", "layout", "ats_check", "jury", "revision")
_TICKS_PER_STEP = 4

DEMO_PROMPT = """TASK: demo
Ceci est une tâche de démonstration. Réponds avec un objet JSON contenant
"headline" (texte), "summary" (texte) et "score" (entier de 0 à 100).
"""


class DemoDraft(BaseModel):
    headline: str
    summary: str
    score: int


def make_demo_job(step_seconds: float = 1.0) -> JobFunc:
    async def run(ctx: JobContext) -> dict[str, Any]:
        draft: DemoDraft | None = None
        total = len(DEMO_STEPS)
        for index, key in enumerate(DEMO_STEPS):
            ctx.start_step(key)
            if key == "draft":
                draft = await complete_json(MockProvider(), DEMO_PROMPT, DemoDraft)
            for tick in range(1, _TICKS_PER_STEP + 1):
                await asyncio.sleep(step_seconds / _TICKS_PER_STEP)
                if tick < _TICKS_PER_STEP:
                    ctx.set_progress(int(100 * (index + tick / _TICKS_PER_STEP) / total))
            ctx.finish_step(key, progress=int(100 * (index + 1) / total))
        assert draft is not None
        return draft.model_dump()

    return run
