from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pandas as pd
import pytest

from ingestion.corruption import CORRUPTION_SEED, NOISE_TEXT, corrupt_clean_dataframe


def clean_frame(rows: int = 12) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "paper_id": f"10.1000/{index:02d}",
                "title": f"A sufficiently descriptive paper title number {index}",
                "summary": f"A useful scholarly abstract for paper {index}.",
                "published": f"2026-07-{index + 1:02d}",
                "age_days": index + 1,
                "authors_joined": f"Author {index}",
                "categories_joined": "Artificial Intelligence, Retrieval",
                "summary_chars": 42,
                "text_for_embedding": f"Original embedding text {index}",
                "abs_url": f"https://doi.org/10.1000/{index:02d}",
                "pdf_url": "",
            }
            for index in range(rows)
        ]
    )


def test_corruption_is_reproducible_logged_and_does_not_mutate_input(tmp_path) -> None:
    original = clean_frame()
    before = original.copy(deep=True)
    first_log = tmp_path / "first.json"
    second_log = tmp_path / "second.json"

    first = corrupt_clean_dataframe(original, first_log)
    second = corrupt_clean_dataframe(original, second_log)

    pd.testing.assert_frame_equal(original, before)
    pd.testing.assert_frame_equal(first, second)
    assert json.loads(first_log.read_text())["seed"] == CORRUPTION_SEED
    assert json.loads(first_log.read_text()) == json.loads(second_log.read_text())


def test_corruption_injects_all_expected_defect_types(tmp_path) -> None:
    original = clean_frame()
    corrupted = corrupt_clean_dataframe(original, tmp_path / "corruption.json")
    log = json.loads((tmp_path / "corruption.json").read_text())
    event_types = {event["corruption_type"] for event in log["events"]}

    assert event_types == {
        "drop_latest_records",
        "blank_summary",
        "summary_noise",
        "truncate_title",
        "stale_publication_date",
        "duplicate_rows",
    }
    assert corrupted["paper_id"].duplicated().any()
    assert (corrupted["summary"] == "").any()
    assert corrupted["summary"].str.contains(NOISE_TEXT, regex=False).any()
    assert (corrupted["title"].str.len() <= 12).any()
    assert (pd.to_datetime(corrupted["published"], utc=True).dt.year < 2020).any()
    assert corrupted["text_for_embedding"].str.startswith("Title:").all()
    assert log["input_rows"] == len(original)
    assert log["output_rows"] == len(corrupted)


def test_corruption_rejects_invalid_inputs(tmp_path) -> None:
    with pytest.raises(ValueError, match="missing columns"):
        corrupt_clean_dataframe(pd.DataFrame({"paper_id": ["x", "y"]}), tmp_path / "log.json")

    with pytest.raises(ValueError, match="At least two"):
        corrupt_clean_dataframe(clean_frame(1), tmp_path / "log.json")
