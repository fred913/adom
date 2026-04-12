"""General utility helpers for adomcore."""


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
