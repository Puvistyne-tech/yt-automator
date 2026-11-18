from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from fastapi import FastAPI

from automator.api.container import ApiOptions, UseCases
from automator.api.errors import install_error_handlers
from automator.api.internal_errors import InternalErrorMiddleware
from automator.api.routers import (
    automations,
    channels,
    configuration,
    credentials,
    events,
    runs,
    system,
)

API_PREFIX = "/api"
ROUTERS = (system, credentials, channels, automations, runs, events, configuration)
Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]


def build_api(
    use_cases: UseCases, options: ApiOptions, lifespan: Lifespan | None = None
) -> FastAPI:
    app = FastAPI(
        title="YouTube Automator",
        version=options.version,
        description="Channels, automations, pipelines and runs.",
        lifespan=lifespan,
    )
    app.state.use_cases = use_cases
    app.state.options = options
    install_error_handlers(app)
    app.add_middleware(InternalErrorMiddleware)
    for module in ROUTERS:
        app.include_router(module.router, prefix=API_PREFIX)
    return app
