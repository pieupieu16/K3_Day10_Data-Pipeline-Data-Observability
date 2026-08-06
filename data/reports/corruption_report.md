# Corruption and Repair Report

## Metric Comparison
| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Retrieval hit rate | N/A | N/A | N/A |
| Mean token F1 | N/A | N/A | N/A |
| Judge accuracy | N/A | N/A | N/A |
| Mean judge score | N/A | N/A | N/A |

## Quality and Freshness Signals
| Signal | Corrupted | Repaired |
|---|---|---|
| Data quality | N/A | N/A |
| Freshness | N/A | N/A |
| Stale rows | N/A | N/A |

## Metric Changes
| Metric | Baseline to Corrupted | Corrupted to Repaired | Repaired vs Baseline |
|---|---:|---:|---:|
| Retrieval hit rate | N/A | N/A | N/A |
| Mean token F1 | N/A | N/A | N/A |
| Judge accuracy | N/A | N/A | N/A |
| Mean judge score | N/A | N/A | N/A |

## Experiment Contract
- Baseline, corrupted and repaired states use the same evaluation set and retrieval configuration.
- Corrupted and repaired data are indexed separately so baseline artifacts are not overwritten.
- Repair should be rebuilt from saved raw records and the normal cleaning pipeline.

## Evidence Delta Table
| Metric | Baseline | Corrupted | Repaired | Corrupted - baseline | Repaired - corrupted |
| --- | ---: | ---: | ---: | ---: | ---: |
| `retrieval_hit_rate` | N/A | N/A | N/A | N/A | N/A |
| `mean_token_f1` | N/A | N/A | N/A | N/A | N/A |
| `judge_accuracy` | N/A | N/A | N/A | N/A | N/A |
| `mean_judge_score` | N/A | N/A | N/A | N/A | N/A |

## Corrupted Data Quality
```json
{}
```

## Repaired Data Quality
```json
{}
```

## Corrupted Freshness
```json
{}
```

## Repaired Freshness
```json
{}
```

## Evidence
- Corruption artifacts should be traceable through `data/results/corruption_log.json`.
- Answer-level retrieval and judge details should be inspected when metric deltas are small.

## Conclusion
- Metric degradation could not be determined because comparable metric values are missing.
- Data quality status did not change after repair.
