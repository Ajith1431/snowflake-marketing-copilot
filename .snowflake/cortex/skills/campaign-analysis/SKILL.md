---
name: campaign-analysis
description: "Deep analysis of campaign performance for a specific client. Breaks down performance by channel, campaign type, audience segment, and time period. Identifies top and bottom performers and seasonal patterns. Use when: reviewing campaign results, preparing optimization recommendations, or auditing channel effectiveness."
---

# Campaign Analysis Skill

## Purpose
Perform a detailed campaign performance analysis for a client, identifying what worked, what didn't, and where the opportunities are.

## Inputs
- `client_name` (required): Name of the client brand
- `date_range` (optional): Start and end dates (defaults to all available data)
- `campaign_type` (optional): Filter to specific type (awareness/consideration/conversion/retention)

## Workflow

### Step 1: Resolve Client and Apply Filters
```sql
SELECT client_id FROM MARKETING_COPILOT.ANALYTICS.DIM_CLIENT
WHERE UPPER(client_name) = UPPER(:client_name);
```
Build WHERE clause fragments from optional inputs.

### Step 2: Channel Performance Ranking
```sql
SELECT
    m.channel_name,
    m.channel_type,
    COUNT(DISTINCT m.campaign_id) AS campaigns_using,
    SUM(m.spend_usd) AS total_spend,
    SUM(m.revenue_usd) AS total_revenue,
    ROUND(AVG(m.roas), 2) AS avg_roas,
    ROUND(AVG(m.ctr) * 100, 3) AS avg_ctr_pct,
    ROUND(AVG(m.conversion_rate) * 100, 3) AS avg_conv_rate_pct,
    ROUND(AVG(m.cpc), 2) AS avg_cpc
FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS m
WHERE m.client_id = :client_id
  AND (:start_date IS NULL OR m.date >= :start_date)
  AND (:end_date IS NULL OR m.date <= :end_date)
GROUP BY m.channel_name, m.channel_type
ORDER BY avg_roas DESC;
```

### Step 3: Campaign Type Breakdown
```sql
SELECT
    m.campaign_type,
    COUNT(DISTINCT m.campaign_id) AS campaign_count,
    SUM(m.spend_usd) AS total_spend,
    SUM(m.revenue_usd) AS total_revenue,
    ROUND(AVG(m.roas), 2) AS avg_roas,
    ROUND(AVG(m.ctr) * 100, 3) AS avg_ctr_pct
FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS m
WHERE m.client_id = :client_id
GROUP BY m.campaign_type
ORDER BY avg_roas DESC;
```

### Step 4: Top and Bottom Campaigns
```sql
-- Top 3 by ROAS
SELECT campaign_name, campaign_type, channel_name,
    SUM(spend_usd) AS spend, SUM(revenue_usd) AS revenue,
    ROUND(AVG(roas), 2) AS avg_roas
FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS
WHERE client_id = :client_id
GROUP BY campaign_name, campaign_type, channel_name
ORDER BY avg_roas DESC
LIMIT 3;

-- Bottom 3 by ROAS
SELECT campaign_name, campaign_type, channel_name,
    SUM(spend_usd) AS spend, SUM(revenue_usd) AS revenue,
    ROUND(AVG(roas), 2) AS avg_roas
FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS
WHERE client_id = :client_id
GROUP BY campaign_name, campaign_type, channel_name
ORDER BY avg_roas ASC
LIMIT 3;
```

### Step 5: Audience Segment Performance
```sql
SELECT
    seg.segment_name,
    seg.age_band,
    seg.income_level,
    AVG(b.allocation_pct) AS avg_allocation_pct,
    COUNT(DISTINCT b.campaign_id) AS campaigns_targeted,
    AVG(m.conversion_rate) AS avg_conv_rate,
    AVG(m.roas) AS avg_roas
FROM MARKETING_COPILOT.RAW.RAW_BRIDGE_CAMPAIGN_SEGMENT b
JOIN MARKETING_COPILOT.ANALYTICS.DIM_AUDIENCE_SEGMENT seg ON b.segment_id = seg.segment_id
JOIN MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS m ON b.campaign_id = m.campaign_id
WHERE seg.client_id = :client_id
GROUP BY seg.segment_name, seg.age_band, seg.income_level
ORDER BY avg_roas DESC;
```

### Step 6: Monthly Seasonality Pattern
```sql
SELECT
    DATE_TRUNC('MONTH', m.date) AS month,
    SUM(m.spend_usd) AS monthly_spend,
    SUM(m.revenue_usd) AS monthly_revenue,
    ROUND(AVG(m.roas), 2) AS avg_roas,
    SUM(m.conversions) AS total_conversions
FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS m
WHERE m.client_id = :client_id
GROUP BY month
ORDER BY month;
```

### Step 7: Compile Analysis

```markdown
## Campaign Performance Analysis: {client_name}
### Analysis Period: {date_range or "All Time"}

### Channel Ranking
| Rank | Channel | Type | Spend | Revenue | ROAS | CTR | Conv Rate | CPC |
(sorted by ROAS descending)

**Recommendation:** Increase investment in {top_channel}, reduce/optimize {bottom_channel}.

### Campaign Type Performance
| Type | Campaigns | Spend | Revenue | ROAS | CTR |
**Best performing type:** {type} with {roas}x ROAS

### Top 3 Campaigns (by ROAS)
1. {campaign_name} - {roas}x ROAS, ${revenue} revenue
2. ...
3. ...

### Bottom 3 Campaigns (by ROAS)
1. {campaign_name} - {roas}x ROAS (investigate: {reason})
2. ...
3. ...

### Audience Segment Insights
| Segment | Age Band | Allocation % | Campaigns | Conv Rate | ROAS |
**Best segment:** {segment_name} | **Underperforming:** {segment_name}

### Seasonal Patterns
- Peak months: {months with highest ROAS}
- Low months: {months with lowest ROAS}
- Recommendation: {timing advice}

### Confidence Level
- {HIGH if 10+ campaigns, MEDIUM if 5-9, LOW if <5}
- Note: {sample size context}
```

## Error Handling
- If fewer than 10 campaigns: add confidence warning "LOW confidence - limited campaign history"
- If no data for requested date range: expand range and note the adjustment
- If channel has < 3 data points: flag as "insufficient data for reliable ranking"
