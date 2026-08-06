from __future__ import annotations

from observability.reporting import generate_corruption_report


def test_corruption_report_contains_metrics_deltas_and_quality_evidence(tmp_path) -> None:
    report_path = tmp_path / "report.md"
    generate_corruption_report(
        report_path,
        baseline_metrics={"retrieval_hit_rate": 1.0, "mean_token_f1": 0.9},
        corrupted_metrics={"retrieval_hit_rate": 0.5, "mean_token_f1": 0.4},
        repaired_metrics={"retrieval_hit_rate": 0.9, "mean_token_f1": 0.8},
        corrupted_quality={"passed": False, "duplicate_rows": 2},
        repaired_quality={"passed": True, "duplicate_rows": 0},
        corrupted_freshness={"is_fresh": False},
        repaired_freshness={"is_fresh": True},
    )

    report = report_path.read_text(encoding="utf-8")
    assert "| `retrieval_hit_rate` | 1.0000 | 0.5000 | 0.9000 | -0.5000 | 0.4000 |" in report
    assert '"duplicate_rows": 2' in report
    assert '"is_fresh": true' in report
    assert "same evaluation set" in report
