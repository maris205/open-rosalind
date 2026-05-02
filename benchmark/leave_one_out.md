# Leave-one-skill-out sensitivity

How robust are the headline gaps if we delete an entire skill category? We use Replication B's per-task seed-mean accuracy and recompute `full`, `react`, `no_tool` aggregates while holding one category out.

Skill-category mapping by task-id prefix: `seq-` → sequence · `ann-` → protein · `lit-` → literature · `mut-` → mutation · `pro-` → protein-or-mixed · `wf-` → workflow-edge · `edge-`/`stress-` → edge · `followup-` → follow-up · `harness-` → multistep.

### Model: `google/gemma-4-26b-a4b-it`

| Held-out skill | n_remaining | full | react | no_tool | full−react | **full−no_tool** |
|---|---|---|---|---|---|---|
| (none) | 59 | 82.0% | 84.1% | 55.6% | -2.0 pp | **+26.4 pp** |
| edge | 52 | 81.5% | 84.2% | 55.4% | -2.7 pp | **+26.2 pp** |
| follow-up | 55 | 84.7% | 84.7% | 57.8% | +0.0 pp | **+26.9 pp** |
| literature | 53 | 81.9% | 84.2% | 51.3% | -2.3 pp | **+30.6 pp** |
| multistep | 49 | 80.4% | 84.1% | 50.6% | -3.7 pp | **+29.8 pp** |
| mutation | 53 | 81.9% | 82.6% | 56.2% | -0.8 pp | **+25.7 pp** |
| protein | 53 | 81.9% | 83.0% | 58.1% | -1.1 pp | **+23.8 pp** |
| protein-or-mixed | 53 | 81.9% | 84.2% | 54.3% | -2.3 pp | **+27.5 pp** |
| sequence | 51 | 79.2% | 83.5% | 60.0% | -4.3 pp | **+19.2 pp** |
| workflow-edge | 53 | 84.5% | 86.0% | 56.2% | -1.5 pp | **+28.3 pp** |

### Model: `openai/gpt-5-mini`

| Held-out skill | n_remaining | full | react | no_tool | full−react | **full−no_tool** |
|---|---|---|---|---|---|---|
| (none) | 59 | 75.3% | 40.0% | 55.9% | +35.3 pp | **+19.3 pp** |
| edge | 52 | 76.9% | 36.9% | 56.5% | +40.0 pp | **+20.4 pp** |
| follow-up | 55 | 77.8% | 39.6% | 57.5% | +38.2 pp | **+20.4 pp** |
| literature | 53 | 75.5% | 40.4% | 54.3% | +35.1 pp | **+21.1 pp** |
| multistep | 49 | 72.2% | 45.7% | 55.1% | +26.5 pp | **+17.1 pp** |
| mutation | 53 | 73.2% | 40.0% | 56.6% | +33.2 pp | **+16.6 pp** |
| protein | 53 | 78.5% | 38.1% | 58.5% | +40.4 pp | **+20.0 pp** |
| protein-or-mixed | 53 | 74.7% | 39.2% | 55.1% | +35.5 pp | **+19.6 pp** |
| sequence | 51 | 71.4% | 40.4% | 54.1% | +31.0 pp | **+17.3 pp** |
| workflow-edge | 53 | 76.6% | 40.0% | 55.5% | +36.6 pp | **+21.1 pp** |
