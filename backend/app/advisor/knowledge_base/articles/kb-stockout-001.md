---
id: kb-stockout-001
title: Stock-out Prediction — How SENTINEL Calculates Days Until Stockout
category: inventory
tags: [stockout, stock_out, days_until_stockout, prediction, inventory, consumption, threshold, risk, depletion]
---

## Stock-out Prediction in SENTINEL

SENTINEL's Stock-out Prediction module calculates how many days remain before each tracked inventory item at each depot reaches zero quantity, based on observed consumption rates.

### Calculation Method

Days Until Stockout (DUS) is computed as:

```
DUS = Current Quantity / Average Daily Consumption Rate
```

Where:
- **Current Quantity** — The most recent recorded quantity for the item at the depot.
- **Average Daily Consumption Rate** — Rolling average consumption derived from historical consumption records.

If Average Daily Consumption Rate is zero or undefined (no consumption recorded), the item is classified as non-depleting and DUS is set to a high sentinel value (e.g., 9999).

### Risk Bands for Days Until Stockout

| Days Until Stockout | Risk Band  | Recommended Action |
|--------------------|------------|-------------------|
| > 30 days          | LOW        | Routine monitoring. |
| 15–30 days         | MEDIUM     | Schedule replenishment review. |
| 7–14 days          | HIGH       | Initiate replenishment process immediately. |
| < 7 days           | CRITICAL   | Emergency replenishment required. |

### What Triggers a Stock-out Alert

A stock-out alert is raised when:
1. An item's current quantity falls below minimum safety threshold, OR
2. The projected days-until-stockout is < 7 days, OR
3. Both conditions are simultaneously true (highest priority alert).

### Limitations

- Consumption rates are rolling averages and may not capture sudden demand spikes.
- Quantity data reflects last recorded values; real-time sensor integration is not available in the current demo environment.
- Days-until-stockout is a projection, not a guarantee. Actual depletion depends on operational tempo.

### Advisor Use of Stockout Data

The SENTINEL Advisor uses stockout predictions as a primary signal when responding to inventory, risk, or depot advisory queries. When the advisor reports items "at risk," it is referring to items with a HIGH or CRITICAL stockout risk band in the verified inventory dataset.
