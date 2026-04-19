"""FastAPI app factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adomcore.app.lifespan import build_container, shutdown, startup
from adomcore.app.settings import AppSettings

_container_key = "container"


def create_app(
    settings: AppSettings | None = None, *, takeover_logging: bool = False
) -> FastAPI:
    if settings is None:
        settings = AppSettings.load()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        c = await build_container(settings, takeover_logging=takeover_logging)
        app.state.container = c
        await startup(c)
        yield
        await shutdown(c)

    app = FastAPI(title="adomcore", lifespan=lifespan)

    if settings.api.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.api.cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    from adomcore.api.routers import (
        agent,
        chat,
        cron,
        health,
        mcp,
        models,
        plugins,
        skills,
    )

    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(agent.router)
    app.include_router(plugins.router)
    app.include_router(skills.router)
    app.include_router(mcp.router)
    app.include_router(cron.router)
    app.include_router(models.router)

    return app
