# Corruption Data Report

## Run summary

| Signal | Baseline | Corrupted | Delta |
| --- | ---: | ---: | ---: |
| Rows | 24 | 22 | -2 |
| Unique paper IDs | 24 | 20 | -4 |
| Blank summaries | 0 | 3 | +3 |
| Rows participating in duplicate IDs | 0 | 4 | +4 |
| Summaries containing injected noise | 0 | 3 | +3 |

## Injected events

Seed: `42`

| Corruption | Target count | Paper IDs |
| --- | ---: | --- |
| `drop_latest_records` | 4 | 10.2118/234689-pa, 10.1007/s10278-026-02086-9, 10.21203/rs.3.rs-10178277/v1, 10.2196/preprints.106157 |
| `blank_summary` | 3 | 10.20944/preprints202602.0996.v1, 10.21203/rs.3.rs-10012178/v1, 10.20944/preprints202604.0339.v1 |
| `summary_noise` | 3 | 10.3390/app16052244, 10.1093/sleep/zsag091.0346, 10.21203/rs.3.rs-9882260/v1 |
| `truncate_title` | 3 | 10.70121/001c.158711, 10.21203/rs.3.rs-9882260/v1, 10.21203/rs.3.rs-10012178/v1 |
| `stale_publication_date` | 3 | 10.20944/preprints202602.0996.v1, 10.22214/ijraset.2026.82233, 10.1111/exsy.70341 |
| `duplicate_rows` | 2 | 10.47576/2949-1894.2026.7.7.023, 10.1111/exsy.70341 |

## Scope of this result

This report verifies data-level corruption against the Task 1 clean artifact. Retrieval, answer and judge metrics are not included yet because `baseline_metrics.json` and the baseline Chroma index have not been produced. Once those artifacts exist, run `uv run python script/run_corruption_flow.py` to generate the full baseline/corrupted/repaired comparison.
