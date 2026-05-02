# Floor / stability analysis

Per-task stability statistics computed across seeds, *not* aggregated across tasks.

**floor acc** = average across tasks of the *worst seed*'s accuracy on that task. If floor acc is high, the system rarely fails on a task even at its unluckiest sample. **lower-decile** = the 10th-percentile per-task seed-mean accuracy (i.e. the worst 10% of tasks). **mean across-seed SD** = average per-task SD across the K seeds. **unstable%** = fraction of tasks where at least one seed disagreed with another. **catastrophic%** = fraction of tasks where *every* seed got it wrong.

## Replication B (5 seeds at T=0.2 — the same temperature as §8.5)

| Model | Condition | n_tasks | mean acc | **floor acc** | lower-decile | mean across-seed SD | unstable% | catastrophic% |
|---|---|---|---|---|---|---|---|---|
| gemma-4-26b-a4b-it | **full** | 59 | 82.0% | **79.7%** | 0.0% | 1.51 pp | 3.4% | 20.3% |
| gemma-4-26b-a4b-it | **no_tool** | 59 | 55.6% | **52.5%** | 0.0% | 2.34 pp | 5.1% | 47.5% |
| gemma-4-26b-a4b-it | **react** | 59 | 84.1% | **76.3%** | 0.0% | 4.22 pp | 10.2% | 23.7% |
| gpt-5-mini | **full** | 59 | 75.3% | **61.0%** | 0.0% | 9.05 pp | 20.3% | 39.0% |
| gpt-5-mini | **no_tool** | 59 | 55.9% | **30.5%** | 0.0% | 18.40 pp | 40.7% | 69.5% |
| gpt-5-mini | **react** | 59 | 40.0% | **15.3%** | 0.0% | 23.00 pp | 52.5% | 84.7% |

## Replication A (3 seeds at T=0.7 — robustness sidecar)

| Model | Condition | n_tasks | mean acc | **floor acc** | lower-decile | mean across-seed SD | unstable% | catastrophic% |
|---|---|---|---|---|---|---|---|---|
| gemma-4-26b-a4b-it | **full** | 59 | 81.4% | **79.7%** | 0.0% | 1.60 pp | 3.4% | 20.3% |
| gemma-4-26b-a4b-it | **no_tool** | 59 | 55.9% | **50.8%** | 0.0% | 4.79 pp | 10.2% | 49.2% |
| gemma-4-26b-a4b-it | **react** | 59 | 84.7% | **79.7%** | 0.0% | 4.79 pp | 10.2% | 20.3% |
| gpt-5-mini | **full** | 59 | 74.0% | **61.0%** | 0.0% | 10.39 pp | 22.0% | 39.0% |
| gpt-5-mini | **no_tool** | 59 | 54.2% | **33.9%** | 0.0% | 19.18 pp | 40.7% | 66.1% |
| gpt-5-mini | **react** | 59 | 39.5% | **22.0%** | 0.0% | 17.58 pp | 37.3% | 78.0% |
