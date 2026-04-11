"""Example OpenAPI-backed plugin using the reusable OpenApiPlugin helper."""

from adomcore.plugins.openapi import OpenApiPlugin

plugin = OpenApiPlugin(
    plugin_id="petstore_openapi",
    name="Petstore OpenAPI",
    description="OpenAPI-backed petstore example plugin.",
    base_url="https://petstore3.swagger.io/api/v3",
    spec={
        "openapi": "3.0.0",
        "paths": {
            "/pet/findByStatus": {
                "get": {
                    "operationId": "findPetsByStatus",
                    "summary": "Find pets by status",
                    "parameters": [
                        {
                            "name": "status",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                }
            }
        },
    },
)
