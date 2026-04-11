from adomcore.plugins.context import PluginContext
from adomcore.plugins.openapi import OpenApiPlugin
from adomcore.services.capability_registry import CapabilityRegistry


def test_openapi_plugin_registers_operation_as_function() -> None:
    registry = CapabilityRegistry()
    plugin = OpenApiPlugin(
        plugin_id="sample_openapi",
        base_url="https://example.com",
        spec={
            "openapi": "3.0.0",
            "paths": {
                "/users/{userId}": {
                    "get": {
                        "operationId": "getUser",
                        "summary": "Get a user",
                        "parameters": [
                            {
                                "name": "userId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            },
                            {
                                "name": "verbose",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "boolean"},
                            },
                        ],
                    }
                }
            },
        },
    )

    plugin.setup(PluginContext(registry))

    spec = registry.get_spec("getUser")
    assert spec is not None
    assert spec.description == "Get a user"
    assert spec.input_schema["properties"]["userId"]["type"] == "string"
    assert "userId" in spec.input_schema["required"]
