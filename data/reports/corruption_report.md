# Corruption and Repair Report

## Metric Comparison
| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Retrieval hit rate | 1 | 0.525 | 1 |
| Mean token F1 | 0.5777 | 0.3951 | 0.5777 |
| Judge accuracy | 0.525 | 0.375 | 0.525 |
| Mean judge score | 3.05 | 2.45 | 3.05 |

## Quality and Freshness Signals
| Signal | Corrupted | Repaired |
|---|---|---|
| Data quality | FAIL | PASS |
| Freshness | STALE | FRESH |
| Stale rows | 4 | 0 |

## Metric Changes
| Metric | Baseline to Corrupted | Corrupted to Repaired | Repaired vs Baseline |
|---|---:|---:|---:|
| Retrieval hit rate | 0.475 | 0.475 | 0 |
| Mean token F1 | 0.1826 | 0.1826 | 0 |
| Judge accuracy | 0.15 | 0.15 | 0 |
| Mean judge score | 0.6 | 0.6 | 0 |

## Experiment Contract
- Baseline, corrupted and repaired states use the same evaluation set and retrieval configuration.
- Corrupted and repaired data are indexed separately so baseline artifacts are not overwritten.
- Repair should be rebuilt from saved raw records and the normal cleaning pipeline.

## Evidence Delta Table
| Metric | Baseline | Corrupted | Repaired | Corrupted - baseline | Repaired - corrupted |
| --- | ---: | ---: | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.0000 | 0.5250 | 1.0000 | -0.4750 | 0.4750 |
| `mean_token_f1` | 0.5777 | 0.3951 | 0.5777 | -0.1826 | 0.1826 |
| `judge_accuracy` | 0.5250 | 0.3750 | 0.5250 | -0.1500 | 0.1500 |
| `mean_judge_score` | 3.0500 | 2.4500 | 3.0500 | -0.6000 | 0.6000 |

## Corrupted Data Quality
```json
{
  "report_name": "corrupted_quality",
  "total_rows": 22,
  "success": false,
  "checks": {
    "row_count_valid": true,
    "required_columns_present": true,
    "paper_id_not_null": true,
    "paper_id_unique": false,
    "title_not_null": true,
    "summary_valid": false,
    "embedding_text_valid": true,
    "age_days_valid": true
  },
  "statistics": {
    "missing_paper_ids": 0,
    "duplicate_paper_ids": 2,
    "empty_titles": 0,
    "invalid_summaries": 3,
    "empty_embedding_texts": 0,
    "stale_rows": 4,
    "stale_ratio": 0.18181818181818182
  }
}
```

## Repaired Data Quality
```json
{
  "report_name": "repaired_quality",
  "total_rows": 24,
  "success": true,
  "checks": {
    "row_count_valid": true,
    "required_columns_present": true,
    "paper_id_not_null": true,
    "paper_id_unique": true,
    "title_not_null": true,
    "summary_valid": true,
    "embedding_text_valid": true,
    "age_days_valid": true
  },
  "statistics": {
    "missing_paper_ids": 0,
    "duplicate_paper_ids": 0,
    "empty_titles": 0,
    "invalid_summaries": 0,
    "empty_embedding_texts": 0,
    "stale_rows": 0,
    "stale_ratio": 0.0
  }
}
```

## Corrupted Freshness
```json
{
  "latest_published": "2026-07-02",
  "oldest_published": "2016-08-08",
  "stale_rows": 4,
  "total_rows": 22,
  "stale_ratio": 0.18181818181818182,
  "freshness_threshold_days": 180,
  "is_fresh": false
}
```

## Repaired Freshness
```json
{
  "latest_published": "2026-08-05",
  "oldest_published": "2026-02-12",
  "stale_rows": 0,
  "total_rows": 24,
  "stale_ratio": 0.0,
  "freshness_threshold_days": 180,
  "is_fresh": true
}
```

## Evidence
- Corruption artifacts should be traceable through `data/results/corruption_log.json`.
- Answer-level retrieval and judge details should be inspected when metric deltas are small.

## Conclusion
- At least one measured metric decreased after corruption.
- At least one measured metric improved after repair.
- Repaired metrics are close to baseline on the available numeric signals.
- Data quality improved from FAIL to PASS after repair.
- Freshness improved because repaired data has fewer stale rows.
