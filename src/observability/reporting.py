from __future__ import annotations

import json
from pathlib import Path
from typing import Any


METRICS = (
    ("retrieval_hit_rate", "Retrieval hit rate"),
    ("mean_token_f1", "Mean token F1"),
    ("judge_accuracy", "Judge accuracy"),
    ("mean_judge_score", "Mean judge score"),
)


def _format_value(value: Any) -> str:
    """Format report values with stable handling for missing data."""
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value) if str(value) else "N/A"


def _metric(metrics: dict[str, Any], key: str) -> Any:
    """Return a metric value or None when it is unavailable."""
    value = metrics.get(key)
    return value if isinstance(value, int | float) and not isinstance(value, bool) else value


def _as_float(value: Any) -> float | None:
    """Convert numeric values to float for comparisons."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_value(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Fetch the first present value from a set of possible keys."""
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _status(value: bool | None, pass_label: str, fail_label: str) -> str:
    """Render a status label from a boolean field."""
    if value is None:
        return "N/A"
    return pass_label if value else fail_label


def _write_markdown(report_path, lines: list[str]) -> None:
    """Write a Markdown report using UTF-8."""
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _quality_status(quality: dict[str, Any]) -> str:
    return _status(quality.get("success") if "success" in quality else None, "PASS", "FAIL")


def _freshness_status(freshness: dict[str, Any]) -> str:
    return _status(freshness.get("is_fresh") if "is_fresh" in freshness else None, "FRESH", "STALE")


def _json_block(payload: dict[str, Any]) -> str:
    """Serialize supporting evidence for Markdown code blocks."""
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Generate the baseline pipeline Markdown report."""
    quality_status = _quality_status(quality)
    freshness_status = _freshness_status(freshness)
    checks = quality.get("checks", {}) if isinstance(quality.get("checks"), dict) else {}
    statistics = quality.get("statistics", {}) if isinstance(quality.get("statistics"), dict) else {}

    if quality.get("success") and freshness.get("is_fresh"):
        conclusion = "Baseline data passed quality checks and is within the freshness threshold."
    elif not quality.get("success") and freshness.get("is_fresh"):
        conclusion = "Baseline data is fresh, but quality checks found issues that should be fixed before relying on the results."
    elif quality.get("success") and not freshness.get("is_fresh"):
        conclusion = "Baseline data passed structural quality checks, but freshness monitoring found stale records."
    else:
        conclusion = "Baseline data has quality and freshness issues that can affect downstream retrieval and answer quality."

    lines = [
        "# Baseline Pipeline Report",
        "",
        "## Source Summary",
        f"- Source: {_format_value(_first_value(source_summary, ('source', 'source_api', 'api')))}",
        f"- Query/filter: {_format_value(_first_value(source_summary, ('query', 'source_query', 'filter', 'source_filter')))}",
        f"- Raw records: {_format_value(_first_value(source_summary, ('raw_records', 'raw_record_count', 'raw_records_count')))}",
        f"- Clean records: {_format_value(_first_value(source_summary, ('clean_records', 'clean_record_count', 'clean_records_count')))}",
        "",
        "## Evaluation Metrics",
    ]

    lines.extend(f"- {label}: {_format_value(_metric(metrics, key))}" for key, label in METRICS)
    lines.extend(
        [
            "",
            "## Data Quality",
            f"- Status: {quality_status}",
            f"- Total rows: {_format_value(quality.get('total_rows'))}",
            "- Quality checks:",
        ]
    )
    lines.extend(f"  - {key}: {_format_value(value)}" for key, value in checks.items())
    lines.append("- Error statistics:")
    lines.extend(f"  - {key}: {_format_value(value)}" for key, value in statistics.items())
    lines.extend(
        [
            "",
            "## Freshness",
            f"- Latest published: {_format_value(freshness.get('latest_published'))}",
            f"- Oldest published: {_format_value(freshness.get('oldest_published'))}",
            f"- Stale rows: {_format_value(freshness.get('stale_rows'))}",
            f"- Stale ratio: {_format_value(freshness.get('stale_ratio'))}",
            f"- Status: {freshness_status}",
            "",
            "## Conclusion",
            f"- {conclusion}",
        ]
    )

    _write_markdown(report_path, lines)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Generate a Markdown comparison for baseline, corrupted, and repaired states."""
    lines = [
        "# Corruption and Repair Report",
        "",
        "## Metric Comparison",
        "| Metric | Baseline | Corrupted | Repaired |",
        "|---|---:|---:|---:|",
    ]
    for key, label in METRICS:
        lines.append(
            "| "
            f"{label} | {_format_value(_metric(baseline_metrics, key))} | "
            f"{_format_value(_metric(corrupted_metrics, key))} | "
            f"{_format_value(_metric(repaired_metrics, key))} |"
        )

    lines.extend(
        [
            "",
            "## Quality and Freshness Signals",
            "| Signal | Corrupted | Repaired |",
            "|---|---|---|",
            f"| Data quality | {_quality_status(corrupted_quality)} | {_quality_status(repaired_quality)} |",
            f"| Freshness | {_freshness_status(corrupted_freshness)} | {_freshness_status(repaired_freshness)} |",
            f"| Stale rows | {_format_value(corrupted_freshness.get('stale_rows'))} | {_format_value(repaired_freshness.get('stale_rows'))} |",
            "",
            "## Metric Changes",
            "| Metric | Baseline to Corrupted | Corrupted to Repaired | Repaired vs Baseline |",
            "|---|---:|---:|---:|",
        ]
    )

    available_changes: list[tuple[str, float, float, float]] = []
    compatibility_rows: list[str] = []
    for key, label in METRICS:
        baseline = _as_float(_metric(baseline_metrics, key))
        corrupted = _as_float(_metric(corrupted_metrics, key))
        repaired = _as_float(_metric(repaired_metrics, key))
        degradation = None if baseline is None or corrupted is None else corrupted - baseline
        recovery = None if repaired is None or corrupted is None else repaired - corrupted
        compatibility_rows.append(
            f"| `{key}` | {_format_fixed(baseline)} | {_format_fixed(corrupted)} | {_format_fixed(repaired)} "
            f"| {_format_fixed(degradation)} | {_format_fixed(recovery)} |"
        )
        if baseline is None or corrupted is None or repaired is None:
            lines.append(f"| {label} | N/A | N/A | N/A |")
            continue

        drop = baseline - corrupted
        gain = repaired - corrupted
        gap = repaired - baseline
        available_changes.append((label, drop, gain, gap))
        lines.append(f"| {label} | {_format_value(drop)} | {_format_value(gain)} | {_format_value(gap)} |")

    conclusions = _build_corruption_conclusions(
        available_changes=available_changes,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    lines.extend(
        [
            "",
            "## Experiment Contract",
            "- Baseline, corrupted and repaired states use the same evaluation set and retrieval configuration.",
            "- Corrupted and repaired data are indexed separately so baseline artifacts are not overwritten.",
            "- Repair should be rebuilt from saved raw records and the normal cleaning pipeline.",
            "",
            "## Evidence Delta Table",
            "| Metric | Baseline | Corrupted | Repaired | Corrupted - baseline | Repaired - corrupted |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
            *compatibility_rows,
            "",
            "## Corrupted Data Quality",
            "```json",
            _json_block(corrupted_quality),
            "```",
            "",
            "## Repaired Data Quality",
            "```json",
            _json_block(repaired_quality),
            "```",
            "",
            "## Corrupted Freshness",
            "```json",
            _json_block(corrupted_freshness),
            "```",
            "",
            "## Repaired Freshness",
            "```json",
            _json_block(repaired_freshness),
            "```",
            "",
            "## Evidence",
            "- Corruption artifacts should be traceable through `data/results/corruption_log.json`.",
            "- Answer-level retrieval and judge details should be inspected when metric deltas are small.",
            "",
            "## Conclusion",
        ]
    )
    lines.extend(f"- {item}" for item in conclusions)

    _write_markdown(report_path, lines)


def _format_fixed(value: float | None) -> str:
    """Format optional floats with four decimals for upstream report tests."""
    return "N/A" if value is None else f"{value:.4f}"


def _build_corruption_conclusions(
    available_changes: list[tuple[str, float, float, float]],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> list[str]:
    """Summarize corruption and repair impact from available metrics."""
    corruption_drops = [drop for _, drop, _, _ in available_changes]
    repair_gains = [gain for _, _, gain, _ in available_changes]
    repaired_gaps = [gap for _, _, _, gap in available_changes]

    conclusions: list[str] = []
    if corruption_drops:
        if any(drop > 0 for drop in corruption_drops):
            conclusions.append("At least one measured metric decreased after corruption.")
        elif all(drop == 0 for drop in corruption_drops):
            conclusions.append("The available metrics did not change after corruption.")
        else:
            conclusions.append("The available metrics do not show a degradation after corruption.")
    else:
        conclusions.append("Metric degradation could not be determined because comparable metric values are missing.")

    if repair_gains:
        if any(gain > 0 for gain in repair_gains):
            conclusions.append("At least one measured metric improved after repair.")
        elif all(gain == 0 for gain in repair_gains):
            conclusions.append("Repair left the available metrics unchanged.")
        else:
            conclusions.append("The available metrics do not show recovery after repair.")

    if repaired_gaps:
        max_abs_gap = max(abs(gap) for gap in repaired_gaps)
        if max_abs_gap <= 0.05:
            conclusions.append("Repaired metrics are close to baseline on the available numeric signals.")
        else:
            conclusions.append("Repaired metrics still differ meaningfully from baseline on at least one numeric signal.")

    corrupted_stale = _as_float(corrupted_freshness.get("stale_rows"))
    repaired_stale = _as_float(repaired_freshness.get("stale_rows"))
    if corrupted_quality.get("success") is False and repaired_quality.get("success") is True:
        conclusions.append("Data quality improved from FAIL to PASS after repair.")
    elif corrupted_quality.get("success") == repaired_quality.get("success"):
        conclusions.append("Data quality status did not change after repair.")

    if corrupted_stale is not None and repaired_stale is not None:
        if repaired_stale < corrupted_stale:
            conclusions.append("Freshness improved because repaired data has fewer stale rows.")
        elif repaired_stale == corrupted_stale:
            conclusions.append("Freshness stale-row count did not change after repair.")
        else:
            conclusions.append("Freshness worsened because repaired data has more stale rows.")

    return conclusions
