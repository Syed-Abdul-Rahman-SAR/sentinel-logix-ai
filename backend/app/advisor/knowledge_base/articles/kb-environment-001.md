---
id: kb-environment-001
title: Environmental Intelligence — Route Risk Assessment in SENTINEL
category: environment
tags: [environment, weather, terrain, route, risk, classification, disruption, condition, score, environmental_risk]
---

## Environmental Intelligence in SENTINEL

SENTINEL's Environmental Intelligence module assesses weather and terrain conditions along logistics routes to evaluate the environmental risk to supply operations.

### Route Risk Score

Each route is assigned an environmental risk score (0–100) computed from two sub-components:

| Component          | Weight | Description |
|-------------------|--------|------------|
| Weather Risk Score | 50%    | Derived from precipitation intensity, visibility, wind speed, and temperature extremes. |
| Terrain Risk Score | 50%    | Derived from route elevation changes, road surface type, seasonal accessibility, and flood risk. |

```
Environmental Risk Score = (Weather Risk Score × 0.5) + (Terrain Risk Score × 0.5)
```

### Route Classification

| Score Range | Classification   | Operational Impact |
|-------------|-----------------|-------------------|
| 0–24        | CLEAR            | Normal operations; no restrictions. |
| 25–49       | CAUTION          | Reduced-speed convoy recommended; monitor conditions. |
| 50–74       | ELEVATED         | Route planning review required; consider alternate routes. |
| 75–89       | HIGH_RISK        | Convoy delays expected; commander approval required. |
| 90–100      | EXTREME_RISK     | Route effectively closed; emergency re-routing required. |

### Common Environmental Risk Factors

**Weather Factors:**
- Heavy rain or snow reducing vehicle mobility.
- Low visibility affecting convoy safety.
- Extreme heat stressing vehicle cooling systems.
- Flash flood risk following storm events.

**Terrain Factors:**
- Mountain passes with seasonal closure risk.
- Unpaved roads degraded by recent precipitation.
- River crossings with variable water level.
- High-altitude routes with altitude-related mechanical risks.

### Route IDs in SENTINEL

Routes in SENTINEL follow the naming convention `[ORIGIN]-[DESTINATION]`, e.g.:
- `SIL-IMP` — Siliguri to Imphal route (Northeast corridor).
- `DEL-AGR` — Delhi to Agra route (Northern plains).
- `CHE-TRI` — Chennai to Trivandrum route (Southern coastal).

### How the Advisor Uses Environmental Data

When responding to route or disruption queries, the SENTINEL Advisor:
1. Retrieves the current environmental risk score and classification for the requested or inferred route.
2. Reports weather and terrain sub-scores alongside the composite score.
3. Flags ELEVATED, HIGH_RISK, or EXTREME_RISK routes as disruption factors affecting replenishment timelines.
4. Does not predict future weather; reports only current assessed conditions.
