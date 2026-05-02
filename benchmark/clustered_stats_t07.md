# Cluster-aware paired analysis (benchmark/paired_results.json)

Tasks: 59 unique · Models: 2 · Seeds: 3 (`[1, 2, 3]`)

Three analyses, each correcting the unit-of-analysis issue in run_paired.py's McNemar:

1. **Task-level McNemar (per-task majority vote across seeds)** — independent pairs only.
2. **Cluster permutation test** — null permutes A↔B per task, preserving cluster structure.
3. **Cluster bootstrap** — resample tasks (with all their seeds) for a 95% CI on mean(A − B).

## Model: `google/gemma-4-26b-a4b-it`

### full vs react

**Task-level McNemar** (n_tasks=59, acc_A=81.4%, acc_B=84.7%, A-only=3, B-only=5, both=45, neither=6): χ² = 0.12, p = 7.24e-01

**Cluster permutation** (n_tasks=59, mean(A−B) = -3.4 pp): p = 5.42e-01

**Cluster bootstrap** (n_tasks=59): mean(A−B) = -3.4 pp, 95% CI [-11.9, +5.1]

### full vs no_tool

**Task-level McNemar** (n_tasks=59, acc_A=81.4%, acc_B=55.9%, A-only=16, B-only=1, both=32, neither=10): χ² = 11.53, p = 6.85e-04

**Cluster permutation** (n_tasks=59, mean(A−B) = +25.4 pp): p = 2.00e-04

**Cluster bootstrap** (n_tasks=59): mean(A−B) = +25.4 pp, 95% CI [+13.6, +37.3]

### react vs no_tool

**Task-level McNemar** (n_tasks=59, acc_A=84.7%, acc_B=55.9%, A-only=19, B-only=2, both=31, neither=7): χ² = 12.19, p = 4.80e-04

**Cluster permutation** (n_tasks=59, mean(A−B) = +28.8 pp): p = 1.00e-04

**Cluster bootstrap** (n_tasks=59): mean(A−B) = +28.8 pp, 95% CI [+16.4, +41.2]

## Model: `openai/gpt-5-mini`

### full vs react

**Task-level McNemar** (n_tasks=59, acc_A=78.0%, acc_B=37.3%, A-only=25, B-only=1, both=21, neither=12): χ² = 20.35, p = 6.46e-06

**Cluster permutation** (n_tasks=59, mean(A−B) = +34.5 pp): p = 1.00e-04

**Cluster bootstrap** (n_tasks=59): mean(A−B) = +34.5 pp, 95% CI [+23.2, +46.3]

### full vs no_tool

**Task-level McNemar** (n_tasks=59, acc_A=78.0%, acc_B=54.2%, A-only=16, B-only=2, both=30, neither=11): χ² = 9.39, p = 2.18e-03

**Cluster permutation** (n_tasks=59, mean(A−B) = +19.8 pp): p = 2.00e-04

**Cluster bootstrap** (n_tasks=59): mean(A−B) = +19.8 pp, 95% CI [+10.2, +29.4]

### react vs no_tool

**Task-level McNemar** (n_tasks=59, acc_A=37.3%, acc_B=54.2%, A-only=7, B-only=17, both=15, neither=20): χ² = 3.38, p = 6.62e-02

**Cluster permutation** (n_tasks=59, mean(A−B) = -14.7 pp): p = 2.86e-02

**Cluster bootstrap** (n_tasks=59): mean(A−B) = -14.7 pp, 95% CI [-27.1, -2.8]
