"""Builtin SearchXNG plugin tools."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from adomcore.domain.capabilities import FunctionBinding, FunctionSpec
from adomcore.domain.ids import PluginId

_PLUGIN_ID = PluginId("searchxng")


class SearchXNGToolset:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    def function_bindings(self) -> list[FunctionBinding]:
        return [
            FunctionBinding(
                spec=FunctionSpec(
                    name="searchxng_search",
                    description="Search a configured SearchXNG/SearXNG instance by keyword.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "keyword": {
                                "type": "string",
                                "description": "Keyword query string to search for.",
                            }
                        },
                        "required": ["keyword"],
                    },
                    source_plugin=_PLUGIN_ID,
                ),
                handler=self.search,
            )
        ]

    async def search(self, keyword: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._search_sync, keyword)

    def _search_sync(self, keyword: str) -> dict[str, Any]:
        base_url = str(self._config.get("base_url", "")).rstrip("/")
        if not base_url:
            raise ValueError("plugins.config.searchxng.base_url is not configured")

        url = f"{base_url}/search?{urlencode({'q': keyword, 'format': 'json'})}"
        with urlopen(url, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))

        results_raw = payload.get("results", [])
        results: list[dict[str, Any]] = []
        if isinstance(results_raw, list):
            for item in results_raw:
                if not isinstance(item, dict):
                    continue
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                        "engine": item.get("engine"),
                    }
                )

        return {"query": keyword, "result_count": len(results), "results": results}


def searchxng_function_bindings(
    config: dict[str, Any] | None = None,
) -> list[FunctionBinding]:
    return SearchXNGToolset(config).function_bindings()