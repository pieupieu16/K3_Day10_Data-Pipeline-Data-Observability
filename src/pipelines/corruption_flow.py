from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _require_files(paths: list[Path]) -> None:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        formatted = "\n- ".join(missing)
        raise FileNotFoundError(
            "Corruption flow requires a completed baseline. Missing artifacts:\n- "
            f"{formatted}\nRun script/run_phase1.py first."
        )


def _load_clean_dataframe(path: Path) -> pd.DataFrame:
    payload = read_json(path)
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"Expected a non-empty JSON record list at {path}")
    return pd.DataFrame(payload)


def _save_dataframe(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))


def run_corruption_flow(settings: Settings) -> dict[str, object]:
    """Corrupt baseline data, measure impact, repair from raw, and compare."""
    paths = settings.paths
    _require_files(
        [
            paths.clean_json,
            paths.raw_records_json,
            paths.eval_testset,
            paths.baseline_metrics,
        ]
    )

    baseline_metrics = read_json(paths.baseline_metrics)
    baseline_df = _load_clean_dataframe(paths.clean_json)

    corrupted_df = corrupt_clean_dataframe(baseline_df, paths.corruption_log)
    _save_dataframe(corrupted_df, paths.corrupted_clean_csv, paths.corrupted_clean_json)
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings=settings,
        embeddings_output_path=paths.corrupted_embeddings_json,
    )
    corrupted_bundle = evaluate_pipeline(
        settings,
        corrupted_index,
        paths.eval_testset,
        paths.corrupted_metrics,
        paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        paths.quality_dir / "corrupted_freshness_report.json",
    )

    # Re-run the trusted transformation from the immutable raw snapshot.
    raw_records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date=now_utc())
    _save_dataframe(repaired_df, paths.repaired_clean_csv, paths.repaired_clean_json)
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings=settings,
        embeddings_output_path=paths.repaired_embeddings_json,
    )
    repaired_bundle = evaluate_pipeline(
        settings,
        repaired_index,
        paths.eval_testset,
        paths.repaired_metrics,
        paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        paths.quality_dir / "repaired_freshness_report.json",
    )

    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted_bundle.summary,
        repaired_bundle.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    return {
        "baseline_metrics": baseline_metrics,
        "corrupted_metrics": corrupted_bundle.summary,
        "repaired_metrics": repaired_bundle.summary,
        "comparison_report": str(paths.comparison_report),
    }


def main() -> None:
    result = run_corruption_flow(load_settings())
    print("Corruption and repair flow completed.")
    print(f"Comparison report: {result['comparison_report']}")
