---
name: event-strategy
description: "Synthesizes internal campaign data with live internet intelligence to produce a complete event-specific marketing strategy with competitor benchmarking, budget allocation, timing recommendation, and creative direction. The final output of the event intelligence pipeline."
---

# Event Strategy Skill

## Purpose
Generate a complete, data-driven marketing strategy for a specific market event by combining three inputs: internal campaign performance data (from Snowflake), live internet intelligence (from the event-intelligence run), and competitive positioning (from the competitor-analysis skill).

## Prerequisites
- Completed event-intelligence run with `run_id`
- Completed competitor-analysis with `competitor_analysis` dict
- Client must exist in DIM_CLIENT with historical campaign data

## Inputs
- `run_id` (required): From event-intelligence output
- `client_name` (required): Client brand name
- `event_name` (required): Event name
- `budget_usd` (required): Total campaign budget in USD
- `campaign_objective` (required): e.g., "Brand Awareness", "Sales Conversion"
- `markets` (required): Target market codes
- `competitor_analysis` (required): Full output dict from competitor-analysis skill
- `intelligence_summary` (required): The `summary` field from event-intelligence output

## Workflow

### Step 1: Pull Brand Guidelines
Search BRAND_SEARCH Cortex Search service:
```
Query: "brand voice tone messaging guidelines dos donts for {client_name}"
Filter: client_name = {client_name}
Limit: 3 results
```
Extract: tone_keywords, dos, donts, color_palette, messaging framework.

### Step 2: Pull Best Historical Campaigns
```sql
SELECT fc.campaign_name, fc.campaign_type,
    ROUND(AVG(m.roas), 2) AS avg_roas,
    SUM(m.impressions) AS total_impressions,
    ROUND(AVG(m.ctr) * 100, 3) AS avg_ctr_pct,
    SUM(m.conversions) AS total_conversions
FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS m
JOIN MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN fc ON m.campaign_id = fc.campaign_id
WHERE fc.client_name = :client_name
GROUP BY fc.campaign_name, fc.campaign_type
ORDER BY avg_roas DESC
LIMIT 5;
```

### Step 3: Pull Google Trends Peak Timing
```sql
SELECT keyword, trend_date AS peak_date,
    interest_score AS peak_score
FROM MARKETING_COPILOT.ANALYTICS.DIM_EVENT_TRENDS
WHERE run_id = :run_id AND is_peak = TRUE
ORDER BY peak_score DESC
LIMIT 1;
```

### Step 4: Calculate Launch Timing
```
peak_date = result from Step 3
recommended_launch = peak_date - 42 days (6 weeks before peak = optimal awareness window)

IF recommended_launch < today:
    recommended_launch = today + 7 days

campaign_end = peak_date + 14 days (2 weeks post-peak for conversion tail)
campaign_duration = campaign_end - recommended_launch

Phase breakdown:
  Phase 1 - Awareness:   recommended_launch to (recommended_launch + duration * 0.4)
  Phase 2 - Consideration: Phase 1 end to (recommended_launch + duration * 0.7)
  Phase 3 - Conversion:  Phase 2 end to campaign_end
```

### Step 5: Build Channel Allocation
Start with `recommended_focus_channels` from competitor_analysis input (top 3 channels ranked by our ROAS + low competitor presence).

For each recommended channel, calculate allocation:
```
historical_roas = from client's FACT_CAMPAIGN_METRICS for this channel
competitor_gap_score = 1.0 if competitor presence is LOW, 0.7 if MEDIUM, 0.4 if HIGH

channel_weight = historical_roas * competitor_gap_score
total_weight = sum of all channel weights
allocation_pct = channel_weight / total_weight * 100
channel_budget = budget_usd * allocation_pct / 100
```

Ensure allocations sum to 100%. Round to nearest $100.

Add 2 additional channels from historical top performers if fewer than 5 channels allocated.

### Step 6: Project KPIs per Channel
For each channel:
```
projected_impressions = channel_budget / historical_avg_cpc * (1 / historical_avg_ctr)
projected_clicks = channel_budget / historical_avg_cpc
projected_conversions = projected_clicks * historical_avg_conversion_rate
projected_revenue = channel_budget * historical_avg_roas
```

Aggregate totals across all channels for overall projections.

### Step 7: Generate Strategy Narrative
Call Snowflake Cortex Complete with this prompt:
```
You are a senior marketing strategist at NovaSpark Agency writing an event campaign strategy for {client_name}.

Event: {event_name}
Budget: ${budget_usd}
Objective: {campaign_objective}
Markets: {markets}

DATA CONTEXT:
- Brand guidelines: {tone_keywords}, dos: {dos}, donts: {donts}
- Best historical campaigns: {top_campaigns_json}
- Peak trend: "{peak_keyword}" peaks on {peak_date} with score {peak_score}
- Rising search queries: {rising_queries}
- Top competitor: {most_active_competitor} with {threat_level} threat level
- Our channel strengths: {our_strengths}
- Opportunities identified: {our_opportunities}
- Key differentiator: {key_differentiator}

CHANNEL ALLOCATION:
{channel_allocation_table}

Write a professional strategy document with these sections:
1. Executive Summary (3 sentences)
2. Event Context and Market Opportunity (how this event creates opportunity for {client_name})
3. Competitive Landscape (our position vs competitors based on the data)
4. Target Audience Strategy (which segments to prioritize and why)
5. Channel Strategy and Budget Allocation (justify each channel choice with data)
6. Creative Direction (aligned with brand guidelines, event theme, and competitor gaps)
7. Campaign Timeline (phased approach with specific dates)
8. Projected Impact (KPI projections grounded in historical performance)
9. Risk Mitigation (competitor threats and how to counter them)

Ground every recommendation in the data provided. State confidence levels.
Do not invent metrics. Reference specific numbers from the data.
```

### Step 8: Save Strategy to Snowflake
```sql
INSERT INTO MARKETING_COPILOT.ANALYTICS.EVENT_STRATEGY_OUTPUT
(strategy_id, run_id, client_name, event_name, strategy_text,
 competitor_comparison, recommended_channels, recommended_budget_split,
 timing_recommendation, expected_roas_min, expected_roas_max,
 projected_impressions, confidence_level)
SELECT
    :strategy_id, :run_id, :client_name, :event_name, :strategy_text,
    PARSE_JSON(:competitor_comparison_json),
    PARSE_JSON(:recommended_channels_json),
    PARSE_JSON(:budget_split_json),
    :timing_recommendation,
    :expected_roas_min, :expected_roas_max,
    :projected_impressions, :confidence_level;
```

### Step 9: Return Complete Strategy
```json
{
  "strategy_id": "STR_RUN_20260829_183117",
  "run_id": "RUN_20260829_183117",
  "client_name": "UrbanThread",
  "event_name": "FIFA World Cup 2026",
  "strategy_narrative": "Full 9-section markdown strategy document",
  "channel_allocation": {
    "Instagram": {"budget": 75000, "pct": 25, "projected_roas": 2.8},
    "TikTok": {"budget": 60000, "pct": 20, "projected_roas": 2.5},
    "YouTube": {"budget": 90000, "pct": 30, "projected_roas": 3.2},
    "Google Search": {"budget": 45000, "pct": 15, "projected_roas": 2.3},
    "Email": {"budget": 30000, "pct": 10, "projected_roas": 1.8}
  },
  "timing": {
    "recommended_launch": "2026-06-07",
    "peak_date": "2026-07-19",
    "campaign_end": "2026-08-02",
    "duration_days": 56,
    "phases": {
      "awareness": "2026-06-07 to 2026-06-29",
      "consideration": "2026-06-30 to 2026-07-16",
      "conversion": "2026-07-17 to 2026-08-02"
    }
  },
  "projected_kpis": {
    "total_impressions": 15000000,
    "total_clicks": 450000,
    "total_conversions": 18000,
    "projected_revenue": 750000,
    "projected_roas_range": "2.3x - 3.2x",
    "blended_roas": 2.5
  },
  "competitor_positioning": {
    "biggest_threat": "Nike (HIGH presence, neutral sentiment)",
    "biggest_opportunity": "TikTok -- low competitor presence, strong our ROAS",
    "key_differentiator": "AI-generated insight from competitor-analysis"
  },
  "brand_alignment": {
    "tone": ["bold", "elegant", "expressive"],
    "dos": ["Use active voice", "Feature real customers"],
    "donts": ["Use competitor names negatively", "Ignore accessibility"]
  },
  "confidence_level": "HIGH",
  "saved_to_snowflake": true
}
```

### Step 10: Print Strategy Summary
```
+=============================================+
|  EVENT STRATEGY GENERATED                    |
|  Client: {client_name}                       |
|  Event: {event_name}                         |
|  Budget: ${budget_usd}                       |
|  Duration: {duration} days                   |
|  Launch: {recommended_launch}                |
|  Projected ROAS: {blended_roas}x             |
|  Confidence: {confidence_level}              |
|  Saved to: EVENT_STRATEGY_OUTPUT             |
+=============================================+

Channel Allocation:
  Channel        | Budget    | %   | Proj. ROAS
  -----------------------------------------------
  YouTube        | $90,000   | 30% | 3.2x
  Instagram      | $75,000   | 25% | 2.8x
  TikTok         | $60,000   | 20% | 2.5x
  Google Search  | $45,000   | 15% | 2.3x
  Email          | $30,000   | 10% | 1.8x
  -----------------------------------------------
  TOTAL          | $300,000  |100% | 2.5x (blended)

Timeline:
  Phase 1 (Awareness):     Jun 7 - Jun 29
  Phase 2 (Consideration): Jun 30 - Jul 16
  Phase 3 (Conversion):    Jul 17 - Aug 2
  Peak Interest:           Jul 19 (score: 100)
```

## Complete Pipeline Flow
```
event-intelligence  -->  competitor-analysis  -->  event-strategy
(pull live data)         (compare brands)          (generate strategy)
     |                        |                         |
     v                        v                         v
RAW tables              Comparison matrix       9-section strategy
Dynamic tables          Threats/opportunities   Channel allocation
Cortex Search           AI differentiator       Timing + projections
                                                Saved to Snowflake
```

## Data Sources Used
| Source | Purpose |
|--------|---------|
| BRAND_SEARCH (Cortex Search) | Client brand guidelines for creative direction |
| FACT_CAMPAIGN_METRICS | Historical channel performance for projections |
| DIM_EVENT_TRENDS | Peak timing for launch date calculation |
| DIM_COMPETITOR_PRESENCE | Competitor media footprint |
| DIM_WEB_INTELLIGENCE | Competitor themes and channel intelligence |
| EVENT_STRATEGY_OUTPUT | Saves the generated strategy for future reference |
| Cortex Complete (LLM) | Generates the 9-section strategy narrative |

## Error Handling
- If no historical campaigns for client: use industry benchmarks from all clients in same industry
- If peak_date is in the past: use today + 7 days as launch date
- If budget_usd < $10,000: warn "Budget may be insufficient for multi-channel strategy"
- If competitor_analysis is empty: skip competitive sections, reduce confidence to MEDIUM
- If Cortex Complete fails: return channel allocation and projections without narrative
