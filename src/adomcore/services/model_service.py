"""Model service — load and resolve ModelSpec from config."""

from adomcore.domain.models import ModelSpec


class ModelService:
    def __init__(self, specs: list[ModelSpec], default_model_id: str) -> None:
        self._specs = {s.id: s for s in specs}
        self._default_id = default_model_id

    def get(self, model_id: str) -> ModelSpec:
        spec = self._specs.get(model_id)
        if spec is None:
            raise KeyError(f"Model not found: {model_id!r}")
        return spec

    def get_default(self) -> ModelSpec:
        return self.get(self._default_id)

    def get_active(self, active_model_id: str) -> ModelSpec:
        return self.get(active_model_id)

    def list_enabled(self) -> list[ModelSpec]:
        return [s for s in self._specs.values() if s.enabled]
