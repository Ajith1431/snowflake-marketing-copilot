---
name: pitch-generator
description: "Generates a client-ready campaign pitch narrative with data-backed recommendations, creative direction aligned to brand guidelines, and projected KPIs. Use when: creating a pitch deck, preparing a client presentation, or generating a campaign proposal."
---

# Pitch Generator Skill

## Purpose
Generate a polished, data-driven campaign pitch document for a client, grounded in historical performance data and brand guidelines.

## Inputs
- `client_name` (required): Target client brand name
- `product_name` (required): Product or service being promoted
- `campaign_objective` (required): What the campaign aims to achieve
- `recommended_channels` (optional): Preferred channels, or auto-select from performance data
- `budget` (optional): Total campaign budget in USD
- `target_segments` (optional): Audience segments to target
- `performance_context` (optional): Output from campaign-analysis skill
- `brand_guidelines` (optional): Output from client-intelligence skill's brand section

## Workflow

### Step 1: Gather Missing Context
If `performance_context` is not provided, run the equivalent of the campaign-analysis queries for the client:
- Overall ROAS, top channels, best campaign types
- Top performing audience segments

If `brand_guidelines` is not provided, search BRAND_SEARCH:
- Query: "brand voice and creative direction for {client_name}"
- Extract: tone_keywords, dos, donts, color_palette

### Step 2: Select Channels (if not specified)
Pick top 3-4 channels by historical ROAS for this client. If no history, use industry benchmarks:
- Retail: Instagram, Google Search, Email, Facebook
- Technology: LinkedIn, Google Search, YouTube, Programmatic Display
- Healthcare: Facebook, Google Search, Email, YouTube
- Finance: LinkedIn, Google Search, Programmatic Display, Email
- Sportswear / Fashion: Instagram, TikTok, YouTube, Facebook
- (other industries use balanced mix)

### Step 3: Allocate Budget
If budget is provided, distribute across selected channels based on historical ROAS weights:
```
channel_weight = channel_historical_roas / sum(all_selected_channel_roas)
channel_budget = total_budget * channel_weight
```
Round to nearest $100. Ensure allocations sum to total budget.

### Step 4: Project KPIs
For each channel, project using historical averages:
```
projected_impressions = channel_budget / historical_avg_cpc * (1 / historical_avg_ctr)
projected_clicks = channel_budget / historical_avg_cpc
projected_conversions = projected_clicks * historical_avg_conversion_rate
projected_revenue = channel_budget * historical_avg_roas
```

### Step 5: Generate Pitch Document

Use AI_COMPLETE (or the LLM in the agent) to generate each section, grounding in the data:

```markdown
# Campaign Pitch: {product_name} for {client_name}
## Prepared by NovaSpark Agency | {current_date}

---

## 1. Executive Summary
{2-3 sentences summarizing the opportunity, strategy, and expected impact.
Ground in: client industry position, campaign objective, projected ROAS.}

## 2. Client & Product Overview
- **Client:** {client_name} ({industry}, {region})
- **Product:** {product_name}
- **Market Context:** {relevant market events from MARKET_SEARCH}
- **Historical Performance:** {overall ROAS}x ROAS across {campaign_count} campaigns

## 3. Campaign Objective & KPIs
- **Primary Objective:** {campaign_objective}
- **Target KPIs:**
  - ROAS: {projected_roas}x (based on historical {historical_roas}x)
  - Impressions: {projected_impressions}
  - Conversions: {projected_conversions}
  - CTR: {projected_ctr}%

## 4. Target Audience Analysis
{For each target segment:}
- **{segment_name}** ({age_band}, {gender_skew}, {income_level})
  - Historical conversion rate: {conv_rate}%
  - Estimated reach: {estimated_size}
  - Key interests: {interests}

## 5. Recommended Channel Strategy
| Channel | Budget | % of Total | Projected ROAS | Est. Impressions | Est. Conversions |
|---------|--------|-----------|----------------|-----------------|-----------------|
{rows for each selected channel}
| **Total** | **${budget}** | **100%** | **{blended_roas}x** | **{total_impressions}** | **{total_conversions}** |

**Rationale:** {Why these channels, based on historical data}

## 6. Creative Direction
- **Brand Voice:** {tone_keywords}
- **Messaging Approach:** {aligned with brand guidelines}
- **Visual Direction:** Color palette {color_palette}
- **Do:** {dos from brand guidelines}
- **Avoid:** {donts from brand guidelines}
- **Suggested Headlines:** {3 headline options aligned with tone}

## 7. Expected Impact & Timeline
- **Campaign Duration:** {recommended duration based on historical campaign_duration_days}
- **Projected Revenue:** ${projected_revenue}
- **Projected ROI:** {roi_pct}%
- **Break-even Point:** Day {break_even_estimate}

---
**Confidence Level:** {HIGH/MEDIUM/LOW}
{Reasoning: based on data volume, historical consistency}

**Next Steps:**
1. Client approval of strategy and budget
2. Creative brief development
3. Media plan finalization
4. Campaign launch
```

### Step 6: Quality Checks
Before returning:
- Verify all monetary projections are reasonable (ROAS between 1-10x)
- Ensure brand guideline compliance (no don'ts in creative direction)
- Check that budget allocations sum to 100%
- Confirm all referenced segments belong to this client

## Output Format
Return the full markdown pitch document, ready for presentation.

## Confidence Levels
- **HIGH**: 20+ completed campaigns, 3+ months of data, all sections populated
- **MEDIUM**: 10-19 campaigns or some sections use industry benchmarks
- **LOW**: <10 campaigns, heavy reliance on benchmarks, missing brand guidelines
