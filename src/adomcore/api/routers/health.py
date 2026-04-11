"""Health router."""

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    return {"status": "ok"}
