from adomcore.plugins.openapi import OpenApiPlugin


def test_openapi_plugin_registers_operation_as_function() -> None:
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

    functions = plugin.functions()
    assert len(functions) == 1
    spec = functions[0].spec
    assert plugin.id == "sample_openapi"
    assert spec.description == "Get a user"
    assert spec.input_schema["properties"]["userId"]["type"] == "string"
    assert "userId" in spec.input_schema["required"]
    assert spec.source_plugin == "sample_openapi"
