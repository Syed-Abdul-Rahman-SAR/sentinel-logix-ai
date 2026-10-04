---
id: kb-advisor-001
title: AI Advisor — How SENTINEL Generates Advisory Recommendations
category: system
tags: [advisor, recommendation, reasoning, confidence, intent, context, query, response, grounding, deterministic]
---

## SENTINEL AI Advisor — How Recommendations Are Generated

The SENTINEL AI Advisor provides natural-language logistics recommendations grounded exclusively in verified SENTINEL intelligence data. It is designed to support human decision-making, not to replace it.

### Query Processing Pipeline

Every advisor query goes through the following stages:

```
User Query → Advisor API → Context Builder → Reasoning Engine → [Optional LLM] → Response Validation → AdvisorResponse
```

#### Stage 1: Context Building
The Context Builder aggregates intelligence from all active SENTINEL modules:
- Inventory levels and threshold violations.
- Stockout predictions and days-until-depletion.
- Operational risk assessments.
- Mission readiness scores.
- Environmental route conditions.
- Active Digital Twin shipments.

No new calculations are performed at this stage; the builder reads verified outputs from existing service layers.

#### Stage 2: Intent Classification
The Advisor classifies the query intent from a predefined set:
- `inventory_risk` — Questions about specific items at risk of stockout.
- `readiness` — Questions about mission readiness status.
- `route_environment` — Questions about route conditions and weather/terrain.
- `route_disruption` — What-if or scenario disruption queries.
- `depot_attention` — Questions about which depot needs priority attention.
- `risk_cause` — Questions about why risk levels are elevated.
- `general` — Fallback for queries that don't match specific intents.

#### Stage 3: Multi-Signal Reasoning Engine
The reasoning engine analyses the aggregated context signals and produces:
- A prioritised recommendation.
- Supporting evidence items from verified data sources.
- Confidence score (0–100) based on signal convergence.
- Relevant entities (depots, items, routes) referenced in the recommendation.

### Confidence Score Interpretation

The confidence score reflects the number and severity of SENTINEL intelligence signals supporting the recommendation. It is **not** a statistically validated probability.

| Confidence | Meaning |
|-----------|---------|
| 80–100    | Multiple high-severity signals strongly converge on the recommendation. |
| 60–79     | Clear signals from at least one primary intelligence module. |
| 40–59     | Mixed or ambiguous signals; recommendation is indicative only. |
| 0–39      | Limited available data; treat recommendation as informational only. |

### Grounding Constraints

The SENTINEL Advisor enforces strict grounding:
- It does **not** invent inventory quantities, dates, or entity names.
- It does **not** create new risk scores or readiness levels.
- It does **not** claim to execute logistics actions.
- All stated facts trace back to verified SENTINEL service outputs.

### Limitations of the Current Advisor

- The advisor operates on synthetic demonstration data only.
- Recommendations are for human review and approval; they do not trigger automated operations.
- The advisor does not have access to classified intelligence systems.
- The confidence score is a decision-support heuristic, not a validated probability.
