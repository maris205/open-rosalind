# Cluster-aware paired analysis (benchmark/paired_results_holdout.json)

Tasks: 30 unique · Models: 2 · Seeds: 3 (`[1, 2, 3]`)

Three analyses, each correcting the unit-of-analysis issue in run_paired.py's McNemar:

1. **Task-level McNemar (per-task majority vote across seeds)** — independent pairs only.
2. **Cluster permutation test** — null permutes A↔B per task, preserving cluster structure.
3. **Cluster bootstrap** — resample tasks (with all their seeds) for a 95% CI on mean(A − B).

## Model: `google/gemma-4-26b-a4b-it`

### full vs react

**Task-level McNemar** (n_tasks=30, acc_A=53.3%, acc_B=76.7%, A-only=0, B-only=7, both=16, neither=7): χ² = 5.14, p = 2.33e-02

**Cluster permutation** (n_tasks=30, mean(A−B) = -16.7 pp): p = 3.21e-02

**Cluster bootstrap** (n_tasks=30): mean(A−B) = -16.7 pp, 95% CI [-31.1, -4.4]

### full vs no_tool

**Task-level McNemar** (n_tasks=30, acc_A=53.3%, acc_B=60.0%, A-only=3, B-only=5, both=13, neither=9): χ² = 0.12, p = 7.24e-01

**Cluster permutation** (n_tasks=30, mean(A−B) = -4.4 pp): p = 7.21e-01

**Cluster bootstrap** (n_tasks=30): mean(A−B) = -4.4 pp, 95% CI [-23.3, +13.3]

### react vs no_tool

**Task-level McNemar** (n_tasks=30, acc_A=76.7%, acc_B=60.0%, A-only=6, B-only=1, both=17, neither=6): χ² = 2.29, p = 1.31e-01

**Cluster permutation** (n_tasks=30, mean(A−B) = +12.2 pp): p = 1.16e-01

**Cluster bootstrap** (n_tasks=30): mean(A−B) = +12.2 pp, 95% CI [-1.1, +25.6]

## Model: `openai/gpt-5-mini`

### full vs react

**Task-level McNemar** (n_tasks=30, acc_A=16.7%, acc_B=3.3%, A-only=4, B-only=0, both=1, neither=25): χ² = 2.25, p = 1.34e-01

**Cluster permutation** (n_tasks=30, mean(A−B) = +12.2 pp): p = 1.26e-01

**Cluster bootstrap** (n_tasks=30): mean(A−B) = +12.2 pp, 95% CI [+2.2, +24.4]

### full vs no_tool

**Task-level McNemar** (n_tasks=30, acc_A=16.7%, acc_B=26.7%, A-only=0, B-only=3, both=5, neither=22): χ² = 1.33, p = 2.48e-01

**Cluster permutation** (n_tasks=30, mean(A−B) = -7.8 pp): p = 2.50e-01

**Cluster bootstrap** (n_tasks=30): mean(A−B) = -7.8 pp, 95% CI [-18.9, +1.1]

### react vs no_tool

**Task-level McNemar** (n_tasks=30, acc_A=3.3%, acc_B=26.7%, A-only=0, B-only=7, both=1, neither=22): χ² = 5.14, p = 2.33e-02

**Cluster permutation** (n_tasks=30, mean(A−B) = -20.0 pp): p = 1.73e-02

**Cluster bootstrap** (n_tasks=30): mean(A−B) = -20.0 pp, 95% CI [-34.4, -7.8]
