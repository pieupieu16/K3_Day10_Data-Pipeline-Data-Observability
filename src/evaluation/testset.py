from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import ensure_parent, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Create a small evaluation set from the cleaned dataframe."""
    if df is None or df.empty:
        return []

    sample_df = df.head(min(6, len(df))).copy()
    if len(sample_df) < 1:
        return []

    items: list[dict[str, Any]] = []
    for idx, row in sample_df.iterrows():
        paper_id = str(row["paper_id"])
        title = str(row["title"])
        authors = ", ".join(row["authors"]) if isinstance(row["authors"], list) else str(row["authors"])
        categories = ", ".join(row["categories"]) if isinstance(row["categories"], list) else str(row["categories"])
        published = str(row["published"])

        if idx == 0:
            items.append(
                {
                    "id": f"{paper_id}-summary",
                    "question_type": "summary",
                    "question": f"What is the main contribution of the paper titled '{title}'?",
                    "ground_truth": str(row["summary"]),
                    "ground_truth_doc_ids": [paper_id],
                }
            )

        items.append(
            {
                "id": f"{paper_id}-authors",
                "question_type": "authors",
                "question": f"Who are the authors of the paper '{title}'?",
                "ground_truth": authors,
                "ground_truth_doc_ids": [paper_id],
            }
        )

        if published:
            items.append(
                {
                    "id": f"{paper_id}-date",
                    "question_type": "date",
                    "question": f"When was the paper '{title}' published?",
                    "ground_truth": published,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

        if categories:
            items.append(
                {
                    "id": f"{paper_id}-categories",
                    "question_type": "categories",
                    "question": f"Which categories describe the paper '{title}'?",
                    "ground_truth": categories,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    if output_path is not None:
        output_path = Path(output_path)
        ensure_parent(output_path)
        write_json(output_path, items)

    return items
