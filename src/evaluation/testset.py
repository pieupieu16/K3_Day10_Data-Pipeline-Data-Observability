from typing import Any

import pandas as pd

from core.utils import write_json


def build_test_set(df: pd.DataFrame, output_path=None) -> list[dict[str, Any]]:
    """Build evaluation test set from cleaned dataframe containing questions for summary, authors, date, categories.

    1. Check minimum number of documents.
    2. Select representative papers from df.
    3. Generate 4 question types per paper: summary, authors, date, categories.
    4. Format entries with id, question_type, question, ground_truth, ground_truth_doc_ids.
    5. Write JSON to output_path if provided.
    """
    if df.empty:
        raise ValueError("Cannot build test set from an empty DataFrame.")

    test_samples: list[dict[str, Any]] = []
    # Take representative papers (up to 10 papers)
    selected_rows = df.head(10).to_dict(orient="records")

    sample_id = 1
    for row in selected_rows:
        paper_id = row["paper_id"]
        title = row["title"]
        summary = row["summary"]
        authors = row["authors_joined"]
        published = row["published"]
        categories = row["categories_joined"]

        # 1. Summary Question
        test_samples.append(
            {
                "id": f"eval-{sample_id:03d}",
                "question_type": "summary",
                "question": f"What is the summary of the paper '{title}'?",
                "ground_truth": summary,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        sample_id += 1

        # 2. Authors Question
        test_samples.append(
            {
                "id": f"eval-{sample_id:03d}",
                "question_type": "authors",
                "question": f"Who are the authors of the paper '{title}'?",
                "ground_truth": authors,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        sample_id += 1

        # 3. Date Question
        test_samples.append(
            {
                "id": f"eval-{sample_id:03d}",
                "question_type": "date",
                "question": f"When was the paper '{title}' published?",
                "ground_truth": published,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        sample_id += 1

        # 4. Categories Question
        test_samples.append(
            {
                "id": f"eval-{sample_id:03d}",
                "question_type": "categories",
                "question": f"What categories or subjects are associated with the paper '{title}'?",
                "ground_truth": categories,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        sample_id += 1

    if output_path:
        write_json(output_path, test_samples)

    return test_samples

