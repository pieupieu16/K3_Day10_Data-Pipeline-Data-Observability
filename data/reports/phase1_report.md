# Baseline Pipeline Report

## Source Summary
- Source: Crossref REST API
- Query/filter: agentic retrieval augmented generation large language model; from-pub-date:2026-02-07,has-abstract:true
- Raw records: 24
- Clean records: 24

## Evaluation Metrics
- Retrieval hit rate: N/A
- Mean token F1: N/A
- Judge accuracy: N/A
- Mean judge score: N/A

## Data Quality
- Status: PASS
- Total rows: 24
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
- Latest published: 2026-08-05
- Oldest published: 2026-02-12
- Stale rows: 0
- Stale ratio: 0
- Status: FRESH

## Conclusion
- Baseline data passed quality checks and is within the freshness threshold.
