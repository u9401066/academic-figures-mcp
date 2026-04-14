from __future__ import annotations

import pytest

from src.domain.exceptions import ValidationError
from src.presentation.validation import (
    normalize_list_limit,
    normalize_output_size,
    normalize_planned_payload,
    normalize_pmids,
    normalize_target_journal,
)


def test_normalize_output_size_returns_canonical_format() -> None:
    assert normalize_output_size(" 1024X1536 ") == "1024x1536"


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("large", "output_size must look like 1024x1536"),
        ("128x1536", "between 256 and 4096"),
        ("1024x5000", "between 256 and 4096"),
    ],
)
def test_normalize_output_size_rejects_invalid_values(value: str, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        normalize_output_size(value)


def test_normalize_pmids_deduplicates_and_preserves_order() -> None:
    assert normalize_pmids([" 123 ", "456", "123", "007"]) == ["123", "456", "007"]


def test_normalize_pmids_rejects_oversized_batches() -> None:
    oversized = [str(index) for index in range(26)]

    with pytest.raises(ValidationError, match="cannot contain more than 25 items"):
        normalize_pmids(oversized)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, None), (" Nature ", "Nature")],
)
def test_normalize_target_journal_accepts_expected_values(
    value: str | None,
    expected: str | None,
) -> None:
    assert normalize_target_journal(value) == expected


@pytest.mark.parametrize(
    ("value", "message"),
    [("   ", "cannot be blank"), ("N" * 121, "too long")],
)
def test_normalize_target_journal_rejects_invalid_values(value: str, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        normalize_target_journal(value)


@pytest.mark.parametrize(
    "value",
    [None, {}, []],
)
def test_normalize_planned_payload_requires_non_empty_dict(value: object) -> None:
    with pytest.raises(ValidationError):
        normalize_planned_payload(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(1, 1), (200, 200)],
)
def test_normalize_list_limit_accepts_bounds(value: int, expected: int) -> None:
    assert normalize_list_limit(value) == expected


@pytest.mark.parametrize("value", [0, 201])
def test_normalize_list_limit_rejects_invalid_values(value: int) -> None:
    with pytest.raises(ValidationError):
        normalize_list_limit(value)
