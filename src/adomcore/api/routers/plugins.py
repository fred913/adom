"""Plugins router."""

from fastapi import APIRouter, Request

from adomcore.api.schemas.plugin import PluginResponse

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("", response_model=list[PluginResponse])
async def list_plugins(request: Request) -> list[PluginResponse]:
    c = request.app.state.container
    return [
        PluginResponse(
            id=str(plugin.id),
            name=plugin.name,
            version=plugin.version,
            enabled=c.plugin_manager.is_enabled(plugin.id),
        )
        for plugin in c.plugin_manager.list_all()
    ]
