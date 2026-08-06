# Baseline vs. Corrupted Data Comparison

## Files compared

- Baseline: `data/clean/papers_clean.json`
- Corrupted: `data/clean/papers_clean_corrupted.json`

## Summary

| Signal | Value |
| --- | ---: |
| Baseline rows | 24 |
| Corrupted rows | 22 |
| Removed paper IDs | 4 |
| Modified paper IDs | 8 |
| Duplicated paper IDs | 1 |
| Modified and duplicated paper IDs | 1 |
| Unchanged paper IDs | 10 |

## Changed records

| Paper ID | Status | Changed fields | Occurrences after corruption |
| --- | --- | --- | ---: |
| `10.2118/234689-pa` | removed | record | 0 |
| `10.1007/s10278-026-02086-9` | removed | record | 0 |
| `10.21203/rs.3.rs-10178277/v1` | removed | record | 0 |
| `10.2196/preprints.106157` | removed | record | 0 |
| `10.1111/exsy.70341` | modified_and_duplicated | published, age_days, text_for_embedding, duplicate_count | 2 |
| `10.47576/2949-1894.2026.7.7.023` | duplicated | duplicate_count | 2 |
| `10.21203/rs.3.rs-10012178/v1` | modified | title, summary, text_for_embedding | 1 |
| `10.21203/rs.3.rs-9882260/v1` | modified | title, summary, text_for_embedding | 1 |
| `10.22214/ijraset.2026.82233` | modified | published, age_days, text_for_embedding | 1 |
| `10.1093/sleep/zsag091.0346` | modified | summary, text_for_embedding | 1 |
| `10.20944/preprints202604.0339.v1` | modified | summary, text_for_embedding | 1 |
| `10.70121/001c.158711` | modified | title, text_for_embedding | 1 |
| `10.3390/app16052244` | modified | summary, text_for_embedding | 1 |
| `10.20944/preprints202602.0996.v1` | modified | summary, published, age_days, text_for_embedding | 1 |
