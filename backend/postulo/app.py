"""FastAPI application: API under /api, compiled frontend under /."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware

from postulo import APP_NAME, __version__, config
from postulo.api import applications, health, jobs, llm, profile, settings
from postulo.db.session import get_engine, init_db
from postulo.services.jobs import JobManager
from postulo.services.llm.base import LLMError, LLMErrorKind

logger = logging.getLogger(__name__)

# Protects the local server against DNS-rebinding attacks from web pages.
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

_FRONTEND_MISSING = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Postulo</title>
<style>body{font-family:system-ui,sans-serif;max-width:40rem;margin:4rem auto;padding:0 1rem;
color:#14213D}code{background:#F6F8FB;padding:.1rem .3rem;border-radius:4px}</style></head>
<body><h1>Postulo</h1><p>Le serveur fonctionne, mais l'interface n'est pas compilée.</p>
<p>Lance <code>pnpm -C frontend install</code> puis <code>pnpm -C frontend build</code>,
et recharge cette page.</p></body></html>"""

_LLM_ERROR_STATUS = {
    LLMErrorKind.NOT_AVAILABLE: 503,
    LLMErrorKind.NOT_LOGGED_IN: 503,
    LLMErrorKind.USAGE_LIMIT: 429,
    LLMErrorKind.TIMEOUT: 504,
    LLMErrorKind.INVALID_RESPONSE: 502,
    LLMErrorKind.UNKNOWN: 502,
}


def create_app(
    *,
    init_database: bool = True,
    demo_step_seconds: float = 1.0,
    frontend_dir: Path | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if init_database:
            init_db()
        app.state.jobs = JobManager(get_engine())
        app.state.demo_step_seconds = demo_step_seconds
        yield
        await app.state.jobs.shutdown()

    app = FastAPI(
        title=APP_NAME,
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
    if config.is_dev_mode():
        app.add_middleware(
            CORSMiddleware,
            allow_origins=DEV_ORIGINS,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.exception_handler(LLMError)
    async def handle_llm_error(_request: Request, exc: LLMError) -> JSONResponse:
        return JSONResponse(
            status_code=_LLM_ERROR_STATUS.get(exc.kind, 502),
            content={
                "error": {"kind": exc.kind.value, "message": exc.message, "detail": exc.detail}
            },
        )

    for router in (
        health.router,
        settings.router,
        llm.router,
        jobs.router,
        profile.router,
        applications.router,
    ):
        app.include_router(router)

    _mount_frontend(app, frontend_dir if frontend_dir is not None else config.frontend_dist_dir())
    return app


def _mount_frontend(app: FastAPI, dist: Path | None) -> None:
    """Serve the SPA: real files when they exist, index.html for client-side routes."""

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> Response:  # sync: filesystem access runs in the threadpool
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        if dist is None or not (dist / "index.html").is_file():
            return HTMLResponse(_FRONTEND_MISSING)
        root = dist.resolve()
        candidate = (root / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(root):
            headers = (
                {"Cache-Control": "public, max-age=31536000, immutable"}
                if path.startswith("assets/")
                else {}
            )
            return FileResponse(candidate, headers=headers)
        return FileResponse(root / "index.html", headers={"Cache-Control": "no-cache"})
