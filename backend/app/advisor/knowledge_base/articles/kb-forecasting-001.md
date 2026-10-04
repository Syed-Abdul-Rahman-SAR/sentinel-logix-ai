---
id: kb-forecasting-001
title: Demand Forecasting — Consumption Prediction in SENTINEL
category: logistics
tags: [forecasting, demand, consumption, rate, prediction, rolling_average, model, trend, supply, planning]
---

## Demand Forecasting in SENTINEL

SENTINEL's Demand Forecasting module predicts future consumption patterns for each inventory item at each depot. These forecasts feed into the stockout prediction and replenishment planning systems.

### Forecasting Method

SENTINEL uses a **rolling average model** for demand forecasting:

```
Forecasted Consumption = Σ(Recent Consumption Records) / N
```

Where N is the rolling window size (default: 7 days of historical consumption).

This approach is chosen for its:
- **Stability** — Rolling averages are resistant to single-day anomalies.
- **Interpretability** — The method is transparent and explainable to logistics officers.
- **Computational efficiency** — Suitable for real-time advisory applications.

### Consumption Categories

Items are categorised by consumption volatility:

| Category           | Typical Volatility | Forecasting Confidence |
|-------------------|-------------------|----------------------|
| Fuel               | Medium-High        | Moderate (operational tempo dependency) |
| Ammunition         | High               | Lower (burst demand during exercises) |
| Medical Supplies   | Low-Medium         | Higher (more predictable consumption) |
| Maintenance Parts  | Variable           | Moderate (failure-driven demand) |
| Food & Water       | Low                | High (personnel count-driven) |

### How Forecasts Affect Risk Scores

Higher forecasted consumption rates directly reduce the projected days-until-stockout:

- If daily consumption increases by 50%, DUS halves.
- This triggers stockout prediction to upgrade risk levels.
- Operational risk scores incorporate consumption rate trends.

### Forecast Limitations

- Rolling averages lag behind sudden demand surges (e.g., unexpected exercise scale-up).
- Seasonal patterns are not modelled in the current implementation.
- Zero consumption periods (e.g., during stand-down) may under-forecast future needs.
- Forecasts reflect synthetic demo data and do not represent real operational consumption.

### Advisor Use of Forecasts

When the Advisor responds to inventory or risk queries, it implicitly relies on forecast-driven consumption rates embedded in the stockout prediction outputs. The Advisor does not expose raw forecast data directly but uses it as an upstream input to the evidence it presents.
