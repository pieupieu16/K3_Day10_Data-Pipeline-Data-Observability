# Corruption and Repair Report

## Metric Comparison
| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Retrieval hit rate | 0.9 | 0.55 | 0.88 |
| Mean token F1 | 0.82 | 0.5 | 0.8 |
| Judge accuracy | 0.75 | 0.5 | 0.75 |
| Mean judge score | 4.2 | 3 | 4 |

## Quality and Freshness Signals
| Signal | Corrupted | Repaired |
|---|---|---|
| Data quality | FAIL | PASS |
| Freshness | STALE | FRESH |
| Stale rows | 1 | 0 |

## Metric Changes
| Metric | Baseline to Corrupted | Corrupted to Repaired | Repaired vs Baseline |
|---|---:|---:|---:|
| Retrieval hit rate | 0.35 | 0.33 | -0.02 |
| Mean token F1 | 0.32 | 0.3 | -0.02 |
| Judge accuracy | 0.25 | 0.25 | 0 |
| Mean judge score | 1.2 | 1 | -0.2 |

## Experiment Contract
- Baseline, corrupted and repaired states use the same evaluation set and retrieval configuration.
- Corrupted and repaired data are indexed separately so baseline artifacts are not overwritten.
- Repair should be rebuilt from saved raw records and the normal cleaning pipeline.

## Evidence Delta Table
| Metric | Baseline | Corrupted | Repaired | Corrupted - baseline | Repaired - corrupted |
| --- | ---: | ---: | ---: | ---: | ---: |
| `retrieval_hit_rate` | 0.9000 | 0.5500 | 0.8800 | -0.3500 | 0.3300 |
| `mean_token_f1` | 0.8200 | 0.5000 | 0.8000 | -0.3200 | 0.3000 |
| `judge_accuracy` | 0.7500 | 0.5000 | 0.7500 | -0.2500 | 0.2500 |
| `mean_judge_score` | 4.2000 | 3.0000 | 4.0000 | -1.2000 | 1.0000 |

## Corrupted Data Quality
```json
{
  "report_name": "task3_bad_quality",
  "total_rows": 3,
  "success": false,
  "checks": {
    "row_count_valid": true,
    "required_columns_present": true,
    "paper_id_not_null": false,
    "paper_id_unique": false,
    "title_not_null": false,
    "summary_valid": false,
    "embedding_text_valid": false,
    "age_days_valid": false
  },
  "statistics": {
    "missing_paper_ids": 1,
    "duplicate_paper_ids": 1,
    "empty_titles": 1,
    "invalid_summaries": 2,
    "empty_embedding_texts": 2,
    "stale_rows": 1,
    "stale_ratio": 0.3333333333333333
  }
}
```

## Repaired Data Quality
```json
{
  "report_name": "task3_clean_quality",
  "total_rows": 2,
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
  "latest_published": "2026-07-01",
  "oldest_published": "2025-01-01",
  "stale_rows": 1,
  "total_rows": 3,
  "stale_ratio": 0.3333333333333333,
  "freshness_threshold_days": 180,
  "is_fresh": false
}
```

## Repaired Freshness
```json
{
  "latest_published": "2026-07-20",
  "oldest_published": "2026-07-10",
  "stale_rows": 0,
  "total_rows": 2,
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
- Repaired metrics still differ meaningfully from baseline on at least one numeric signal.
- Data quality improved from FAIL to PASS after repair.
- Freshness improved because repaired data has fewer stale rows.
