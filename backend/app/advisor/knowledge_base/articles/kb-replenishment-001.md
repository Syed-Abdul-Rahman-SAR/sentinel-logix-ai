---
id: kb-replenishment-001
title: Replenishment Planning — How SENTINEL Recommends Resupply Actions
category: logistics
tags: [replenishment, resupply, shipment, convoy, planning, route, priority, dispatch, supply_chain, vehicle]
---

## Replenishment Planning in SENTINEL

SENTINEL's replenishment planning capabilities help logistics commanders prioritise and schedule resupply actions across the depot network.

### Replenishment Trigger Conditions

A replenishment recommendation is generated when any of the following conditions are detected:

1. **Item below minimum threshold** — Current quantity ≤ minimum safety threshold.
2. **HIGH stockout risk** — Days-until-stockout ≤ 14 days.
3. **CRITICAL stockout risk** — Days-until-stockout ≤ 7 days (emergency priority).
4. **Readiness degradation** — Depot readiness score drops below OPERATIONAL threshold.

### Replenishment Priority Tiers

| Tier     | Trigger Condition              | Response Time Target |
|----------|-------------------------------|---------------------|
| EMERGENCY | DUS < 7 days, CRITICAL risk   | Immediate dispatch (< 24 hours) |
| URGENT    | DUS 7–14 days, HIGH risk      | Dispatch within 48 hours |
| ROUTINE   | DUS 14–30 days, MEDIUM risk   | Schedule next convoy window |
| PLANNED   | DUS > 30 days, LOW risk       | Include in next monthly plan |

### Replenishment Route Selection

The Digital Twin Engine selects replenishment routes based on:
- **Route availability** — Environmental risk score < 75 (below HIGH_RISK threshold).
- **Distance** — Shorter routes preferred for emergency and urgent tiers.
- **Vehicle availability** — Available fleet units at origin depot.
- **Capacity** — Vehicle payload capacity vs. required replenishment quantity.

If the primary route is classified HIGH_RISK or EXTREME_RISK, the system recommends:
- Alternate route (if available and assessment score < 75).
- Pre-positioning via air or emergency ground route.
- Holding at origin until route conditions improve.

### Item Criticality Ordering

When multiple items need replenishment, prioritisation follows:

1. **Mission-Critical** — Fuel, ammunition (operational capability items).
2. **Life-Support** — Medical supplies, food, water.
3. **Enabling** — Maintenance parts, communication equipment.
4. **General Support** — All other tracked items.

### Advisor Replenishment Recommendations

When the SENTINEL Advisor generates a replenishment recommendation, it:
- Identifies the specific item(s) and depot(s) requiring resupply.
- States the priority tier based on current risk signals.
- Suggests the recommended route if environmental data is available.
- Notes any route risk conditions that may affect delivery timelines.
- Reminds the operator that all recommendations require human commander approval before action.
