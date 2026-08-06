from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _normalize_list(items: list[str] | None) -> list[str]:
    if not items:
        return []
    normalized: list[str] = []
    for item in items:
        cleaned = normalize_whitespace(str(item))
        if cleaned:
            normalized.append(cleaned)
    return normalized


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a dataframe ready for embedding and evaluation."""
    rows: list[dict[str, Any]] = []

    for record in records:
        title = normalize_whitespace(record.title or "")
        summary = normalize_whitespace(re.sub(r"^(abstract|ABSTRACT)[:\s]*", "", (record.summary or "")))
        authors = _normalize_list(record.authors)
        categories = _normalize_list(record.categories)

        if not title or not summary:
            continue

        published_dt = _parse_date(record.published)
        updated_dt = _parse_date(record.updated) or published_dt
        if published_dt is None and updated_dt is None:
            continue

        if published_dt is None:
            published_dt = updated_dt
        if updated_dt is None:
            updated_dt = published_dt

        age_days = (run_date.date() - published_dt.date()).days if published_dt else None
        if age_days is not None and age_days < 0:
            age_days = 0

        authors_joined = compact_join(authors, ", ")
        categories_joined = compact_join(categories, ", ")

        text_for_embedding = " | ".join(
            part for part in [title, summary, authors_joined, categories_joined] if part
        )

        rows.append(
            {
                "paper_id": record.paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": record.primary_category or (categories[0] if categories else ""),
                "published": record.published,
                "updated": record.updated,
                "published_dt": published_dt,
                "updated_dt": updated_dt,
                "age_days": age_days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
            }
        )

    if not rows:
        return pd.DataFrame(columns=[
            "paper_id",
            "title",
            "summary",
            "authors",
            "categories",
            "primary_category",
            "published",
            "updated",
            "published_dt",
            "updated_dt",
            "age_days",
            "authors_joined",
            "categories_joined",
            "summary_chars",
            "text_for_embedding",
            "abs_url",
            "pdf_url",
            "comment",
        ])

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["paper_id", "title"], keep="first").reset_index(drop=True)
    df = df.sort_values(by=["published_dt", "paper_id"], ascending=[False, True], kind="mergesort").reset_index(drop=True)
    df["authors"] = df["authors"].apply(lambda values: values if isinstance(values, list) else [])
    df["categories"] = df["categories"].apply(lambda values: values if isinstance(values, list) else [])
    return df
