from datetime import datetime
from pathlib import Path
import re
from typing import Any

import pandas as pd

from core.utils import normalize_whitespace
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
    """Clean raw records into a normalized pandas DataFrame ready for embedding.

    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Calculate age_days relative to run_date.
    4. Create helper columns:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates and filter bad/invalid rows.
    6. Sort dataframe by published date descending and return.
    """
    rows: list[dict] = []
    run_dt = run_date.date() if isinstance(run_date, datetime) else run_date

    for r in records:
        title = normalize_whitespace(r.title or "")
        summary = normalize_whitespace(r.summary or "")

        # Filter invalid rows (empty title or summary under 20 chars)
        if not title or not summary or len(summary) < 20:
            continue

        authors = [normalize_whitespace(a) for a in (r.authors or []) if a]
        authors_joined = ", ".join(authors) if authors else "Unknown"

        categories = [normalize_whitespace(c) for c in (r.categories or []) if c]
        categories_joined = ", ".join(categories) if categories else "General"
        primary_category = r.primary_category or (categories[0] if categories else "General")

        published_str = (r.published or "").strip()
        updated_str = (r.updated or "").strip() or published_str

        age_days = 0
        if published_str:
            try:
                pub_date = datetime.strptime(published_str[:10], "%Y-%m-%d").date()
                age_days = max(0, (run_dt - pub_date).days)
            except Exception:
                age_days = 0

        summary_chars = len(summary)

        text_for_embedding = normalize_whitespace(
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Categories: {categories_joined}\n"
            f"Published: {published_str}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": r.paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "authors_joined": authors_joined,
                "categories": categories,
                "categories_joined": categories_joined,
                "primary_category": primary_category,
                "published": published_str,
                "updated": updated_str,
                "age_days": age_days,
                "summary_chars": summary_chars,
                "abs_url": r.abs_url or f"https://doi.org/{r.paper_id}",
                "pdf_url": r.pdf_url or r.abs_url or f"https://doi.org/{r.paper_id}",
                "comment": r.comment or "",
                "text_for_embedding": text_for_embedding,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "paper_id",
                "title",
                "summary",
                "authors",
                "authors_joined",
                "categories",
                "categories_joined",
                "primary_category",
                "published",
                "updated",
                "age_days",
                "summary_chars",
                "abs_url",
                "pdf_url",
                "comment",
                "text_for_embedding",
            ]
        )

    df = pd.DataFrame(rows)

    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df.drop_duplicates(subset=["title"], keep="first")
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)

    return df

