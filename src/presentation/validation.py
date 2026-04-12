"""Input validation helpers for MCP tools and CLI entrypoints."""

from __future__ import annotations

import re
from typing import Any

from src.domain.exceptions import ValidationError
from src.domain.value_objects import FIGURE_TYPE_TO_TEMPLATE

_PMID_PATTERN = re.compile(r"^\d{1,12}$")
_LANGUAGE_PATTERN = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})?$")
_OUTPUT_SIZE_PATTERN = re.compile(r"^(?P<width>\d{2,5})x(?P<height>\d{2,5})$")
_SUPPORTED_FIGURE_TYPES = frozenset({"auto", *FIGURE_TYPE_TO_TEMPLATE.keys()})
_MAX_BATCH_PMIDS = 25
_MAX_LIST_LIMIT = 200


def normalize_pmid(value: str, *, field_name: str = "pmid") -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} is required")
    if not _PMID_PATTERN.fullmatch(normalized):
        raise ValidationError(f"{field_name} must contain only digits")
    return normalized


def normalize_optional_pmid(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalize_pmid(normalized, field_name=field_name)


def normalize_figure_type(value: str, *, allow_auto: bool = True) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValidationError("figure_type is required")
    if normalized == "auto" and allow_auto:
        return normalized
    if normalized not in _SUPPORTED_FIGURE_TYPES - {"auto"}:
        supported = ", ".join(sorted(_SUPPORTED_FIGURE_TYPES - {"auto"}))
        raise ValidationError(f"figure_type must be one of: {supported}")
    return normalized


def normalize_language(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError("language is required")
    if not _LANGUAGE_PATTERN.fullmatch(normalized):
        raise ValidationError("language must look like en or zh-TW")
    return normalized


def normalize_output_size(value: str) -> str:
    normalized = value.strip().lower()
    match = _OUTPUT_SIZE_PATTERN.fullmatch(normalized)
    if match is None:
        raise ValidationError("output_size must look like 1024x1536")
    width = int(match.group("width"))
    height = int(match.group("height"))
    if width < 256 or height < 256 or width > 4096 or height > 4096:
        raise ValidationError("output_size must stay between 256 and 4096 pixels per side")
    return f"{width}x{height}"


def normalize_feedback(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError("feedback is required")
    if len(normalized) > 4000:
        raise ValidationError("feedback is too long")
    return normalized


def normalize_image_path(value: str, *, field_name: str = "image_path") -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} is required")
    return normalized


def normalize_style_preset(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError("style_preset is required")
    return normalized


def normalize_target_journal(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ValidationError("target_journal cannot be blank when provided")
    if len(normalized) > 120:
        raise ValidationError("target_journal is too long")
    return normalized


def normalize_planned_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("planned_payload must be an object")
    if not value:
        raise ValidationError("planned_payload cannot be empty")
    return dict(value)


def normalize_output_dir(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ValidationError("output_dir cannot be blank when provided")
    return normalized


def normalize_pmids(values: list[str]) -> list[str]:
    if not values:
        raise ValidationError("pmids must contain at least one PMID")
    if len(values) > _MAX_BATCH_PMIDS:
        raise ValidationError(f"pmids cannot contain more than {_MAX_BATCH_PMIDS} items")

    unique: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        pmid = normalize_pmid(raw_value)
        if pmid in seen:
            continue
        unique.append(pmid)
        seen.add(pmid)
    return unique


def normalize_manifest_id(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError("manifest_id is required")
    if len(normalized) > 200:
        raise ValidationError("manifest_id is too long")
    return normalized


def normalize_list_limit(value: int) -> int:
    if value <= 0:
        raise ValidationError("limit must be positive")
    if value > _MAX_LIST_LIMIT:
        raise ValidationError(f"limit cannot exceed {_MAX_LIST_LIMIT}")
    return value
