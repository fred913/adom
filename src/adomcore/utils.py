"""General utility helpers for adomcore."""

from __future__ import annotations

import random
import secrets
import socket
import string
from typing import cast

type PrimitiveValue = str | int | float | bool | None
type StructuredValue = (
    PrimitiveValue | dict[str, StructuredValue] | list[StructuredValue]
)


def auto_truncate(string: str, max_length: int) -> str:
    """Truncate a string and append a human-readable omitted-length suffix.

    Example suffix format:
    ``... [15 characters truncated]``
    """

    if max_length < 0:
        raise ValueError("truncLength must be >= 0")
    if len(string) <= max_length:
        return string

    truncated_count = len(string) - max_length
    return f"{string[:max_length]}... [{truncated_count} characters truncated]"


def discover_random_unused_port(
    port_range: tuple[int, int] = (40000, 50000),
) -> int:
    """Return a random currently-unused TCP port within the given inclusive range."""

    start, end = port_range
    if start > end:
        raise ValueError("port_range start must be <= end")
    if start < 1 or end > 65535:
        raise ValueError("port_range must stay within 1..65535")

    max_attempts = max(32, min((end - start) + 1, 512))
    for _ in range(max_attempts):
        candidate = random.randint(start, end)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", candidate))
            except OSError:
                continue
        return candidate

    raise RuntimeError("Unable to discover an unused port in the requested range")


def random_password(length: int) -> str:
    """Generate an ASCII alphanumeric password of the requested length."""

    if length <= 0:
        raise ValueError("length must be > 0")

    alphabet = string.ascii_lowercase + string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def require_json_object(value: object) -> dict[str, StructuredValue]:
    """Validate that a value is a JSON-compatible object."""

    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    result: dict[str, StructuredValue] = {}
    mapping = cast(dict[object, object], value)
    for key, item in mapping.items():
        if not isinstance(key, str):
            raise ValueError("Expected a JSON object")
        result[key] = require_json_value(item)
    return result


def require_json_value(value: object) -> StructuredValue:
    """Validate that a value is JSON-compatible."""

    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list):
        sequence = cast(list[object], value)
        return [require_json_value(item) for item in sequence]
    if isinstance(value, dict):
        return require_json_object(cast(object, value))
    raise ValueError("Expected a JSON-compatible value")
