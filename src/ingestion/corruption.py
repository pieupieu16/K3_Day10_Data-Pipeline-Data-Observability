from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import random

import pandas as pd

from core.utils import normalize_whitespace, write_json


CORRUPTION_SEED = 42
NOISE_TEXT = "[CORRUPTED] unrelated boilerplate noise 0000 ###"
REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "published",
    "authors_joined",
    "categories_joined",
    "text_for_embedding",
}


def _target_count(row_count: int, fraction: float = 0.15) -> int:
    return max(1, round(row_count * fraction)) if row_count else 0


def _embedding_text(row: pd.Series) -> str:
    # Keep the exact clean-data contract so untouched rows remain byte-for-byte
    # comparable with the baseline after text_for_embedding is rebuilt.
    return normalize_whitespace(
        f"Title: {row.get('title', '')}\n"
        f"Authors: {row.get('authors_joined', '')}\n"
        f"Categories: {row.get('categories_joined', '')}\n"
        f"Published: {row.get('published', '')}\n"
        f"Summary: {row.get('summary', '')}"
    )


def _pick_indices(indices: list[int], count: int, rng: random.Random, offset: int) -> list[int]:
    """Pick deterministic targets, preferring different rows for each corruption."""
    if not indices or count <= 0:
        return []
    rotated = indices[offset % len(indices) :] + indices[: offset % len(indices)]
    pool = rotated.copy()
    rng.shuffle(pool)
    return pool[: min(count, len(pool))]


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    """Create reproducible data defects and record every affected paper.

    The input frame is never mutated. The returned frame intentionally violates
    completeness, validity, freshness and uniqueness expectations so the same
    evaluation set can expose their impact on retrieval.
    """
    missing_columns = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing_columns:
        raise ValueError(f"Cannot corrupt dataframe; missing columns: {', '.join(missing_columns)}")
    if len(df) < 2:
        raise ValueError("At least two clean records are required for the corruption experiment.")

    corrupted = df.copy(deep=True).reset_index(drop=True)
    rng = random.Random(CORRUPTION_SEED)
    events: list[dict] = []

    # Removing recent papers directly attacks retrieval coverage for the fixed test set.
    published = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
    drop_count = min(_target_count(len(corrupted)), len(corrupted) - 1)
    latest_indices = published.sort_values(ascending=False, na_position="last").index[:drop_count].tolist()
    dropped_ids = corrupted.loc[latest_indices, "paper_id"].astype(str).tolist()
    corrupted = corrupted.drop(index=latest_indices).reset_index(drop=True)
    events.append(
        {
            "corruption_type": "drop_latest_records",
            "count": len(dropped_ids),
            "paper_ids": dropped_ids,
            "parameters": {"selection": "most recent published date"},
        }
    )

    indices = corrupted.index.tolist()
    mutation_count = _target_count(len(indices))

    blank_indices = _pick_indices(indices, mutation_count, rng, offset=0)
    blank_ids = corrupted.loc[blank_indices, "paper_id"].astype(str).tolist()
    corrupted.loc[blank_indices, "summary"] = ""
    events.append(
        {
            "corruption_type": "blank_summary",
            "count": len(blank_ids),
            "paper_ids": blank_ids,
            "parameters": {"replacement": "empty string"},
        }
    )

    noise_indices = _pick_indices(indices, mutation_count, rng, offset=mutation_count)
    noise_ids = corrupted.loc[noise_indices, "paper_id"].astype(str).tolist()
    corrupted.loc[noise_indices, "summary"] = corrupted.loc[noise_indices, "summary"].map(
        lambda value: normalize_whitespace(f"{value} {NOISE_TEXT}")
    )
    events.append(
        {
            "corruption_type": "summary_noise",
            "count": len(noise_ids),
            "paper_ids": noise_ids,
            "parameters": {"noise": NOISE_TEXT},
        }
    )

    title_indices = _pick_indices(indices, mutation_count, rng, offset=mutation_count * 2)
    title_ids = corrupted.loc[title_indices, "paper_id"].astype(str).tolist()
    corrupted.loc[title_indices, "title"] = corrupted.loc[title_indices, "title"].map(
        lambda value: normalize_whitespace(str(value))[:12]
    )
    events.append(
        {
            "corruption_type": "truncate_title",
            "count": len(title_ids),
            "paper_ids": title_ids,
            "parameters": {"max_characters": 12},
        }
    )

    stale_indices = _pick_indices(indices, mutation_count, rng, offset=mutation_count * 3)
    stale_ids = corrupted.loc[stale_indices, "paper_id"].astype(str).tolist()
    stale_date = (datetime.now(timezone.utc).date() - timedelta(days=3650)).isoformat()
    corrupted.loc[stale_indices, "published"] = stale_date
    if "age_days" in corrupted.columns:
        corrupted.loc[stale_indices, "age_days"] = 3650
    events.append(
        {
            "corruption_type": "stale_publication_date",
            "count": len(stale_ids),
            "paper_ids": stale_ids,
            "parameters": {"published": stale_date, "age_days": 3650},
        }
    )

    duplicate_count = min(_target_count(len(indices), fraction=0.10), len(corrupted))
    duplicate_indices = _pick_indices(indices, duplicate_count, rng, offset=mutation_count * 4)
    duplicate_rows = corrupted.loc[duplicate_indices].copy(deep=True)
    duplicate_ids = duplicate_rows["paper_id"].astype(str).tolist()
    corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)
    events.append(
        {
            "corruption_type": "duplicate_rows",
            "count": len(duplicate_ids),
            "paper_ids": duplicate_ids,
            "parameters": {"duplicate_keeps_same_paper_id": True},
        }
    )

    corrupted["summary_chars"] = corrupted["summary"].fillna("").astype(str).str.len()
    corrupted["text_for_embedding"] = corrupted.apply(_embedding_text, axis=1)

    write_json(
        output_log_path,
        {
            "seed": CORRUPTION_SEED,
            "input_rows": int(len(df)),
            "output_rows": int(len(corrupted)),
            "net_row_delta": int(len(corrupted) - len(df)),
            "events": events,
        },
    )
    return corrupted
