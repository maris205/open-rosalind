# Pilot ablation results

Model: `google/gemma-4-26b-a4b-it` · Tasks: 10 (4 basic + 2 edge + 2 multi-step + 2 single-step from edge)

| Condition | Acc | ToolCorr | CitePres | TraceComp | NoFail | Avg ms |
|---|---|---|---|---|---|---|
| **full** | 90% | 100% | 10% | 100% | 100% | 9499 |
| **react** | 90% | 100% | 0% | 100% | 100% | 11273 |
| **no_tool** | 50% | 0% | 0% | 0% | 100% | 5786 |
| **no_cite** | 90% | 100% | 10% | 100% | 100% | 8037 |
| **no_template** | 100% | 80% | 20% | 100% | 100% | 5626 |
