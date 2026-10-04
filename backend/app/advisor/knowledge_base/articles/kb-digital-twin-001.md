---
id: kb-digital-twin-001
title: Digital Twin Engine — Scenario Simulation and Replenishment Planning
category: digital_twin
tags: [digital_twin, scenario, simulation, replenishment, shipment, what_if, disruption, planning, twin]
---

## Digital Twin Engine in SENTINEL

SENTINEL's Digital Twin Engine provides scenario simulation, replenishment planning, and shipment tracking capabilities. It enables logistics commanders to evaluate supply chain responses to disruptions before committing to operational decisions.

### Core Capabilities

#### 1. Baseline State Assessment
The Digital Twin computes the current operational baseline:
- Aggregated inventory levels across all depots.
- Active stockout risks and days-until-depletion.
- Mission readiness scores across all depots.
- Environmental conditions on active supply routes.

#### 2. Scenario Simulation (What-If Analysis)
Commanders can simulate disruption scenarios to evaluate supply chain resilience:

- **Route Disruption Scenarios** — Simulate closure of one or more supply routes and assess impact on depot inventories.
- **Surge Demand Scenarios** — Simulate increased consumption rates (e.g., ×1.5, ×2.0) and project accelerated stockout timelines.
- **Depot Isolation Scenarios** — Simulate loss of connectivity for a specific depot and assess alternate supply feasibility.

#### 3. Replenishment Engine
Automated replenishment recommendations are generated based on:
- Items with HIGH or CRITICAL stockout risk.
- Mission-critical item categories (fuel, ammunition, medical).
- Available vehicle fleet and route accessibility.

Replenishment plans produced by the Digital Twin are decision-support outputs for human review and approval. The system does not autonomously dispatch vehicles.

#### 4. Shipment Tracking
The Digital Twin tracks synthetic replenishment shipments:
- Shipment ID, origin depot, destination depot.
- Route used and current status (`in_transit`, `delivered`, `pending`).
- Estimated delivery based on route distance and vehicle speed.

### Advisor Integration

When responding to scenario or disruption queries, the SENTINEL Advisor:
1. Retrieves the current Digital Twin baseline.
2. Reports active shipments and their status.
3. Identifies routes with active disruptions that may affect replenishment timelines.
4. Provides replenishment recommendations aligned with the Digital Twin's plan outputs.

### What-If Query Interpretation

Queries containing words like "what if," "simulate," "scenario," or "disrupt" trigger the Advisor's scenario-reasoning mode, which:
- Identifies the disruption type from query context.
- Cross-references with environmental risk scores on relevant routes.
- Reports the estimated inventory impact if the disruption persists.
- Recommends pre-positioning or alternate routing as mitigation.
