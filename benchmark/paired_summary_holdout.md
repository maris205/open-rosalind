# Seeded paired ablation

Tasks: 30 unique · Conditions: 3 · Models: 2 · Seeds: 3 (T=0.7)
Total runs: 540

## Accuracy by seed (mean across all 59 tasks)

| Model | Condition | seed=1 | seed=2 | seed=3 | mean | std |
|---|---|---|---|---|---|---|---|
| gemma-4-26b-a4b-it | full | 53.3% | 53.3% | 53.3% | 53.3% | 0.0 |
| gemma-4-26b-a4b-it | react | 66.7% | 73.3% | 70.0% | 70.0% | 2.7 |
| gemma-4-26b-a4b-it | no_tool | 60.0% | 60.0% | 53.3% | 57.8% | 3.1 |
| gpt-5-mini | full | 16.7% | 16.7% | 13.3% | 15.6% | 1.6 |
| gpt-5-mini | react | 3.3% | 3.3% | 3.3% | 3.3% | 0.0 |
| gpt-5-mini | no_tool | 23.3% | 23.3% | 23.3% | 23.3% | 0.0 |

## Paired McNemar tests (across all seeds combined)

### Model: `google/gemma-4-26b-a4b-it`

| Comparison | n_pairs | acc_A | acc_B | A-only | B-only | both | neither | χ² | p |
|---|---|---|---|---|---|---|---|---|---|
| full vs react | 90 | 53.3% | 70.0% | 2 | 17 | 46 | 25 | 10.32 | 1.32e-03 |
| full vs no_tool | 90 | 53.3% | 57.8% | 13 | 17 | 35 | 25 | 0.30 | 5.84e-01 |
| react vs no_tool | 90 | 70.0% | 57.8% | 18 | 7 | 45 | 20 | 4.00 | 4.55e-02 |

### Model: `openai/gpt-5-mini`

| Comparison | n_pairs | acc_A | acc_B | A-only | B-only | both | neither | χ² | p |
|---|---|---|---|---|---|---|---|---|---|
| full vs react | 90 | 15.6% | 3.3% | 11 | 0 | 3 | 76 | 9.09 | 2.57e-03 |
| full vs no_tool | 90 | 15.6% | 23.3% | 2 | 9 | 12 | 67 | 3.27 | 7.04e-02 |
| react vs no_tool | 90 | 3.3% | 23.3% | 0 | 18 | 3 | 69 | 16.06 | 6.15e-05 |

