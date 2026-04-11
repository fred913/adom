"""Cron plugin tools."""

from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.domain.ids import PluginId

_PLUGIN_ID = PluginId("cron")


def cron_function_bindings() -> list[FunctionBinding]:
    return [
        FunctionBinding(
            spec=FunctionSpec(
                name="create_cron_instruction",
                description="Create a scheduled instruction that fires on a cron schedule.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "string"},
                        "cron_expr": {
                            "type": "string",
                            "description": "5-field cron expression",
                        },
                        "instruction": {"type": "string"},
                    },
                    "required": ["job_id", "cron_expr", "instruction"],
                },
                source_plugin=_PLUGIN_ID,
            ),
            handler=_create_cron_instruction,
        ),
        FunctionBinding(
            spec=FunctionSpec(
                name="list_cron_jobs",
                description="List all scheduled cron jobs.",
                input_schema={"type": "object", "properties": {}},
                source_plugin=_PLUGIN_ID,
            ),
            handler=_list_cron_jobs,
        ),
        FunctionBinding(
            spec=FunctionSpec(
                name="remove_cron_job",
                description="Remove a scheduled cron job.",
                input_schema={
                    "type": "object",
                    "properties": {"job_id": {"type": "string"}},
                    "required": ["job_id"],
                },
                source_plugin=_PLUGIN_ID,
            ),
            handler=_remove_cron_job,
        ),
    ]


def _create_cron_instruction(
    job_id: str, cron_expr: str, instruction: str
) -> dict[str, str]:
    return {
        "status": "scheduled",
        "job_id": job_id,
        "cron_expr": cron_expr,
        "instruction": instruction,
    }


def _list_cron_jobs() -> dict[str, str]:
    return {"status": "ok", "jobs": "[]"}


def _remove_cron_job(job_id: str) -> dict[str, str]:
    return {"status": "removed", "job_id": job_id}
