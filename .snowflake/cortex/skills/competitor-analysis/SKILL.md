---
name: competitor-analysis
description: "Compares client brand vs competitors across news sentiment, web presence, and internal campaign performance benchmarks. Requires a completed event-intelligence run. Use when: preparing competitive positioning, identifying threats and opportunities, or benchmarking brand presence for an event."
---

# Competitor Analysis Skill

## Purpose
Build a competitive comparison matrix that combines live internet intelligence (news sentiment, web presence) with internal campaign performance data to identify threats, opportunities, and strategic gaps.

## Prerequisites
- A completed event-intelligence run (need `run_id` from its output)
- Data must be loaded into the ANALYTICS dynamic tables

## Inputs
- `run_id` (required): From event-intelligence skill output (e.g., "RUN_20260829_183117")
- `client_name` (required): Client brand name (must match DIM_CLIENT)
- `competitors` (required): List of competitor brand names tracked in the intelligence run

## Workflow

### Step 1: Pull Competitor Media Presence
```sql
SELECT brand_name, brand_type, total_articles,
    positive_count, negative_count, neutral_count,
    avg_sentiment_score, overall_sentiment, media_presence
FROM MARKETING_COPILOT.ANALYTICS.DIM_COMPETITOR_PRESENCE
WHERE run_id = :run_id
ORDER BY total_articles DESC;
```

### Step 2: Pull Web Intelligence for Competitor Activity
```sql
SELECT competitor_activity, recommended_channels,
    consumer_sentiment, key_findings
FROM MARKETING_COPILOT.ANALYTICS.DIM_WEB_INTELLIGENCE
WHERE run_id = :run_id;
```

### Step 3: Pull Internal Campaign Performance for Client
```sql
SELECT m.channel_name,
    ROUND(AVG(m.roas), 2) AS avg_roas,
    ROUND(AVG(m.ctr) * 100, 3) AS avg_ctr_pct,
    SUM(m.impressions) AS total_impressions,
    COUNT(DISTINCT m.campaign_id) AS campaign_count
FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS m
WHERE m.client_name = :client_name
GROUP BY m.channel_name
ORDER BY avg_roas DESC;
```

### Step 4: Build Comparison Matrix
For each brand (client + each competitor), build a row:
```json
{
  "brand": "Nike",
  "brand_type": "COMPETITOR",
  "media_presence": "HIGH",
  "sentiment": "Neutral",
  "sentiment_score": -0.20,
  "total_coverage": 10,
  "positive_articles": 0,
  "negative_articles": 2,
  "estimated_threat": "HIGH"
}
```

**Threat estimation logic:**
- **HIGH**: Competitor + positive/neutral sentiment + HIGH media presence
- **MEDIUM**: Competitor + neutral sentiment + MEDIUM presence
- **LOW**: Competitor + negative sentiment OR LOW presence
- **N/A**: Our brand (not a threat to ourselves)

### Step 5: Identify Strategic Gaps

**Our strengths:**
Channels where client avg_roas > 3.0 AND campaign_count > 5.

**Competitor threats:**
Competitors with media_presence = 'High' AND overall_sentiment IN ('Positive', 'Neutral').

**Our opportunities:**
If a competitor has LOW media presence on any channel AND our historical ROAS on that channel > 2.5 --> flag as "Underserved channel opportunity: {channel} -- competitor {name} has low presence, our ROAS is {roas}x"

### Step 6: Generate Key Differentiator Insight
Call Snowflake Cortex Complete:
```sql
SELECT SNOWFLAKE.CORTEX.COMPLETE(
    'claude-sonnet-4-6',
    ARRAY_CONSTRUCT(
        OBJECT_CONSTRUCT('role', 'system', 'content',
            'You are a marketing strategist. Analyze competitive data and give one actionable insight.'),
        OBJECT_CONSTRUCT('role', 'user', 'content',
            'Based on this competitor analysis data:
             Comparison matrix: {comparison_matrix_json}
             Our strengths: {our_strengths}
             Competitor threats: {competitor_threats}
             In 2 sentences, what is the single biggest strategic opportunity for {client_name}?
             Be specific about channels and timing.')
    )
) AS insight;
```

### Step 7: Return Results
```json
{
  "comparison_matrix": [
    {"brand": "Nike", "brand_type": "OUR_BRAND", "media_presence": "-", "sentiment": "Positive", "estimated_threat": "N/A"},
    {"brand": "Adidas", "brand_type": "COMPETITOR", "media_presence": "MEDIUM", "sentiment": "Neutral", "estimated_threat": "MEDIUM"},
    {"brand": "Puma", "brand_type": "COMPETITOR", "media_presence": "LOW", "sentiment": "Positive", "estimated_threat": "LOW"}
  ],
  "our_strengths": [
    {"channel": "YouTube", "avg_roas": 3.2, "campaigns": 12},
    {"channel": "Instagram", "avg_roas": 3.0, "campaigns": 15}
  ],
  "competitor_threats": [
    {"competitor": "Nike", "reason": "HIGH media presence with neutral sentiment"}
  ],
  "our_opportunities": [
    "Underserved channel: TikTok -- Adidas has LOW presence, our ROAS is 2.8x"
  ],
  "key_differentiator": "AI-generated 2-sentence strategic insight",
  "recommended_focus_channels": ["YouTube", "Instagram", "TikTok"],
  "confidence_note": "Based on 32 news articles and 8 web research queries from run RUN_20260829_183117"
}
```

### Step 8: Print Comparison Table
```
Brand         | Presence | Sentiment | Score | Threat
------------------------------------------------------
Nike          | -        | Positive  |  0.20 | N/A (us)
Adidas        | MEDIUM   | Neutral   |  0.00 | MEDIUM
Puma          | LOW      | Positive  |  0.10 | LOW
------------------------------------------------------
Key Differentiator: {2-sentence AI insight}
Recommended Focus: YouTube, Instagram, TikTok
```

## Data Sources Used
| Source | Table | Purpose |
|--------|-------|---------|
| Event Intelligence | DIM_COMPETITOR_PRESENCE | News coverage counts, sentiment aggregation, media presence level |
| Event Intelligence | DIM_WEB_INTELLIGENCE | Competitor creative themes, platform activity, channel recommendations |
| Historical Campaigns | FACT_CAMPAIGN_METRICS | Client's own channel performance (ROAS, CTR, campaign count) |
| Cortex Complete | LLM | Strategic insight generation from combined data |

## Downstream Usage
The output dict is passed to the **event-strategy** skill as the `competitor_analysis` input parameter, where it feeds into channel allocation and budget decisions.
