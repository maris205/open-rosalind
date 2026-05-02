# Seeded paired ablation

Tasks: 59 unique · Conditions: 3 · Models: 2 · Seeds: 5 (T=0.7)
Total runs: 1770

## Accuracy by seed (mean across all 59 tasks)

| Model | Condition | seed=11 | seed=12 | seed=13 | seed=14 | seed=15 | mean | std |
|---|---|---|---|---|---|---|---|---|---|
| gemma-4-26b-a4b-it | full | 83.1% | 81.4% | 81.4% | 81.4% | 83.1% | 82.0% | 0.8 |
| gemma-4-26b-a4b-it | react | 86.4% | 81.4% | 83.1% | 83.1% | 86.4% | 84.1% | 2.0 |
| gemma-4-26b-a4b-it | no_tool | 55.9% | 55.9% | 55.9% | 55.9% | 54.2% | 55.6% | 0.7 |
| gpt-5-mini | full | 72.9% | 71.2% | 72.9% | 78.0% | 81.4% | 75.3% | 3.8 |
| gpt-5-mini | react | 37.3% | 45.8% | 42.4% | 42.4% | 32.2% | 40.0% | 4.7 |
| gpt-5-mini | no_tool | 59.3% | 57.6% | 55.9% | 54.2% | 52.5% | 55.9% | 2.4 |

## Paired McNemar tests (across all seeds combined)

### Model: `google/gemma-4-26b-a4b-it`

| Comparison | n_pairs | acc_A | acc_B | A-only | B-only | both | neither | χ² | p |
|---|---|---|---|---|---|---|---|---|---|
| full vs react | 295 | 82.0% | 84.1% | 22 | 28 | 220 | 25 | 0.50 | 4.80e-01 |
| full vs no_tool | 295 | 82.0% | 55.6% | 81 | 3 | 161 | 50 | 70.58 | 4.41e-17 |
| react vs no_tool | 295 | 84.1% | 55.6% | 100 | 16 | 148 | 31 | 59.39 | 1.29e-14 |

### Model: `openai/gpt-5-mini`

| Comparison | n_pairs | acc_A | acc_B | A-only | B-only | both | neither | χ² | p |
|---|---|---|---|---|---|---|---|---|---|
| full vs react | 295 | 75.3% | 40.0% | 124 | 20 | 98 | 53 | 73.67 | 9.22e-18 |
| full vs no_tool | 295 | 75.3% | 55.9% | 67 | 10 | 155 | 63 | 40.73 | 1.75e-10 |
| react vs no_tool | 295 | 40.0% | 55.9% | 39 | 86 | 79 | 91 | 16.93 | 3.88e-05 |

