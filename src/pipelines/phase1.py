from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def run_phase1_pipeline(settings: Settings) -> dict[str, object]:
    """Run baseline pipeline end-to-end with clean data."""
    paths = settings.paths

    # 1. Load or fetch raw records
    if settings.refresh_source or not paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(paths.raw_records_json)

    # 2. Clean data
    df = build_clean_dataframe(records, run_date=now_utc())

    # 3. Save clean CSV and JSON
    write_csv(df, paths.clean_csv)
    write_json(paths.clean_json, df.to_dict(orient="records"))

    # 4. Build Chroma vector index
    index = LocalEmbeddingIndex.build(
        df,
        settings=settings,
        embeddings_output_path=paths.embeddings_json,
    )

    # 5. Create or load evaluation test set
    if settings.refresh_test_set or not paths.eval_testset.exists():
        build_test_set(df, paths.eval_testset)

    # 6. Evaluate baseline RAG pipeline
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )

    # 7. Run data quality checks & freshness monitoring
    quality = run_data_quality_checks(df, settings, "baseline_quality")
    freshness = build_freshness_report(df, settings, paths.freshness_report)

    # 8. Generate baseline markdown report
    source_summary = {
        "source": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "raw_records": len(records),
        "clean_records": len(df),
    }
    generate_phase1_report(
        paths.baseline_report,
        source_summary,
        bundle.summary,
        quality,
        freshness,
    )

    return {
        "source_summary": source_summary,
        "baseline_metrics": bundle.summary,
        "quality": quality,
        "freshness": freshness,
        "baseline_report": str(paths.baseline_report),
    }


def main() -> None:
    settings = load_settings()
    result = run_phase1_pipeline(settings)
    print("Baseline (Phase 1) pipeline completed successfully!")
    print(f"Metrics: {result['baseline_metrics']}")
    print(f"Report path: {result['baseline_report']}")

