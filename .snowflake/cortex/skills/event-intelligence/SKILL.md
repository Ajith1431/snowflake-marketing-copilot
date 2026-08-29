---
name: event-intelligence
description: "Orchestrates live internet data pull for a specific market event and client, then loads all results into Snowflake. Pulls Google Trends, news articles (Event Registry + Google News RSS), and web intelligence (Cortex Complete). Use when: preparing for a major market event, competitive analysis for a specific occasion, or gathering real-time market intelligence for campaign planning."
---

# Event Intelligence Skill

## Purpose
Pull live intelligence from the internet about a specific market event (e.g., FIFA World Cup 2026, Black Friday, Paris Fashion Week) for a client brand, analyze competitor activity, and load all data into Snowflake for downstream analysis and strategy generation.

## Inputs
- `client_name` (required): Must match a name in MARKETING_COPILOT.ANALYTICS.DIM_CLIENT
- `event_name` (required): Full event name (e.g., "FIFA World Cup 2026")
- `event_keywords` (required): List of 5-8 search keywords for Google Trends
- `competitors` (required): List of competitor brand names to track
- `markets` (required): List of market codes (e.g., ["US", "GB"])
- `news_api_key` (optional): From config.EVENT_REGISTRY_API_KEY; falls back to Google News RSS if empty

## Data Sources
| Source | What It Pulls | API |
|--------|--------------|-----|
| Google Trends | Interest over time, rising queries, regional interest | pytrends (free) |
| News Articles | Event news, brand mentions, competitor coverage with sentiment | Event Registry API + Google News RSS fallback |
| Web Intelligence | Competitor themes, platform presence, consumer sentiment, channel recommendations | Snowflake Cortex Complete (LLM-powered web research) |

## Workflow

### Step 1: Validate Client
```sql
SELECT client_id, client_name, industry, region
FROM MARKETING_COPILOT.ANALYTICS.DIM_CLIENT
WHERE UPPER(client_name) = UPPER(:client_name);
```
If no match found, return error: "Client {client_name} not found in system. Available clients: {list from DIM_CLIENT}"

### Step 2: Log Start
```
Starting Event Intelligence for {event_name}
  Client: {client_name}
  Competitors: {competitors}
  Markets: {markets}
  Keywords: {event_keywords}
```

### Step 3: Run Intelligence Collection
Call `src/intelligence/intelligence_orchestrator.py` -> `run_full_intelligence()` with all inputs.

This runs 3 pullers in sequence:
1. **Google Trends** (pytrends) - interest_over_time, related_queries, interest_by_region
2. **News Articles** (Event Registry primary, Google News RSS fallback) - event news, brand news, competitor news with keyword sentiment
3. **Web Intelligence** (Cortex Complete) - 8 structured web research queries about competitor activity, consumer sentiment, channel recommendations

Store result as `intelligence_result`.

### Step 4: Check Confidence
If `intelligence_result.confidence == "INSUFFICIENT DATA"`:
  - Return warning: "Insufficient data returned from all sources. Check API keys and network connectivity."
  - Do NOT proceed to load step.

Confidence levels:
- **HIGH**: All 3 sources returned data
- **MEDIUM**: 2 of 3 sources returned data
- **LOW**: Only 1 source returned data
- **INSUFFICIENT DATA**: No sources returned data

### Step 5: Load to Snowflake
Call `src/intelligence/snowflake_loader.py` -> `load_intelligence_run(session, intelligence_result)`.

This inserts into 4 RAW tables:
| Table | What Gets Loaded |
|-------|-----------------|
| RAW.EVENT_INTELLIGENCE_RUNS | Run metadata: run_id, client, event, competitors, confidence |
| RAW.GOOGLE_TRENDS_DATA | Daily interest scores per keyword, peak flags |
| RAW.NEWS_ARTICLES | All articles with brand tags, sentiment labels, sentiment scores |
| RAW.WEB_INTELLIGENCE | Each web query result with findings, activity, channels |

### Step 6: Check Load Status
If `load_result.load_status == "FAILED"`: return error with load_result.errors list.

### Step 7: Wait for Dynamic Tables
Wait 90 seconds for these Dynamic Tables to refresh (TARGET_LAG = 1 minute):
- `ANALYTICS.DIM_EVENT_TRENDS` -- trends with interest_level classification
- `ANALYTICS.DIM_NEWS_SENTIMENT` -- articles with brand_type tagging
- `ANALYTICS.DIM_COMPETITOR_PRESENCE` -- aggregated competitor media presence and sentiment
- `ANALYTICS.DIM_WEB_INTELLIGENCE` -- web research results joined with run metadata

Print countdown: "Waiting for Snowflake Dynamic Tables... {N}s remaining"

### Step 8: Validate Dynamic Tables
```sql
SELECT COUNT(*) FROM MARKETING_COPILOT.ANALYTICS.DIM_EVENT_TRENDS WHERE run_id = :run_id;
SELECT COUNT(*) FROM MARKETING_COPILOT.ANALYTICS.DIM_NEWS_SENTIMENT WHERE run_id = :run_id;
SELECT COUNT(*) FROM MARKETING_COPILOT.ANALYTICS.DIM_COMPETITOR_PRESENCE WHERE run_id = :run_id;
```

### Step 9: Return Summary
```json
{
  "status": "SUCCESS | PARTIAL | FAILED",
  "run_id": "RUN_YYYYMMDD_HHMMSS",
  "confidence": "HIGH | MEDIUM | LOW",
  "sources_succeeded": 3,
  "records_loaded": {
    "google_trends": 465,
    "news_articles": 32,
    "web_intelligence": 8
  },
  "dynamic_tables_populated": {
    "dim_event_trends": 465,
    "dim_news_sentiment": 32,
    "dim_competitor_presence": 4
  },
  "summary": {
    "peak_trend_keyword": "World Cup 2026",
    "peak_trend_date": "2026-07-19",
    "peak_trend_score": 100,
    "top_news_headline": "Brand Innovators FIFA World Cup Ad Tracker 2026",
    "most_active_competitor": "Nike",
    "top_trending_channel": "Instagram",
    "key_insight": "Nike leads competitor coverage with 10 articles..."
  },
  "ready_for_analysis": true
}
```

### Step 10: Print Status Box
```
+======================================+
|  EVENT INTELLIGENCE COMPLETE          |
|  Run ID: {run_id}                     |
|  Confidence: {confidence}             |
|  Sources: {N}/3 succeeded             |
|  Ready for analysis: YES/NO           |
+======================================+
```

## Downstream Usage
After this skill completes with `ready_for_analysis: true`, the data is available for:
- **competitor-analysis** skill: compare brand vs competitors across sentiment and presence
- **event-strategy** skill: generate a complete event marketing strategy
- **Cortex Agent**: query via `CampaignAnalytics` tool (trends + news in the semantic layer)
- **EVENT_NEWS_SEARCH**: Cortex Search service indexes all loaded news articles

## Error Handling
- Google Trends rate limited (429): retries once after 10s, then returns empty with error_message
- Event Registry API error: falls back to Google News RSS automatically
- Snowflake connector timeout: returns error with connection details
- ARRAY_CONSTRUCT in VALUES: loader uses INSERT...SELECT syntax
- Dynamic tables not refreshing: suspend/resume triggers immediate refresh
