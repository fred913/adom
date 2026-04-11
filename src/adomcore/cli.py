"""CLI entry point."""

import typer

app = typer.Typer(name="adomcore", help="adomcore agent runtime")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind host"),
    port: int = typer.Option(8000, help="Bind port"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
) -> None:
    """Start the adomcore API server."""
    import uvicorn

    uvicorn.run(
        "adomcore.app.main:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )


if __name__ == "__main__":
    app()
