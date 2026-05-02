# Cluster-aware paired analysis (benchmark/paired_results_holdout.json)

Tasks: 30 unique · Models: 2 · Seeds: 3 (`[1, 2, 3]`)

Three analyses, each correcting the unit-of-analysis issue in run_paired.py's McNemar:

1. **Task-level McNemar (per-task majority vote across seeds)** — independent pairs only.
2. **Cluster permutation test** — null permutes A↔B per task, preserving cluster structure.
3. **Cluster bootstrap** — resample tasks (with all their seeds) for a 95% CI on mean(A − B).

## Model: `google/gemma-4-26b-a4b-it`

### full vs react

**Task-level McNemar** (n_tasks=30, acc_A=30.0%, acc_B=73.3%, A-only=0, B-only=13, both=9, neither=8): χ² = 11.08, p = 8.74e-04

**Cluster permutation** (n_tasks=30, mean(A−B) = -37.8 pp): p = 1.20e-03

**Cluster bootstrap** (n_tasks=30): mean(A−B) = -37.8 pp, 95% CI [-56.7, -18.9]

### full vs no_tool

**Task-level McNemar** (n_tasks=30, acc_A=30.0%, acc_B=53.3%, A-only=1, B-only=8, both=8, neither=13): χ² = 4.00, p = 4.55e-02

**Cluster permutation** (n_tasks=30, mean(A−B) = -26.7 pp): p = 5.80e-03

**Cluster bootstrap** (n_tasks=30): mean(A−B) = -26.7 pp, 95% CI [-43.3, -11.1]

### react vs no_tool

**Task-level McNemar** (n_tasks=30, acc_A=73.3%, acc_B=53.3%, A-only=7, B-only=1, both=15, neither=7): χ² = 3.12, p = 7.71e-02

**Cluster permutation** (n_tasks=30, mean(A−B) = +11.1 pp): p = 1.98e-01

**Cluster bootstrap** (n_tasks=30): mean(A−B) = +11.1 pp, 95% CI [-3.3, +26.7]

## Model: `openai/gpt-5-mini`

### full vs react

**Task-level McNemar** (n_tasks=30, acc_A=10.0%, acc_B=0.0%, A-only=3, B-only=0, both=0, neither=27): χ² = 1.33, p = 2.48e-01

**Cluster permutation** (n_tasks=30, mean(A−B) = +11.1 pp): p = 1.28e-01

**Cluster bootstrap** (n_tasks=30): mean(A−B) = +11.1 pp, 95% CI [+1.1, +23.3]

### full vs no_tool

**Task-level McNemar** (n_tasks=30, acc_A=10.0%, acc_B=10.0%, A-only=1, B-only=1, both=2, neither=26): χ² = 0.50, p = 4.80e-01

**Cluster permutation** (n_tasks=30, mean(A−B) = +0.0 pp): p = 1.00e+00

**Cluster bootstrap** (n_tasks=30): mean(A−B) = +0.0 pp, 95% CI [-10.0, +10.0]

### react vs no_tool

**Task-level McNemar** (n_tasks=30, acc_A=0.0%, acc_B=10.0%, A-only=0, B-only=3, both=0, neither=27): χ² = 1.33, p = 2.48e-01

**Cluster permutation** (n_tasks=30, mean(A−B) = -11.1 pp): p = 3.25e-02

**Cluster bootstrap** (n_tasks=30): mean(A−B) = -11.1 pp, 95% CI [-21.1, -3.3]
