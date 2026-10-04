---
id: kb-risk-001
title: Understanding Operational Risk Scores in SENTINEL
category: risk
tags: [risk, risk_score, risk_level, critical, high, medium, low, operational, assessment, depot, inventory]
---

## Understanding Operational Risk Scores in SENTINEL

SENTINEL's Operational Risk Assessment module evaluates supply risk for each depot/item combination using a composite scoring model.

### Risk Score Calculation

The risk score (0–100) is derived from multiple contributing factors:

- **Days Until Stock-out** — Lower days-until-stockout contributes significantly to higher risk scores. Items projected to run out within 7 days receive maximum score contribution from this factor.
- **Consumption Rate Volatility** — High variance in daily consumption patterns increases risk due to demand uncertainty.
- **Stock Level vs. Minimum Threshold** — Items at or below minimum safety threshold trigger elevated risk regardless of days-until-stockout estimates.
- **Replenishment Backlog** — Pending replenishment shipments in transit may partially reduce scored risk.

### Risk Levels

| Risk Level | Score Range | Meaning |
|------------|-------------|---------|
| LOW        | 0–34        | Normal operations; monitoring continues. |
| MEDIUM     | 35–59       | Increased monitoring and pre-positioning review recommended. |
| HIGH       | 60–79       | Immediate review required; plan replenishment. |
| CRITICAL   | 80–100      | Emergency action required; mission capability at risk. |

### Common Causes of CRITICAL Risk

- **Simultaneous Depletion** — Multiple items at a single depot approaching stockout concurrently.
- **Route Disruption** — Adverse environmental conditions on replenishment routes delay inbound shipments.
- **Surge Demand** — Unexpected operational tempo increase exceeds consumption forecasts.
- **Delayed Replenishment** — Shipments held at origin depot due to vehicle availability or route closure.

### Advisor Interpretation

When the SENTINEL Advisor reports CRITICAL risk, it means the deterministic risk engine has scored at least one depot/item pair ≥ 80 based on verified inventory, stockout prediction, and consumption data. The advisor recommendation is for human review and action; no automatic replenishment is triggered.
