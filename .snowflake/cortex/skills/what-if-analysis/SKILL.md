---
name: what-if-analysis
description: "Compares current scenario vs an alternative budget or channel allocation. Projects revenue, impressions, and conversions for both scenarios using historical performance data. Use when: evaluating budget reallocation, comparing channel strategies, or testing optimization hypotheses."
---

# What-If Analysis Skill

## Purpose
Enable scenario comparison by projecting campaign outcomes under different budget or channel allocations, grounded in historical performance metrics.

## Inputs
- `client_name` (required): Client brand name
- `campaign_type` (optional): Filter historical data to specific campaign type
- `current_allocation` (required): Dictionary of channel_name -> budget_usd for the current/baseline scenario
- `proposed_allocation` (required): Dictionary of channel_name -> budget_usd for the alternative scenario

Example:
```json
{
  "current_allocation": {
    "Instagram": 50000,
    "Google Search": 80000,
    "TV": 120000,
    "Email": 30000
  },
  "proposed_allocation": {
    "Instagram": 80000,
    "Google Search": 100000,
    "TikTok": 60000,
    "Email": 40000
  }
}
```

## Workflow

### Step 1: Resolve Client
```sql
SELECT client_id FROM MARKETING_COPILOT.ANALYTICS.DIM_CLIENT
WHERE UPPER(client_name) = UPPER(:client_name);
```

### Step 2: Get Historical Channel Performance
For each channel mentioned in either allocation:
```sql
SELECT
    channel_name,
    COUNT(DISTINCT date) AS data_points,
    ROUND(AVG(roas), 4) AS avg_roas,
    ROUND(AVG(ctr), 6) AS avg_ctr,
    ROUND(AVG(conversion_rate), 6) AS avg_conversion_rate,
    ROUND(AVG(cpc), 2) AS avg_cpc,
    ROUND(AVG(spend_usd), 2) AS avg_daily_spend
FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS
WHERE client_id = :client_id
  AND channel_name IN (:channel_list)
  AND (:campaign_type IS NULL OR campaign_type = :campaign_type)
GROUP BY channel_name;
```

If a channel has no historical data for this client, use cross-client averages as a fallback:
```sql
SELECT channel_name, AVG(roas) AS avg_roas, AVG(ctr) AS avg_ctr,
    AVG(conversion_rate) AS avg_conversion_rate, AVG(cpc) AS avg_cpc
FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS
WHERE channel_name = :channel_name
GROUP BY channel_name;
```

### Step 3: Project Metrics for Each Scenario
For each channel in an allocation:
```
projected_revenue = budget * avg_roas
projected_clicks = budget / avg_cpc (if avg_cpc > 0)
projected_impressions = projected_clicks / avg_ctr (if avg_ctr > 0)
projected_conversions = projected_clicks * avg_conversion_rate
```

### Step 4: Calculate Totals and Deltas
```
total_current_budget = SUM(current channel budgets)
total_proposed_budget = SUM(proposed channel budgets)
total_current_revenue = SUM(current projected revenues)
total_proposed_revenue = SUM(proposed projected revenues)

delta_revenue = total_proposed_revenue - total_current_revenue
delta_impressions = total_proposed_impressions - total_current_impressions
delta_conversions = total_proposed_conversions - total_current_conversions
delta_roas = (total_proposed_revenue / total_proposed_budget) - (total_current_revenue / total_current_budget)
```

### Step 5: Generate Comparison Report

```markdown
## What-If Scenario Analysis: {client_name}

### Scenario Overview
| Metric | Current | Proposed | Delta | Change % |
|--------|---------|----------|-------|----------|
| Total Budget | ${current_budget} | ${proposed_budget} | ${delta_budget} | {pct}% |
| Projected Revenue | ${current_rev} | ${proposed_rev} | ${delta_rev} | {pct}% |
| Projected ROAS | {current_roas}x | {proposed_roas}x | {delta_roas} | - |
| Projected Impressions | {current_imp} | {proposed_imp} | {delta_imp} | {pct}% |
| Projected Conversions | {current_conv} | {proposed_conv} | {delta_conv} | {pct}% |

### Channel-Level Breakdown

#### Current Scenario
| Channel | Budget | Proj. Revenue | Proj. ROAS | Proj. Clicks | Proj. Conv |
|---------|--------|--------------|-----------|-------------|-----------|
{rows}

#### Proposed Scenario
| Channel | Budget | Proj. Revenue | Proj. ROAS | Proj. Clicks | Proj. Conv |
|---------|--------|--------------|-----------|-------------|-----------|
{rows}

### Recommendation
**{PROPOSED/CURRENT} scenario is recommended.**
- {Rationale grounded in projected metrics}
- {Key advantage of recommended scenario}
- {Risk factors to consider}

### Confidence Assessment
- **Overall Confidence:** {HIGH/MEDIUM/LOW}
- Channels with strong data (100+ days): {list}
- Channels with weak data (<30 days): {list} (projections less reliable)
- Channels with no client-specific data (using cross-client avg): {list}
```

### Step 6: Sensitivity Notes
- If budget totals differ between scenarios, note this explicitly
- If any channel has < 30 data points, flag as "low confidence"
- If using cross-client fallback data, flag with asterisk and note

## Error Handling
- Client not found: suggest alternatives
- Channel name not recognized: show valid channel names from DIM_CHANNEL
- No historical data for any channel: cannot project, return error with explanation
- All channels have < 10 data points: return analysis with LOW confidence warning
