from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings


REQUIRED_COLUMNS = ("paper_id", "title", "summary", "text_for_embedding", "age_days")
MIN_SUMMARY_LENGTH = 20


def _is_blank(series: pd.Series) -> pd.Series:
    """Return a boolean mask for null or whitespace-only values."""
    return series.isna() | series.astype(str).str.strip().eq("")


def _column_blank_count(df: pd.DataFrame, column: str) -> int:
    """Count blank values, treating a missing column as fully invalid."""
    if column not in df.columns:
        return int(len(df))
    return int(_is_blank(df[column]).sum())


def _to_python(value: Any) -> Any:
    """Convert pandas/numpy scalar values into JSON-serializable Python values."""
    if isinstance(value, dict):
        return {str(key): _to_python(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_python(item) for item in value]
    if isinstance(value, tuple):
        return [_to_python(item) for item in value]
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.date().isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write UTF-8 JSON using non-ASCII characters as-is."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_python(payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run defensive quality checks and persist the JSON report."""
    total_rows = int(len(df))
    present_columns = set(df.columns)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in present_columns]

    missing_paper_ids = _column_blank_count(df, "paper_id")
    duplicate_paper_ids = 0
    if "paper_id" in df.columns:
        valid_ids = df.loc[~_is_blank(df["paper_id"]), "paper_id"].astype(str).str.strip()
        duplicate_paper_ids = int(valid_ids.duplicated().sum())

    empty_titles = _column_blank_count(df, "title")

    invalid_summaries = total_rows
    if "summary" in df.columns:
        summaries = df["summary"]
        invalid_summaries = int((_is_blank(summaries) | summaries.astype(str).str.strip().str.len().lt(MIN_SUMMARY_LENGTH)).sum())

    empty_embedding_texts = _column_blank_count(df, "text_for_embedding")

    age_days_valid = False
    stale_rows = 0
    if "age_days" in df.columns:
        age_days = pd.to_numeric(df["age_days"], errors="coerce")
        age_days_valid = bool(total_rows > 0 and age_days.notna().all())
        stale_rows = int(age_days.gt(settings.freshness_threshold_days).sum())

    stale_ratio = float(stale_rows / total_rows) if total_rows else 0.0

    checks = {
        "row_count_valid": bool(total_rows > 0),
        "required_columns_present": bool(not missing_columns),
        "paper_id_not_null": bool(missing_paper_ids == 0 and "paper_id" in df.columns),
        "paper_id_unique": bool(duplicate_paper_ids == 0 and "paper_id" in df.columns),
        "title_not_null": bool(empty_titles == 0 and "title" in df.columns),
        "summary_valid": bool(invalid_summaries == 0 and "summary" in df.columns),
        "embedding_text_valid": bool(empty_embedding_texts == 0 and "text_for_embedding" in df.columns),
        "age_days_valid": age_days_valid,
    }

    payload: dict[str, Any] = {
        "report_name": report_name,
        "total_rows": total_rows,
        "success": bool(all(checks.values())),
        "checks": checks,
        "statistics": {
            "missing_paper_ids": missing_paper_ids,
            "duplicate_paper_ids": duplicate_paper_ids,
            "empty_titles": empty_titles,
            "invalid_summaries": invalid_summaries,
            "empty_embedding_texts": empty_embedding_texts,
            "stale_rows": stale_rows,
            "stale_ratio": stale_ratio,
        },
    }
    if missing_columns:
        payload["missing_columns"] = missing_columns

    report_path = settings.paths.quality_dir / f"{report_name}.json"
    _write_json(report_path, payload)
    return _to_python(payload)


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build and persist a freshness summary for published dates and age."""
    total_rows = int(len(df))
    published = pd.Series(dtype="datetime64[ns]")
    age_days = pd.Series(dtype="float64")

    has_published = "published" in df.columns
    has_age_days = "age_days" in df.columns
    if has_published:
        published = pd.to_datetime(df["published"], errors="coerce")
    if has_age_days:
        age_days = pd.to_numeric(df["age_days"], errors="coerce")

    valid_published = bool(total_rows > 0 and has_published and published.notna().all())
    valid_age_days = bool(total_rows > 0 and has_age_days and age_days.notna().all())
    stale_rows = int(age_days.gt(settings.freshness_threshold_days).sum()) if has_age_days else 0
    stale_ratio = float(stale_rows / total_rows) if total_rows else 0.0

    latest_published = published.max() if has_published and published.notna().any() else None
    oldest_published = published.min() if has_published and published.notna().any() else None

    payload: dict[str, Any] = {
        "latest_published": _to_python(latest_published),
        "oldest_published": _to_python(oldest_published),
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "freshness_threshold_days": int(settings.freshness_threshold_days),
        "is_fresh": bool(valid_published and valid_age_days and stale_rows == 0),
    }

    _write_json(Path(report_path), payload)
    return _to_python(payload)
