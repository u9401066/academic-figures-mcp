from __future__ import annotations

import pytest

from src.domain.exceptions import ValidationError
from src.presentation.validation import (
    normalize_list_limit,
    normalize_output_format,
    normalize_output_size,
    normalize_plan_source,
    normalize_planned_payload,
    normalize_pmids,
    normalize_print_dimension_mm,
    normalize_publication_output_format,
    normalize_source_kind,
    normalize_source_title,
    normalize_target_dpi,
    normalize_target_journal,
)


def test_normalize_output_size_returns_canonical_format() -> None:
    assert normalize_output_size(" 1024X1536 ") == "1024x1536"


def test_normalize_output_format_returns_canonical_format() -> None:
    assert normalize_output_format(" JPG ") == "jpeg"
    assert normalize_output_format(" gif ") == "gif"


def test_normalize_publication_output_format_returns_canonical_format() -> None:
    assert normalize_publication_output_format(" JPG ") == "jpeg"
    assert normalize_publication_output_format(" tif ") == "tiff"
    assert normalize_publication_output_format(" png ") == "png"


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


def test_normalize_plan_source_accepts_pmid_or_source_title() -> None:
    assert normalize_plan_source(pmid="12345678", source_title=None) == ("12345678", None)
    assert normalize_plan_source(pmid=None, source_title="Repo brief") == (None, "Repo brief")


@pytest.mark.parametrize(
    ("pmid", "source_title", "message"),
    [
        (None, None, "Provide either pmid or source_title"),
        ("12345678", "Repo brief", "Provide either pmid or source_title, not both"),
    ],
)
def test_normalize_plan_source_rejects_invalid_combinations(
    pmid: str | None,
    source_title: str | None,
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        normalize_plan_source(pmid=pmid, source_title=source_title)


def test_normalize_source_title_rejects_blank_values() -> None:
    with pytest.raises(ValidationError, match="cannot be blank"):
        normalize_source_title("   ")


def test_normalize_source_kind_rejects_unknown_values() -> None:
    with pytest.raises(ValidationError, match="source_kind must be one of"):
        normalize_source_kind("dataset")


def test_normalize_output_format_rejects_unknown_values() -> None:
    with pytest.raises(ValidationError, match="output_format must be one of"):
        normalize_output_format("bmp")


def test_normalize_publication_output_format_rejects_gif() -> None:
    with pytest.raises(ValidationError, match="publication output_format"):
        normalize_publication_output_format("gif")


def test_normalize_target_dpi_accepts_publication_values() -> None:
    assert normalize_target_dpi(600) == 600


@pytest.mark.parametrize("value", [71, 2401])
def test_normalize_target_dpi_rejects_invalid_values(value: int) -> None:
    with pytest.raises(ValidationError, match="target_dpi"):
        normalize_target_dpi(value)


def test_normalize_print_dimension_mm_accepts_optional_positive_values() -> None:
    assert normalize_print_dimension_mm(None, field_name="width_mm") is None
    assert normalize_print_dimension_mm(89.0, field_name="width_mm") == 89.0


@pytest.mark.parametrize("value", [0.0, -1.0, 501.0])
def test_normalize_print_dimension_mm_rejects_invalid_values(value: float) -> None:
    with pytest.raises(ValidationError):
        normalize_print_dimension_mm(value, field_name="width_mm")


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
