# Seeded paired ablation

Tasks: 59 unique · Conditions: 3 · Models: 2 · Seeds: 3 (T=0.7)
Total runs: 1062

## Accuracy by seed (mean across all 59 tasks)

| Model | Condition | seed=1 | seed=2 | seed=3 | mean | std |
|---|---|---|---|---|---|---|---|
| gemma-4-26b-a4b-it | full | 83.1% | 79.7% | 81.4% | 81.4% | 1.4 |
| gemma-4-26b-a4b-it | react | 83.1% | 84.7% | 86.4% | 84.7% | 1.4 |
| gemma-4-26b-a4b-it | no_tool | 55.9% | 54.2% | 57.6% | 55.9% | 1.4 |
| gpt-5-mini | full | 74.6% | 72.9% | 74.6% | 74.0% | 0.8 |
| gpt-5-mini | react | 35.6% | 44.1% | 39.0% | 39.5% | 3.5 |
| gpt-5-mini | no_tool | 54.2% | 57.6% | 50.8% | 54.2% | 2.8 |

## Paired McNemar tests (across all seeds combined)

### Model: `google/gemma-4-26b-a4b-it`

| Comparison | n_pairs | acc_A | acc_B | A-only | B-only | both | neither | χ² | p |
|---|---|---|---|---|---|---|---|---|---|
| full vs react | 177 | 81.4% | 84.7% | 10 | 16 | 134 | 17 | 0.96 | 3.27e-01 |
| full vs no_tool | 177 | 81.4% | 55.9% | 50 | 5 | 94 | 28 | 35.20 | 2.98e-09 |
| react vs no_tool | 177 | 84.7% | 55.9% | 57 | 6 | 93 | 21 | 39.68 | 2.99e-10 |

### Model: `openai/gpt-5-mini`

| Comparison | n_pairs | acc_A | acc_B | A-only | B-only | both | neither | χ² | p |
|---|---|---|---|---|---|---|---|---|---|
| full vs react | 177 | 74.0% | 39.5% | 70 | 9 | 61 | 37 | 45.57 | 1.47e-11 |
| full vs no_tool | 177 | 74.0% | 54.2% | 45 | 10 | 86 | 36 | 21.02 | 4.55e-06 |
| react vs no_tool | 177 | 39.5% | 54.2% | 24 | 50 | 46 | 57 | 8.45 | 3.66e-03 |

