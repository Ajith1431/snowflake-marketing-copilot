# Business Requirements: Marketing Co-Pilot & Pitch Engine

## Problem Statement

Marketing agencies spend significant time manually assembling campaign performance data, audience insights, and competitive intelligence to produce client pitch decks. Each pitch requires analysts to query multiple data sources, strategists to interpret trends, and creatives to package the narrative -- a process that can take days per client.

## Objectives

1. **Reduce pitch preparation time** from days to minutes using AI-driven analysis
2. **Deliver data-backed recommendations** grounded in historical campaign performance
3. **Ensure brand-safe messaging** by incorporating brand guidelines into all generated content
4. **Enable multi-client scalability** across 12+ client brands without proportional headcount growth
5. **Provide an auditable, explainable recommendation trail** with confidence levels

## Target Users

| Persona | Role | Primary Need |
|---------|------|-------------|
| Account Director | Client relationship owner | Quick, polished pitch with defensible data |
| Media Strategist | Channel planning | Next-best channel and budget allocation |
| Data Analyst | Performance reporting | Self-service campaign analytics |
| Creative Strategist | Messaging and positioning | Brand-aligned creative direction |

## Key Business Questions

1. Which campaigns drove the highest ROI for a given client?
2. What audience segments are underperforming, and what should we do differently?
3. Given seasonality and market events, what is the optimal campaign timing?
4. What creative messaging resonates most with a target segment?
5. How should we allocate budget across channels for maximum reach and conversion?
6. What are competitor trends we should react to?
7. Generate a complete pitch for Client Y focusing on a specific product launch.

## Functional Requirements

### FR1: Client Intelligence Dashboard
- Display KPIs: total campaigns, avg ROAS, total spend, sentiment score
- Visualize channel performance, monthly trends, top campaigns, budget distribution
- Pull from structured analytics and unstructured brand guidelines

### FR2: Campaign Recommendation Engine
- Accept client, product, objective, and budget as inputs
- Analyze historical performance to recommend channels and audience segments
- Ground all recommendations in data with stated confidence levels
- Support iterative refinement via conversational interface

### FR3: What-If Scenario Analysis
- Compare current vs proposed budget allocations side-by-side
- Project revenue, impressions, and conversions per channel
- Calculate deltas and recommend the optimal scenario

### FR4: Pitch Document Generation
- Generate 7-section pitch document (Executive Summary through Expected Impact)
- Apply brand voice, tone, and visual guidelines from brand guidelines database
- Support continuation for long documents that exceed generation limits
- Export as downloadable markdown file

### FR5: Human-in-the-Loop Approval
- Recommendation must be approved before pitch generation
- User can regenerate or modify recommendations
- Explicit "Start Over" workflow to reset state

## Non-Functional Requirements

- **Performance:** Dashboard loads within 5 seconds; agent responses within 2 minutes
- **Data freshness:** Dynamic tables refresh within 1 minute of RAW layer changes
- **Scalability:** Support 10+ concurrent client brands with independent data
- **Security:** All data stays within Snowflake; no external API calls for core functionality

## Data Sources

All data is synthetic, generated to simulate a realistic full-service marketing agency:
- 3 client brands: Nike (Sportswear), Pepsi (Food & Beverage), Samsung (Technology)
- 150 campaigns (2023-2025) with daily metrics across 10 channels
- 2,522 customer profiles across 17 audience segments
- 6,316 customer feedback records with sentiment scores
- 53 market events (holidays, economic, competitor, regulatory, cultural)
- 29 brand guideline sections

## Success Criteria

1. Agent correctly identifies top-performing channels for any client (validated against SQL)
2. Generated pitch includes data-backed projections consistent with historical metrics
3. All 8 data quality assertions pass
4. End-to-end workflow (select client -> recommendation -> pitch) completes within 5 minutes
