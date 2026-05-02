# Cluster-aware paired analysis (benchmark/paired_results_t02.json)

Tasks: 59 unique · Models: 2 · Seeds: 5 (`[11, 12, 13, 14, 15]`)

Three analyses, each correcting the unit-of-analysis issue in run_paired.py's McNemar:

1. **Task-level McNemar (per-task majority vote across seeds)** — independent pairs only.
2. **Cluster permutation test** — null permutes A↔B per task, preserving cluster structure.
3. **Cluster bootstrap** — resample tasks (with all their seeds) for a 95% CI on mean(A − B).

## Model: `google/gemma-4-26b-a4b-it`

### full vs react

**Task-level McNemar** (n_tasks=59, acc_A=83.1%, acc_B=86.4%, A-only=4, B-only=6, both=45, neither=4): χ² = 0.10, p = 7.52e-01

**Cluster permutation** (n_tasks=59, mean(A−B) = -2.0 pp): p = 7.38e-01

**Cluster bootstrap** (n_tasks=59): mean(A−B) = -2.0 pp, 95% CI [-11.5, +7.5]

### full vs no_tool

**Task-level McNemar** (n_tasks=59, acc_A=83.1%, acc_B=55.9%, A-only=17, B-only=1, both=32, neither=9): χ² = 12.50, p = 4.07e-04

**Cluster permutation** (n_tasks=59, mean(A−B) = +26.4 pp): p = 1.00e-04

**Cluster bootstrap** (n_tasks=59): mean(A−B) = +26.4 pp, 95% CI [+15.3, +38.3]

### react vs no_tool

**Task-level McNemar** (n_tasks=59, acc_A=86.4%, acc_B=55.9%, A-only=21, B-only=3, both=30, neither=5): χ² = 12.04, p = 5.20e-04

**Cluster permutation** (n_tasks=59, mean(A−B) = +28.5 pp): p = 3.00e-04

**Cluster bootstrap** (n_tasks=59): mean(A−B) = +28.5 pp, 95% CI [+14.9, +41.7]

## Model: `openai/gpt-5-mini`

### full vs react

**Task-level McNemar** (n_tasks=59, acc_A=81.4%, acc_B=37.3%, A-only=28, B-only=2, both=20, neither=9): χ² = 20.83, p = 5.01e-06

**Cluster permutation** (n_tasks=59, mean(A−B) = +35.3 pp): p = 1.00e-04

**Cluster bootstrap** (n_tasks=59): mean(A−B) = +35.3 pp, 95% CI [+23.7, +46.8]

### full vs no_tool

**Task-level McNemar** (n_tasks=59, acc_A=81.4%, acc_B=62.7%, A-only=12, B-only=1, both=36, neither=10): χ² = 7.69, p = 5.55e-03

**Cluster permutation** (n_tasks=59, mean(A−B) = +19.3 pp): p = 1.00e-04

**Cluster bootstrap** (n_tasks=59): mean(A−B) = +19.3 pp, 95% CI [+11.2, +28.1]

### react vs no_tool

**Task-level McNemar** (n_tasks=59, acc_A=37.3%, acc_B=62.7%, A-only=6, B-only=21, both=16, neither=16): χ² = 7.26, p = 7.05e-03

**Cluster permutation** (n_tasks=59, mean(A−B) = -15.9 pp): p = 1.35e-02

**Cluster bootstrap** (n_tasks=59): mean(A−B) = -15.9 pp, 95% CI [-27.8, -3.7]
