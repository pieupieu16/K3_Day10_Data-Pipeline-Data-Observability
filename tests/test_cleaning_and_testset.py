from __future__ import annotations

from datetime import datetime

from ingestion.crossref import PaperRecord
from ingestion.cleaning import build_clean_dataframe
from evaluation.testset import build_test_set


def test_cleaning_and_testset_pipeline(tmp_path):
    records = [
        PaperRecord(
            paper_id="10.1000/test1",
            title="  Agentic RAG for Science  ",
            summary="Abstract: This paper studies agentic retrieval augmented generation.",
            authors=["Ada Lovelace", "Grace Hopper"],
            categories=["Computer Science", "Machine Learning"],
            primary_category="Computer Science",
            published="2024-01-10",
            updated="2024-01-12",
            abs_url="https://doi.org/10.1000/test1",
            pdf_url="https://doi.org/10.1000/test1.pdf",
            comment="Journal",
        ),
        PaperRecord(
            paper_id="10.1000/test2",
            title="Agentic RAG for Science",
            summary="",
            authors=["Ada Lovelace", "Ada Lovelace"],
            categories=["Computer Science"],
            primary_category="Computer Science",
            published="",
            updated="",
            abs_url="https://doi.org/10.1000/test2",
            pdf_url="https://doi.org/10.1000/test2.pdf",
            comment="Journal",
        ),
    ]

    df = build_clean_dataframe(records, datetime(2024, 1, 20))
    assert not df.empty
    assert "text_for_embedding" in df.columns
    assert "age_days" in df.columns
    assert df["paper_id"].nunique() == 1

    output_path = tmp_path / "test_set.json"
    test_set = build_test_set(df, output_path)
    assert len(test_set) >= 2
    assert output_path.exists()
    assert all("ground_truth_doc_ids" in item for item in test_set)
