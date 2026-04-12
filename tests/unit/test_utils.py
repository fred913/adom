import pytest

from adomcore.utils import auto_truncate


def test_auto_truncate_returns_original_when_short_enough() -> None:
    assert auto_truncate("hello", 5) == "hello"


def test_auto_truncate_adds_suffix_when_truncated() -> None:
    assert auto_truncate("hello world", 5) == "hello... [6 characters truncated]"


def test_auto_truncate_allows_zero_length_prefix() -> None:
    assert auto_truncate("hello", 0) == "... [5 characters truncated]"


def test_auto_truncate_rejects_negative_length() -> None:
    with pytest.raises(ValueError, match="truncLength must be >= 0"):
        auto_truncate("hello", -1)