"""Models router."""

from fastapi import APIRouter, Request

from adomcore.api.schemas.model import ModelResponse

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelResponse])
async def list_models(request: Request) -> list[ModelResponse]:
    c = request.app.state.container
    return [
        ModelResponse(
            id=s.id,
            provider=s.provider.value,
            model=s.model,
            context_window=s.context_window,
            enabled=s.enabled,
        )
        for s in c.model_service.list_enabled()
    ]
