# Cluster-aware paired analysis (benchmark/paired_results_holdout.json)

Tasks: 30 unique · Models: 2 · Seeds: 3 (`[1, 2, 3]`)

Three analyses, each correcting the unit-of-analysis issue in run_paired.py's McNemar:

1. **Task-level McNemar (per-task majority vote across seeds)** — independent pairs only.
2. **Cluster permutation test** — null permutes A↔B per task, preserving cluster structure.
3. **Cluster bootstrap** — resample tasks (with all their seeds) for a 95% CI on mean(A − B).

## Model: `google/gemma-4-26b-a4b-it`

### full vs react

**Task-level McNemar** (n_tasks=30, acc_A=20.0%, acc_B=50.0%, A-only=1, B-only=10, both=5, neither=14): χ² = 5.82, p = 1.59e-02

**Cluster permutation** (n_tasks=30, mean(A−B) = -31.1 pp): p = 3.60e-03

**Cluster bootstrap** (n_tasks=30): mean(A−B) = -31.1 pp, 95% CI [-50.0, -13.3]

### full vs no_tool

**Task-level McNemar** (n_tasks=30, acc_A=20.0%, acc_B=53.3%, A-only=1, B-only=11, both=5, neither=13): χ² = 6.75, p = 9.37e-03

**Cluster permutation** (n_tasks=30, mean(A−B) = -28.9 pp): p = 2.40e-03

**Cluster bootstrap** (n_tasks=30): mean(A−B) = -28.9 pp, 95% CI [-45.6, -13.3]

### react vs no_tool

**Task-level McNemar** (n_tasks=30, acc_A=50.0%, acc_B=53.3%, A-only=2, B-only=3, both=13, neither=12): χ² = 0.00, p = 1.00e+00

**Cluster permutation** (n_tasks=30, mean(A−B) = +2.2 pp): p = 8.78e-01

**Cluster bootstrap** (n_tasks=30): mean(A−B) = +2.2 pp, 95% CI [-11.1, +16.7]

## Model: `openai/gpt-5-mini`

### full vs react

**Task-level McNemar** (n_tasks=30, acc_A=10.0%, acc_B=3.3%, A-only=2, B-only=0, both=1, neither=27): χ² = 0.50, p = 4.80e-01

**Cluster permutation** (n_tasks=30, mean(A−B) = +7.8 pp): p = 6.58e-02

**Cluster bootstrap** (n_tasks=30): mean(A−B) = +7.8 pp, 95% CI [+2.2, +14.4]

### full vs no_tool

**Task-level McNemar** (n_tasks=30, acc_A=10.0%, acc_B=23.3%, A-only=1, B-only=5, both=2, neither=22): χ² = 1.50, p = 2.21e-01

**Cluster permutation** (n_tasks=30, mean(A−B) = -15.6 pp): p = 2.71e-02

**Cluster bootstrap** (n_tasks=30): mean(A−B) = -15.6 pp, 95% CI [-27.8, -4.4]

### react vs no_tool

**Task-level McNemar** (n_tasks=30, acc_A=3.3%, acc_B=23.3%, A-only=0, B-only=6, both=1, neither=23): χ² = 4.17, p = 4.12e-02

**Cluster permutation** (n_tasks=30, mean(A−B) = -23.3 pp): p = 1.10e-03

**Cluster bootstrap** (n_tasks=30): mean(A−B) = -23.3 pp, 95% CI [-35.6, -12.2]
