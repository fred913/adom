"""CLI entry point."""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from fastapi import FastAPI

app = typer.Typer(name="adomcore", help="adomcore agent runtime")


def _cli_create_app() -> FastAPI:  # pyright: ignore[reportUnusedFunction]
    from adomcore.app.main import create_app

    return create_app(takeover_logging=True)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind host"),
    port: int = typer.Option(8000, help="Bind port"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
) -> None:
    """Start the adomcore API server."""
    import uvicorn

    uvicorn.run(
        "adomcore.cli:_cli_create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )


if __name__ == "__main__":
    app()
