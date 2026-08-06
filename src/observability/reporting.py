from __future__ import annotations

import json
from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report cho baseline phase.

    Pseudo-code:
    1. Gom source summary.
    2. In metrics retrieval/evaluation.
    3. In data quality va freshness.
    4. Ghi markdown vao report_path.
    """
    raise NotImplementedError("Student task: implement phase 1 report.")


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
    """Write an evidence-based baseline/corrupted/repaired comparison."""
    metric_names = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")

    def number(payload: dict[str, Any], key: str) -> float | None:
        value = payload.get(key)
        return float(value) if isinstance(value, (int, float)) else None

    def fmt(value: float | None) -> str:
        return "N/A" if value is None else f"{value:.4f}"

    rows = []
    for name in metric_names:
        baseline = number(baseline_metrics, name)
        corrupted = number(corrupted_metrics, name)
        repaired = number(repaired_metrics, name)
        degradation = None if baseline is None or corrupted is None else corrupted - baseline
        recovery = None if repaired is None or corrupted is None else repaired - corrupted
        rows.append(
            f"| `{name}` | {fmt(baseline)} | {fmt(corrupted)} | {fmt(repaired)} "
            f"| {fmt(degradation)} | {fmt(recovery)} |"
        )

    def json_block(payload: dict[str, Any]) -> str:
        return json.dumps(payload, indent=2, ensure_ascii=False, default=str)

    report = f"""# Corruption and Repair Comparison Report

## Experiment contract

- Baseline, corrupted and repaired states use the same evaluation set and retrieval configuration.
- Corrupted and repaired data are indexed in separate collections; baseline artifacts are not overwritten.
- Repair is rebuilt from the saved raw records and the normal cleaning pipeline, not by editing answers or metrics.

## Evaluation comparison

| Metric | Baseline | Corrupted | Repaired | Corrupted − baseline | Repaired − corrupted |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(rows)}

A negative `Corrupted − baseline` value indicates degradation for these higher-is-better metrics. A positive
`Repaired − corrupted` value indicates recovery. Exact recovery is not guaranteed when ranking contains ties or
when an external judge is non-deterministic; the answer artifacts should be inspected before drawing conclusions.

## Corrupted data quality

```json
{json_block(corrupted_quality)}
```

## Repaired data quality

```json
{json_block(repaired_quality)}
```

## Corrupted freshness

```json
{json_block(corrupted_freshness)}
```

## Repaired freshness

```json
{json_block(repaired_freshness)}
```

## Evidence and interpretation

Use `data/results/corruption_log.json` to trace each injected defect to its paper IDs. Detailed retrieval hits,
answers and judge results are stored separately for corrupted and repaired states under `data/results/`.
Conclusions should only claim an impact when the metric delta or answer-level evidence above supports it.
"""
    write_text(report_path, report)
