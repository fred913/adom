"""Model schemas."""

from pydantic import BaseModel


class ModelResponse(BaseModel):
    id: str
    provider: str
    model: str
    context_window: int
    enabled: bool
