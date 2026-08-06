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

## Conclusion
- At least one measured metric decreased after corruption.
- At least one measured metric improved after repair.
- Repaired metrics still differ meaningfully from baseline on at least one numeric signal.
- Data quality improved from FAIL to PASS after repair.
- Freshness improved because repaired data has fewer stale rows.
