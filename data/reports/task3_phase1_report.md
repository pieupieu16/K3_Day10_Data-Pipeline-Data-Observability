# Baseline Pipeline Report

## Source Summary
- Source: Synthetic validation data
- Query/filter: observability task3 validation
- Raw records: 2
- Clean records: 2

## Evaluation Metrics
- Retrieval hit rate: 0.9
- Mean token F1: 0.82
- Judge accuracy: 0.75
- Mean judge score: 4.2

## Data Quality
- Status: PASS
- Total rows: 2
- Quality checks:
  - row_count_valid: PASS
  - required_columns_present: PASS
  - paper_id_not_null: PASS
  - paper_id_unique: PASS
  - title_not_null: PASS
  - summary_valid: PASS
  - embedding_text_valid: PASS
  - age_days_valid: PASS
- Error statistics:
  - missing_paper_ids: 0
  - duplicate_paper_ids: 0
  - empty_titles: 0
  - invalid_summaries: 0
  - empty_embedding_texts: 0
  - stale_rows: 0
  - stale_ratio: 0

## Freshness
- Latest published: 2026-07-20
- Oldest published: 2026-07-10
- Stale rows: 0
- Stale ratio: 0
- Status: FRESH

## Conclusion
- Baseline data passed quality checks and is within the freshness threshold.
