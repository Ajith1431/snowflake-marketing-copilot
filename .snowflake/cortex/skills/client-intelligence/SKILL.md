---
name: client-intelligence
description: "Retrieves and summarizes all available intelligence for a specific client brand. Gathers client profile, campaign performance snapshot, audience health, sentiment overview, and brand guidelines into a single structured briefing. Use when: preparing for a client meeting, starting a new pitch, or needing a full client overview."
---

# Client Intelligence Skill

## Purpose
Produce a comprehensive intelligence briefing for any NovaSpark Agency client by pulling data from all available sources: structured analytics, customer feedback, and brand guidelines.

## Inputs
- `client_name` (required): Name of the client brand (e.g., "LuminaRetail", "TechVista")

## Workflow

### Step 1: Resolve Client Identity
```sql
SELECT client_id, client_name, industry, region, annual_revenue_usd,
       contract_start_date, primary_contact, status
FROM MARKETING_COPILOT.ANALYTICS.DIM_CLIENT
WHERE UPPER(client_name) = UPPER(:client_name);
```
If no match, suggest similar names from DIM_CLIENT and ask the user to clarify.

### Step 2: Campaign Portfolio Summary
```sql
SELECT
    COUNT(DISTINCT campaign_id) AS total_campaigns,
    COUNT(DISTINCT CASE WHEN status = 'COMPLETED' THEN campaign_id END) AS completed,
    COUNT(DISTINCT CASE WHEN status = 'ACTIVE' THEN campaign_id END) AS active,
    COUNT(DISTINCT CASE WHEN status = 'PLANNED' THEN campaign_id END) AS planned,
    MIN(start_date) AS earliest_campaign,
    MAX(end_date) AS latest_campaign,
    SUM(total_budget_usd) AS total_budget_allocated
FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN
WHERE client_id = :client_id;
```

### Step 3: Performance Snapshot
```sql
SELECT
    SUM(spend_usd) AS total_spend,
    SUM(revenue_usd) AS total_revenue,
    ROUND(SUM(revenue_usd) / NULLIF(SUM(spend_usd), 0), 2) AS overall_roas,
    ROUND(AVG(ctr) * 100, 2) AS avg_ctr_pct,
    ROUND(AVG(conversion_rate) * 100, 2) AS avg_conversion_rate_pct,
    SUM(impressions) AS total_impressions,
    SUM(clicks) AS total_clicks,
    SUM(conversions) AS total_conversions
FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS
WHERE client_id = :client_id;
```

### Step 4: Channel Performance Ranking
```sql
SELECT channel_name, channel_type,
    SUM(spend_usd) AS spend,
    SUM(revenue_usd) AS revenue,
    ROUND(AVG(roas), 2) AS avg_roas,
    ROUND(AVG(ctr) * 100, 2) AS avg_ctr_pct
FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS
WHERE client_id = :client_id
GROUP BY channel_name, channel_type
ORDER BY avg_roas DESC;
```

### Step 5: Audience Sentiment
```sql
SELECT
    COUNT(*) AS feedback_count,
    ROUND(AVG(sentiment_score), 3) AS avg_sentiment,
    ROUND(AVG(rating), 1) AS avg_rating,
    COUNT(CASE WHEN sentiment_score > 0.3 THEN 1 END) AS positive_count,
    COUNT(CASE WHEN sentiment_score BETWEEN -0.3 AND 0.3 THEN 1 END) AS neutral_count,
    COUNT(CASE WHEN sentiment_score < -0.3 THEN 1 END) AS negative_count
FROM MARKETING_COPILOT.ANALYTICS.FACT_CUSTOMER_FEEDBACK
WHERE client_id = :client_id;
```

### Step 6: Brand Guidelines (via Cortex Search)
Search `BRAND_SEARCH` for the client's brand voice, visual identity, and messaging framework.
Return: tone keywords, dos/donts, and a 2-3 sentence brand personality summary.

### Step 7: Compile and Return

Structure the response as:

```markdown
## Client Intelligence Briefing: {client_name}

### Profile
- Industry: {industry} | Region: {region}
- Annual Revenue: ${annual_revenue_usd}
- Contract Since: {contract_start_date}
- Status: {status}

### Campaign Portfolio
- Total Campaigns: {total} (Active: {active}, Completed: {completed}, Planned: {planned})
- Date Range: {earliest} to {latest}
- Total Budget: ${total_budget}

### Performance Snapshot
- Total Spend: ${spend} | Revenue: ${revenue} | ROAS: {roas}x
- Avg CTR: {ctr}% | Avg Conversion Rate: {conv_rate}%
- Total Impressions: {impressions} | Clicks: {clicks} | Conversions: {conversions}

### Channel Ranking (by ROAS)
| Channel | Spend | Revenue | ROAS | CTR |
|---------|-------|---------|------|-----|
(sorted table)

### Audience Sentiment
- Avg Sentiment Score: {sentiment} | Avg Rating: {rating}/5
- Positive: {pos}% | Neutral: {neutral}% | Negative: {neg}%

### Brand Personality
- Tone: {tone_keywords}
- Key Dos: {dos}
- Key Don'ts: {donts}
- Summary: {2-3 sentence brand personality description}

### Data Completeness
- Confidence: HIGH/MEDIUM/LOW
- Missing: {list any unavailable data points}
```

## Error Handling
- If client_name not found: suggest closest matches from DIM_CLIENT
- If no campaigns exist: note "New client - no campaign history available"
- If no feedback data: note "No customer feedback recorded yet"
