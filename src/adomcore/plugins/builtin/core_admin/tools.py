"""Builtin core_admin plugin — agent self-modification tools."""

from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.domain.ids import PluginId

_PLUGIN_ID = PluginId("core_admin")
type _StatusResult = dict[str, str]


def _add_skill(skill_id: str, name: str, content: str) -> _StatusResult:
    del name, content
    return {"status": "added", "skill_id": skill_id}


def _enable_skill(skill_id: str) -> _StatusResult:
    return {"status": "enabled", "skill_id": skill_id}


def _disable_skill(skill_id: str) -> _StatusResult:
    return {"status": "disabled", "skill_id": skill_id}


def _switch_model(model_id: str) -> _StatusResult:
    return {"status": "switched", "model_id": model_id}


def core_admin_function_bindings() -> list[FunctionBinding]:
    return [
        FunctionBinding(
            spec=FunctionSpec(
                name="add_skill",
                description="Add a new skill to the agent.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "skill_id": {"type": "string"},
                        "name": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["skill_id", "name", "content"],
                },
                source_plugin=_PLUGIN_ID,
            ),
            handler=_add_skill,
        ),
        FunctionBinding(
            spec=FunctionSpec(
                name="enable_skill",
                description="Enable a skill by ID.",
                input_schema={
                    "type": "object",
                    "properties": {"skill_id": {"type": "string"}},
                    "required": ["skill_id"],
                },
                source_plugin=_PLUGIN_ID,
            ),
            handler=_enable_skill,
        ),
        FunctionBinding(
            spec=FunctionSpec(
                name="disable_skill",
                description="Disable a skill by ID.",
                input_schema={
                    "type": "object",
                    "properties": {"skill_id": {"type": "string"}},
                    "required": ["skill_id"],
                },
                source_plugin=_PLUGIN_ID,
            ),
            handler=_disable_skill,
        ),
        FunctionBinding(
            spec=FunctionSpec(
                name="switch_model",
                description="Switch the active LLM model.",
                input_schema={
                    "type": "object",
                    "properties": {"model_id": {"type": "string"}},
                    "required": ["model_id"],
                },
                source_plugin=_PLUGIN_ID,
            ),
            handler=_switch_model,
        ),
    ]
