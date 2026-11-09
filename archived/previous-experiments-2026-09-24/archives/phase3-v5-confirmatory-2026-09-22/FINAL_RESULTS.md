# Council of Delphi — Phase 3 v5 Final Results

Experiment: `82ad9fb9945d`  
Freeze: `phase3-paired-low-labels-2026-09-22-v5`  
Archived UTC: 2026-09-22T16:27:30+00:00

## Primary paired result

- Completed paired questions: 497/500
- Unresolved: 3 (0.6%)
- Round-one majority: 324/497 (65.19%)
- Delphi final: 376/497 (75.65%)
- Accuracy change: **+10.46%**
- Approximate paired 95% interval: +6.96% to +13.96%
- Exact McNemar p-value: 8.54e-09
- Wrong to right: 68
- Right to wrong: 16

## Operational result

- Escalated: 378 (76.06%)
- Recorded total result cost: $5.285104
- Round-one agent cost: $2.632138
- Round-two agent cost: $2.652966
- Recorded marginal cost per net correction: $0.0510
- Mean latency: 11041.0 ms
- Multiple-choice transport failures: 0
- JEV cost was not returned by the API and is therefore excluded from monetary totals.

## Source breakdown

| Source | Completed | Round one | Delphi | Change | Escalated |
|---|---:|---:|---:|---:|---:|
| arc_challenge | 50 | 96.0% | 92.0% | -4.0% | 34.0% |
| bbeh_mini | 98 | 36.7% | 44.9% | +8.2% | 100.0% |
| gsm1k | 100 | 45.0% | 65.0% | +20.0% | 72.0% |
| mmlu_pro | 249 | 78.3% | 88.8% | +10.4% | 76.7% |

## Claim boundary

The frozen JEV-mediated Delphi procedure materially improved accuracy over its own paired Round-one majority vote on this benchmark. The result evaluates the complete routing-and-reconsideration system; it does not establish that JEV is superior to every cheaper routing heuristic or that gains generalize to every dataset. JEV monetary cost remains unmeasured.
