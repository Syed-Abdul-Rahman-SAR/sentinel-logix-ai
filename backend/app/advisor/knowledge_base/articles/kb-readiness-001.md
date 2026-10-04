---
id: kb-readiness-001
title: Mission Readiness Assessment — How SENTINEL Evaluates Depot Readiness
category: readiness
tags: [readiness, mission, ready, operational, depot, score, status, critical, degraded, full, limited]
---

## Mission Readiness Assessment in SENTINEL

SENTINEL's Mission Readiness module evaluates each depot's ability to sustain mission-critical supply operations based on the status of its tracked inventory items.

### Readiness Score Calculation

The readiness score (0–100) reflects how well a depot's current inventory supports mission execution:

- **Full Supply** — Items above safe threshold, low stockout risk, normal consumption rate.
- **Below Threshold** — Items at or below minimum safety threshold reduce readiness score.
- **Critical Stockout Risk** — Items with HIGH/CRITICAL stockout prediction contribute heavily to score reduction.
- **Multiple Item Deficits** — Concurrent deficits across multiple item categories produce compounding readiness degradation.

### Readiness Status Thresholds

| Readiness Score | Status                 | Operational Meaning |
|----------------|------------------------|-------------------|
| 85–100          | FULLY_OPERATIONAL      | All systems go; depot can sustain mission requirements. |
| 70–84           | OPERATIONAL            | Minor supply considerations; normal operations continue. |
| 55–69           | DEGRADED               | Multiple items below optimal; prioritise replenishment. |
| 40–54           | LIMITED_OPERATIONS     | Significant supply constraints; mission scope may need reduction. |
| 0–39            | MISSION_CRITICAL_RISK  | Immediate intervention required; mission capability severely at risk. |

### Factors That Degrade Readiness

1. **Fuel Stock Depletion** — Fuel is classified as mission-critical; depletion immediately degrades readiness.
2. **Medical Supply Shortage** — Medical items are weighted more heavily in the readiness score.
3. **Ammunition Below Threshold** — Triggers readiness degradation regardless of other factors.
4. **Maintenance Parts Shortage** — Reduces vehicle availability, indirectly degrading mobility readiness.
5. **Communication Equipment Deficit** — Classified as command-critical; shortage triggers immediate status reduction.

### Readiness vs. Risk: Key Distinction

- **Risk Score** measures the supply risk for an individual item at a depot.
- **Readiness Score** measures the aggregate capability of an entire depot to sustain operations.

A depot may have individual items at HIGH risk but remain OPERATIONAL overall if non-critical items are at risk while mission-critical items remain well-stocked.

### Advisor Interpretation of Readiness

When the SENTINEL Advisor responds to a readiness query, it reports:
- The worst-case readiness status across relevant depots.
- Specific items contributing to degraded readiness.
- Recommended replenishment priorities based on item criticality.

Readiness is a decision-support indicator for human commanders; no automatic operational decisions are made.
