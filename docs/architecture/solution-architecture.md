# Solution Architecture: Marketing Co-Pilot & Pitch Engine

## Overview

The Marketing Co-Pilot is a multi-layer Snowflake-native application that combines structured analytics (Cortex Analyst), unstructured search (Cortex Search), and AI orchestration (Cortex Agent) to power a Streamlit dashboard for marketing agency teams.

## Architecture Layers

### Layer 1: Data Generation (Python)
- `data/generators/generate_all.py` produces 11 CSV files with 114K+ rows
- Deterministic seed (42) for reproducible synthetic data
- Realistic metric distributions: CTR (0.5-5%), ROAS (1.2-7.0), conversion rate (1-8%)
- Referential integrity enforced across all tables

### Layer 2: Raw Storage (Snowflake RAW Schema)
- 11 tables loaded via COPY INTO from internal stage `@MARKETING_STAGE`
- Preserves source data as-is with appropriate Snowflake types
- No transformations at this layer

### Layer 3: Analytics (Dynamic Tables)
- 10 dynamic tables in ANALYTICS schema with TARGET_LAG = 1 minute
- Dimension tables: DIM_CLIENT, DIM_PRODUCT, DIM_CHANNEL, DIM_AUDIENCE_SEGMENT, DIM_CUSTOMER_PROFILE, DIM_MARKET_EVENT
- Fact tables: FACT_CAMPAIGN, FACT_CAMPAIGN_METRICS, FACT_CUSTOMER_FEEDBACK, FACT_BRAND_GUIDELINES
- Enrichments: computed metrics (CTR, ROAS, CPC, conversion_rate), sentiment categories, search-optimized text fields

### Layer 4: Intelligence (SEMANTIC Schema)

#### Cortex Analyst (Semantic View)
- `CAMPAIGN_ANALYTICS` semantic view with 8 logical tables
- 9 metrics: TOTAL_IMPRESSIONS, TOTAL_CLICKS, TOTAL_CONVERSIONS, TOTAL_SPEND, TOTAL_REVENUE, AVG_CTR, AVG_ROAS, AVG_CPC, AVG_CONVERSION_RATE
- 6 relationships connecting fact tables to dimension tables
- 10 verified queries covering common analytical questions
- Deployed via `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML`

#### Cortex Search Services
- `BRAND_SEARCH`: Indexes brand guideline text (110 documents) with filterable attributes (client_name, section_title)
- `MARKET_SEARCH`: Indexes market event descriptions (53 events) with filterable attributes (event_type, region, impact_level)

#### Cortex Agent
- `MARKETING_COPILOT` agent with 4 tools:
  - `CampaignAnalytics` (cortex_analyst_text_to_sql) -- structured data queries
  - `BrandSearch` (cortex_search) -- brand guideline retrieval
  - `MarketSearch` (cortex_search) -- market event retrieval
  - `data_to_chart` -- visualization generation
- Budget: 120 seconds, 64K tokens
- Orchestration instructions guide tool selection based on question type

### Layer 5: Presentation (Streamlit in Snowflake)

#### Tab 1: Client Intelligence
- KPI cards populated from FACT_CAMPAIGN_METRICS and FACT_CUSTOMER_FEEDBACK
- Plotly charts: ROAS by channel (bar), monthly revenue (line), top campaigns (horizontal bar), budget by type (pie)
- All queries cached with 300-second TTL

#### Tab 2: Campaign Recommendation
- Calls Cortex Agent with client/product/objective/budget context
- Displays structured recommendation with approve/regenerate workflow
- Continuation support for incomplete responses

#### Tab 3: What-If Analysis
- Pure computation layer using historical channel metrics
- Slider-based budget allocation with real-time projected metric recalculation
- Grouped bar chart comparing current vs proposed scenarios

#### Tab 4: Generate Pitch
- Available after recommendation approval (human-in-the-loop gate)
- Calls Cortex Agent for 7-section pitch document
- Expandable section panels, downloadable as markdown
- Continuation support for long documents

## Data Flow

```
CSV Files --> @MARKETING_STAGE --> RAW Tables --> Dynamic Tables (ANALYTICS)
                                                        |
                                                        v
                                               Semantic View (SEMANTIC)
                                               Cortex Search Services
                                                        |
                                                        v
                                                  Cortex Agent
                                                        |
                                                        v
                                                Streamlit Dashboard
```

## Security Model

- All data stays within Snowflake (no external API calls for core functionality)
- Snowflake RBAC controls access to database objects
- Streamlit app uses `get_active_session()` (embedded identity in SiS)
- Agent calls use dollar-quoted SQL strings to prevent injection

## Scalability Considerations

- Dynamic tables auto-refresh with 1-minute lag
- Warehouse auto-suspend at 60 seconds minimizes idle costs
- Cortex Search services handle real-time indexing
- Semantic view supports ad-hoc analytical queries without pre-aggregation
- Agent budget is configurable (currently 120s/64K tokens)
