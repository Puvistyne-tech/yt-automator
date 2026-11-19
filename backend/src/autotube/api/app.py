from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from fastapi import FastAPI

from autotube.api.container import ApiOptions, UseCases
from autotube.api.errors import install_error_handlers
from autotube.api.internal_errors import InternalErrorMiddleware
from autotube.api.routers import (
    automations,
    channels,
    configuration,
    credentials,
    events,
    runs,
    storage,
    system,
    templates,
)

API_PREFIX = "/api"
ROUTERS = (
    system,
    credentials,
    channels,
    automations,
    runs,
    events,
    configuration,
    storage,
    templates,
)
Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]


def build_api(
    use_cases: UseCases, options: ApiOptions, lifespan: Lifespan | None = None
) -> FastAPI:
    app = FastAPI(
        title="AutoTube",
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
