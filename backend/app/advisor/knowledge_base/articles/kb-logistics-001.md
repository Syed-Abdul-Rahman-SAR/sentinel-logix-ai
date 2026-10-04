---
id: kb-logistics-001
title: Logistics Concepts — Depots, Bases, and Supply Routes in SENTINEL
category: logistics
tags: [depot, base, route, logistics, supply, location, facility, inventory, hub, forward]
---

## Logistics Entities in SENTINEL

SENTINEL models the military logistics network using three primary entity types: Depots, Bases, and Supply Routes.

### Depots

Depots are the primary inventory storage and distribution facilities in the SENTINEL network.

**Key Depot Attributes:**
- **Depot ID** — Unique identifier (e.g., `D001`, `D002`).
- **Name** — Facility name (e.g., "Northern Command Depot").
- **Location** — GPS coordinates for map visualisation.
- **Capacity** — Maximum storage capacity in standardised units.
- **Inventory** — List of tracked items with current quantities and minimum thresholds.

**Depot Types:**
- **Main Depot (Hub)** — Primary storage facilities with large capacity and direct road/rail connectivity.
- **Forward Depot** — Smaller forward-positioned facilities supporting active operational areas.
- **Emergency Cache** — Pre-positioned emergency reserves at strategic locations.

### Bases

Bases are command and operational facilities that receive supply from depots.

**Key Base Attributes:**
- **Base ID** — Unique identifier (e.g., `B001`, `B002`).
- **Name** — Facility name.
- **Associated Depots** — Primary and backup depot assignments.
- **Mission Profile** — Operational role affecting consumption patterns.

### Supply Routes

Supply routes connect depots to each other and to bases for replenishment convoys.

**Route Naming:**
- Routes follow the `[ORIGIN]-[DESTINATION]` convention.
- Direction is implicit; routes are bidirectional unless noted otherwise.

**Route Types:**
- **Primary Route** — Main replenishment corridor; optimised for convoy speed.
- **Alternate Route** — Backup corridor; typically longer but available if primary is disrupted.
- **Emergency Route** — Tertiary option; slow, used only when primary and alternate are unavailable.

### Depot Priority Assessment

When the Advisor is asked "which depot needs attention" or "where should I focus," it evaluates:
1. Depots with CRITICAL or HIGH operational risk items.
2. Depots with degraded readiness scores.
3. Depots served by routes with HIGH_RISK or EXTREME_RISK environmental conditions.
4. Depots with multiple concurrent item deficits.

The depot with the highest aggregate signal severity is recommended for priority attention.
