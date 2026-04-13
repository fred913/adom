import pytest

from adomcore.utils import auto_truncate, discover_random_unused_port, random_password


def test_auto_truncate_returns_original_when_short_enough() -> None:
    assert auto_truncate("hello", 5) == "hello"


def test_auto_truncate_adds_suffix_when_truncated() -> None:
    assert auto_truncate("hello world", 5) == "hello... [6 characters truncated]"


def test_auto_truncate_allows_zero_length_prefix() -> None:
    assert auto_truncate("hello", 0) == "... [5 characters truncated]"


def test_auto_truncate_rejects_negative_length() -> None:
    with pytest.raises(ValueError, match="truncLength must be >= 0"):
        auto_truncate("hello", -1)


def test_discover_random_unused_port_returns_port_in_range() -> None:
    port = discover_random_unused_port((45000, 45010))

    assert 45000 <= port <= 45010


def test_random_password_generates_alphanumeric_string() -> None:
    password = random_password(24)

    assert len(password) == 24
    assert password.isalnum()


def test_random_password_rejects_non_positive_length() -> None:
    with pytest.raises(ValueError, match="length must be > 0"):
        random_password(0)
