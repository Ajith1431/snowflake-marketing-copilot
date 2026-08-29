# Snowflake Marketing Co-Pilot and Pitch Engine - Complete Project Documentation

**Hackathon:** Snowflake CoCo CLI Hackathon (GCC Edition)
**Project:** NovaSpark Agency Marketing Co-Pilot and Pitch Engine
**Account:** WFVAMNP-AP54607
**Team Contact:** Ajithkumar M (ajithkumar.m@wpp.com)

---

## 1. Project Overview

### What It Is
An AI-powered marketing intelligence platform built entirely on Snowflake that helps agency teams:
- Analyze campaign performance across 12 client brands
- Generate data-backed campaign recommendations
- Compare budget allocation scenarios with projected outcomes
- Produce client-ready pitch documents grounded in real data and brand guidelines

### The Business Problem
Marketing agencies waste days manually assembling performance data, audience insights, and competitive intelligence to produce a single client pitch. Analysts query multiple sources, strategists interpret trends, and creatives package the narrative -- all disconnected. This project collapses that into minutes with a unified AI-powered platform.

### How It Works (End-to-End Flow)

```
  [Account Director]
        |
        v
  [Sidebar: Select Client + Product + Budget]
        |
        +---> [Tab 1: Client Intelligence]
        |         |
        |         v
        |     SQL Queries --> Dynamic Tables --> Plotly Charts + KPI Cards
        |
        +---> [Tab 2: Campaign Recommendation]
        |         |
        |         v
        |     Cortex Agent
        |       |         |           |
        |       v         v           v
        |   Campaign   Brand       Market
        |   Analytics  Search      Search
        |   (Analyst)  (Search)   (Search)
        |       |         |           |
        |       v         v           v
        |     Semantic  BRAND_     MARKET_
        |     View      SEARCH     SEARCH
        |       |
        |       v
        |     Dynamic Tables --> RAW Tables
        |         |
        |         v
        |     Structured Recommendation
        |         |
        |         v
        |     [User Approves?]
        |         |
        |        Yes
        |         |
        +---> [Tab 4: Generate Pitch]
        |         |
        |         v
        |     Cortex Agent --> 7-Section Pitch Document --> Download
        |
        +---> [Tab 3: What-If Analysis]
                  |
                  v
              Budget Sliders --> Historical Metrics --> Projected Revenue + Conversions
```

---

## 2. Architecture Layers

### Layer 1: Data Generation (Python)
**File:** `data/generators/generate_all.py` (864 lines, 14 functions)

Generates 11 CSV files with 114,365 total rows of synthetic but realistic marketing data for "NovaSpark Agency" -- a fictional full-service agency managing 12 client brands.

**The 12 Client Brands:**

| Client ID | Brand Name | Industry |
|-----------|-----------|----------|
| C001 | LuminaRetail | Retail |
| C002 | TechVista | Technology |
| C003 | CareWell | Healthcare |
| C004 | FinEdge | Finance |
| C005 | PureLife | CPG |
| C006 | DriveMax | Automotive |
| C007 | Wanderlux | Travel |
| C008 | ConnectSphere | Telecom |
| C009 | FlavorCo | Food and Beverage |
| C010 | UrbanThread | Fashion |
| C011 | MediaPulse | Media and Entertainment |
| C012 | GreenCore | Energy |

**Generator Functions and Their Outputs:**

| Function | Output CSV | Rows | Description |
|----------|-----------|------|-------------|
| `generate_clients()` | clients.csv | 12 | One row per brand |
| `generate_products(clients_df)` | products.csv | 52 | 3-5 industry-specific products per client |
| `generate_channels()` | channels.csv | 10 | Instagram, YouTube, Google Search, Facebook, LinkedIn, TikTok, Email, Programmatic Display, TV, Out-of-Home |
| `generate_audience_segments(clients_df)` | audience_segments.csv | 71 | 5-8 demographic segments per client |
| `generate_customer_profiles(segments_df)` | customer_profiles.csv | 10,000 | Distributed proportionally across segments |
| `generate_campaigns(clients_df, products_df)` | campaigns.csv | 600 | 50 campaigns per client, 2023-2025 |
| `generate_bridge_campaign_segment(...)` | bridge_campaign_segment.csv | 1,789 | 2-4 segments per campaign, allocations sum to 100% |
| `generate_campaign_metrics(campaigns_df, channels_df)` | campaign_metrics.csv | 76,668 | Daily metrics per campaign-channel combo |
| `generate_customer_feedback(...)` | customer_feedback.csv | 25,000 | Sentiment-correlated text and ratings |
| `generate_market_events()` | market_events.csv | 53 | Holidays, economic, competitor, regulatory, cultural |
| `generate_brand_guidelines(clients_df)` | brand_guidelines.csv | 110 | 8-10 guideline sections per client, 100-200 words each |

**Realistic Metric Distributions:**
- CTR: 0.5% to 5.0% (beta distribution)
- ROAS: 1.2 to 7.0 (lognormal distribution)
- Conversion rate: 1% to 8% (beta distribution)
- Spend varies by channel: TV $2K-$10K/day, Social $100-$2K/day, Email $50-$500/day
- Self-consistent: clicks = impressions x CTR, conversions = clicks x conversion_rate, revenue = spend x ROAS

---

### Layer 2: RAW Storage (Snowflake)
**Database:** `MARKETING_COPILOT`
**Schema:** `RAW`
**File:** `sql/ddl/02_tables.sql`

11 tables loaded via `COPY INTO` from internal stage `@MARKETING_STAGE`:

#### Table: RAW_CLIENTS
| Column | Type | Description |
|--------|------|-------------|
| client_id | VARCHAR(10) PK | Unique identifier (C001-C012) |
| client_name | VARCHAR(100) | Brand name |
| industry | VARCHAR(50) | Industry vertical |
| region | VARCHAR(50) | Primary region |
| annual_revenue_usd | NUMBER(15,2) | Client revenue |
| contract_start_date | DATE | When agency contract began |
| primary_contact | VARCHAR(100) | Contact person |
| status | VARCHAR(20) | Account status |

#### Table: RAW_PRODUCTS
| Column | Type | Description |
|--------|------|-------------|
| product_id | VARCHAR(10) PK | Unique identifier (P0001-P0052) |
| client_id | VARCHAR(10) FK | References RAW_CLIENTS |
| product_name | VARCHAR(100) | Industry-specific name |
| category | VARCHAR(50) | Product category |
| launch_date | DATE | When product launched |
| price_tier | VARCHAR(20) | budget / mid / premium |
| description | VARCHAR(1000) | Product description |

#### Table: RAW_CHANNELS
| Column | Type | Description |
|--------|------|-------------|
| channel_id | VARCHAR(10) PK | CH01-CH10 |
| channel_name | VARCHAR(50) | Instagram, YouTube, etc. |
| channel_type | VARCHAR(30) | Social, Video, Search, Direct, Display, Traditional |

#### Table: RAW_AUDIENCE_SEGMENTS
| Column | Type | Description |
|--------|------|-------------|
| segment_id | VARCHAR(10) PK | S0001-S0071 |
| client_id | VARCHAR(10) FK | References RAW_CLIENTS |
| segment_name | VARCHAR(100) | e.g. "Budget Shoppers", "EV Early Adopters" |
| age_band | VARCHAR(20) | e.g. "18-34", "35-54" |
| gender_skew | VARCHAR(30) | Male-leaning, Female-leaning, Balanced |
| income_level | VARCHAR(30) | Low, Medium, High, combinations |
| interests_json | VARCHAR(500) | JSON array of interest keywords |
| estimated_size | INTEGER | Estimated population count |

#### Table: RAW_CUSTOMER_PROFILES
| Column | Type | Description |
|--------|------|-------------|
| customer_id | VARCHAR(12) PK | CU000001-CU010000 |
| segment_id | VARCHAR(10) FK | References RAW_AUDIENCE_SEGMENTS |
| client_id | VARCHAR(10) FK | References RAW_CLIENTS |
| age | INTEGER | Customer age |
| gender | VARCHAR(20) | Male, Female, Non-binary |
| geo_region | VARCHAR(50) | Geographic region |
| lifetime_value_usd | NUMBER(12,2) | Customer LTV |
| acquisition_channel | VARCHAR(30) | How customer was acquired |
| join_date | DATE | When customer was acquired |

#### Table: RAW_CAMPAIGNS
| Column | Type | Description |
|--------|------|-------------|
| campaign_id | VARCHAR(10) PK | CAM0001-CAM0600 |
| client_id | VARCHAR(10) FK | References RAW_CLIENTS |
| product_id | VARCHAR(10) FK | References RAW_PRODUCTS |
| campaign_name | VARCHAR(200) | Full descriptive name |
| campaign_type | VARCHAR(30) | awareness, consideration, conversion, retention |
| objective | VARCHAR(200) | Business objective text |
| start_date | DATE | Campaign start |
| end_date | DATE | Campaign end |
| total_budget_usd | NUMBER(12,2) | Total budget allocated |
| status | VARCHAR(20) | completed, active, planned |

#### Table: RAW_BRIDGE_CAMPAIGN_SEGMENT
| Column | Type | Description |
|--------|------|-------------|
| campaign_id | VARCHAR(10) PK | References RAW_CAMPAIGNS |
| segment_id | VARCHAR(10) PK | References RAW_AUDIENCE_SEGMENTS |
| allocation_pct | NUMBER(5,1) | % of budget for this segment (sums to 100) |

#### Table: RAW_CAMPAIGN_METRICS
| Column | Type | Description |
|--------|------|-------------|
| metric_id | VARCHAR(12) PK | M0000001-M0076668 |
| campaign_id | VARCHAR(10) FK | References RAW_CAMPAIGNS |
| channel_id | VARCHAR(10) FK | References RAW_CHANNELS |
| date | DATE | Daily measurement date |
| impressions | INTEGER | Ad impressions served |
| clicks | INTEGER | Ad clicks |
| conversions | INTEGER | Conversion events |
| spend_usd | NUMBER(12,2) | Daily spend |
| revenue_usd | NUMBER(12,2) | Daily attributed revenue |
| ctr | NUMBER(10,6) | Click-through rate |
| roas | NUMBER(10,4) | Return on ad spend |
| cpc | NUMBER(10,2) | Cost per click |
| conversion_rate | NUMBER(10,6) | Conversion rate |

#### Table: RAW_CUSTOMER_FEEDBACK
| Column | Type | Description |
|--------|------|-------------|
| feedback_id | VARCHAR(12) PK | FB000001-FB025000 |
| customer_id | VARCHAR(12) FK | References RAW_CUSTOMER_PROFILES |
| campaign_id | VARCHAR(10) FK | References RAW_CAMPAIGNS |
| feedback_date | DATE | When feedback was given |
| sentiment_score | NUMBER(6,4) | -1.0 (negative) to 1.0 (positive) |
| rating | INTEGER | 1-5 star rating |
| feedback_text | VARCHAR(500) | Realistic templated feedback |
| feedback_channel | VARCHAR(30) | email, social_media, app_review, etc. |

#### Table: RAW_MARKET_EVENTS
| Column | Type | Description |
|--------|------|-------------|
| event_id | VARCHAR(10) PK | EV001-EV053 |
| event_type | VARCHAR(30) | holiday, economic, competitor_launch, regulatory, cultural |
| event_name | VARCHAR(200) | Event name |
| region | VARCHAR(50) | Affected region |
| start_date | DATE | Event start |
| end_date | DATE | Event end |
| impact_level | VARCHAR(20) | low, medium, high |
| description | VARCHAR(500) | Impact description |
| affected_industries | VARCHAR(500) | Comma-separated industry list |

#### Table: RAW_BRAND_GUIDELINES
| Column | Type | Description |
|--------|------|-------------|
| guideline_id | VARCHAR(10) PK | BG0001-BG0110 |
| client_id | VARCHAR(10) FK | References RAW_CLIENTS |
| section_title | VARCHAR(100) | e.g. "Brand Voice and Tone", "Visual Identity" |
| guideline_text | VARCHAR(5000) | 100-200 word guideline paragraph |
| dos | VARCHAR(500) | JSON array of recommended actions |
| donts | VARCHAR(500) | JSON array of things to avoid |
| tone_keywords | VARCHAR(500) | JSON array of tone descriptors |
| color_palette | VARCHAR(200) | Hex color codes |
| created_date | DATE | When guideline was created |

---

### Layer 3: Analytics (Dynamic Tables)
**Schema:** `ANALYTICS`
**File:** `sql/dynamic_tables/01_analytics_layer.sql`
**Refresh:** TARGET_LAG = 1 minute

10 Dynamic Tables that clean, join, and enrich the RAW data:

| Dynamic Table | Source Tables | Key Enrichments | Rows |
|--------------|--------------|-----------------|------|
| DIM_CLIENT | RAW_CLIENTS | Status uppercased | 12 |
| DIM_PRODUCT | RAW_PRODUCTS + RAW_CLIENTS | Added client_name | 52 |
| DIM_CHANNEL | RAW_CHANNELS | Clean passthrough | 10 |
| DIM_AUDIENCE_SEGMENT | RAW_AUDIENCE_SEGMENTS + RAW_CLIENTS | interests parsed to VARIANT, added client_name | 71 |
| DIM_CUSTOMER_PROFILE | RAW_CUSTOMER_PROFILES + RAW_CLIENTS + RAW_AUDIENCE_SEGMENTS | Added client_name, segment_name | 10,000 |
| DIM_MARKET_EVENT | RAW_MARKET_EVENTS | Added duration_days | 53 |
| FACT_CAMPAIGN | RAW_CAMPAIGNS + RAW_CLIENTS + RAW_PRODUCTS | Added product_name, industry, campaign_duration_days | 600 |
| FACT_CAMPAIGN_METRICS | RAW_CAMPAIGN_METRICS + RAW_CAMPAIGNS + RAW_CLIENTS + RAW_CHANNELS | Recomputed CTR, ROAS, CPC, conversion_rate; added client_name, campaign_name, channel_name | 76,668 |
| FACT_CUSTOMER_FEEDBACK | RAW_CUSTOMER_FEEDBACK + RAW_CAMPAIGNS + RAW_CLIENTS | Added sentiment_category (positive/neutral/negative), client_name | 25,000 |
| FACT_BRAND_GUIDELINES | RAW_BRAND_GUIDELINES + RAW_CLIENTS | Added search_title, search_content for Cortex Search | 110 |

---

### Layer 4: Intelligence (Semantic Schema)

#### 4A. Cortex Analyst -- Semantic View
**Object:** `MARKETING_COPILOT.SEMANTIC.CAMPAIGN_ANALYTICS`
**File:** `semantic_models/campaign_analytics.yaml`

The semantic view defines the business ontology that lets Cortex Analyst translate natural language questions into SQL.

**Logical Tables in the Semantic View:**

```
  FACT_CAMPAIGN_METRICS ---[metrics_to_campaign (CAMPAIGN_ID)]---> FACT_CAMPAIGN
  FACT_CAMPAIGN ---[campaign_to_client (CLIENT_ID)]---> DIM_CLIENT
  FACT_CAMPAIGN ---[campaign_to_product (PRODUCT_ID)]---> DIM_PRODUCT
  FACT_CAMPAIGN_METRICS ---[metrics_to_channel (CHANNEL_ID)]---> DIM_CHANNEL
  BRIDGE_CAMPAIGN_SEGMENT ---[bridge_to_campaign (CAMPAIGN_ID)]---> FACT_CAMPAIGN
  BRIDGE_CAMPAIGN_SEGMENT ---[bridge_to_segment (SEGMENT_ID)]---> DIM_AUDIENCE_SEGMENT
```

**Metrics Defined on FACT_CAMPAIGN_METRICS:**

| Metric Name | Expression | Description |
|------------|-----------|-------------|
| TOTAL_IMPRESSIONS | SUM(IMPRESSIONS) | Total ad impressions |
| TOTAL_CLICKS | SUM(CLICKS) | Total clicks |
| TOTAL_CONVERSIONS | SUM(CONVERSIONS) | Total conversions |
| TOTAL_SPEND | SUM(SPEND_USD) | Total ad spend in USD |
| TOTAL_REVENUE | SUM(REVENUE_USD) | Total revenue in USD |
| AVG_CTR | AVG(CTR) | Average click-through rate |
| AVG_ROAS | AVG(ROAS) | Average return on ad spend |
| AVG_CPC | AVG(CPC) | Average cost per click |
| AVG_CONVERSION_RATE | AVG(CONVERSION_RATE) | Average conversion rate |

**Metrics Defined on FACT_CAMPAIGN:**

| Metric Name | Expression | Description |
|------------|-----------|-------------|
| TOTAL_BUDGET | SUM(TOTAL_BUDGET_USD) | Total campaign budget |
| CAMPAIGN_COUNT | COUNT(CAMPAIGN_ID) | Number of campaigns |

**10 Verified Queries (VQRs):**

| # | Question | What It Queries |
|---|---------|----------------|
| 1 | Which campaigns had the highest ROAS for LuminaRetail? | FACT_CAMPAIGN_METRICS + FACT_CAMPAIGN, filtered by client, grouped by campaign |
| 2 | What is the total spend by channel in 2024? | FACT_CAMPAIGN_METRICS, filtered by year, grouped by channel |
| 3 | Which audience segment has the highest conversion rate? | FACT_CAMPAIGN_METRICS + BRIDGE + DIM_AUDIENCE_SEGMENT |
| 4 | Compare campaign performance across all clients by industry | FACT_CAMPAIGN_METRICS + FACT_CAMPAIGN, grouped by industry + client |
| 5 | What is the monthly revenue trend for TechVista? | FACT_CAMPAIGN_METRICS, filtered by client, grouped by month |
| 6 | Which channel performs best for fashion clients? | FACT_CAMPAIGN_METRICS + FACT_CAMPAIGN, filtered by industry |
| 7 | What is the average CTR by campaign type? | FACT_CAMPAIGN_METRICS, grouped by campaign_type |
| 8 | Show top 5 campaigns by ROI percentage | FACT_CAMPAIGN_METRICS + FACT_CAMPAIGN, computed ROI% |
| 9 | Which market segment has the lowest CPC? | FACT_CAMPAIGN_METRICS + BRIDGE + DIM_AUDIENCE_SEGMENT |
| 10 | What is the total budget allocated vs actual spend by client? | FACT_CAMPAIGN + FACT_CAMPAIGN_METRICS, grouped by client |

#### 4B. Cortex Search Services

**Service 1: BRAND_SEARCH**
- **Object:** `MARKETING_COPILOT.SEMANTIC.BRAND_SEARCH`
- **Indexes:** FACT_BRAND_GUIDELINES.guideline_text (110 documents)
- **Searchable:** guideline_text
- **Filterable attributes:** client_id, client_name, section_title, tone_keywords, dos, donts
- **Purpose:** Retrieve brand voice, tone, visual identity, messaging framework, social media guidelines, crisis protocol, competitive positioning, and legal compliance rules for any client

**Service 2: MARKET_SEARCH**
- **Object:** `MARKETING_COPILOT.SEMANTIC.MARKET_SEARCH`
- **Indexes:** DIM_MARKET_EVENT.description (53 events)
- **Searchable:** description
- **Filterable attributes:** event_type, region, impact_level, affected_industries
- **Purpose:** Find holidays, economic events, competitor launches, regulatory changes, and cultural moments that impact marketing campaigns

#### 4C. Cortex Agent
**Object:** `MARKETING_COPILOT.SEMANTIC.MARKETING_COPILOT`
**File:** `agents/marketing_copilot_agent.yaml`

The agent is the AI orchestrator that ties everything together. It receives natural language requests and decides which tools to call, in what order, to produce a complete response.

**Agent Configuration:**
- Model: auto (Snowflake-selected)
- Budget: 120 seconds, 64,000 tokens
- Display name: "NovaSpark Marketing Co-Pilot"

**4 Tools Bound to the Agent:**

| Tool Name | Type | Resource | What It Does |
|-----------|------|----------|-------------|
| CampaignAnalytics | cortex_analyst_text_to_sql | Semantic View `CAMPAIGN_ANALYTICS` | Translates natural language to SQL against structured campaign data. Warehouse: MARKETING_WH |
| BrandSearch | cortex_search | Search Service `BRAND_SEARCH` | Retrieves brand guideline documents filtered by client and section. Max 5 results |
| MarketSearch | cortex_search | Search Service `MARKET_SEARCH` | Retrieves market event intelligence filtered by type, region, impact. Max 5 results |
| data_to_chart | data_to_chart | (built-in) | Generates chart visualizations from data returned by other tools |

**Agent Orchestration Logic:**
1. Performance questions (spend, ROAS, CTR) --> CampaignAnalytics
2. Brand questions (tone, guidelines, creative) --> BrandSearch
3. Market questions (events, seasonality, competition) --> MarketSearch
4. Campaign pitches --> CampaignAnalytics first, then BrandSearch, then MarketSearch, then synthesize all three
5. Data visualization --> data_to_chart

**Agent System Prompt Rules:**
- Always ground in data, never fabricate metrics
- State confidence level (HIGH/MEDIUM/LOW)
- Apply brand guidelines to all creative suggestions
- Ask clarifying questions when client/product is ambiguous

---

### Layer 5: CoCo Skills (4 Skills)
**Directory:** `.snowflake/cortex/skills/`

Skills are structured instruction sets that CoCo Desktop uses for specialized workflows.

#### Skill 1: client-intelligence
**File:** `.snowflake/cortex/skills/client-intelligence/SKILL.md`

| Step | Action | Data Source |
|------|--------|-------------|
| 1 | Resolve client identity | DIM_CLIENT |
| 2 | Campaign portfolio summary | FACT_CAMPAIGN |
| 3 | Performance snapshot (ROAS, spend, revenue, CTR) | FACT_CAMPAIGN_METRICS |
| 4 | Channel performance ranking | FACT_CAMPAIGN_METRICS grouped by channel |
| 5 | Audience sentiment analysis | FACT_CUSTOMER_FEEDBACK |
| 6 | Brand guidelines retrieval | BRAND_SEARCH (Cortex Search) |
| 7 | Compile structured briefing | All above combined |

**Output:** A structured markdown briefing with Profile, Campaign Portfolio, Performance Snapshot, Channel Ranking, Audience Sentiment, and Brand Personality sections.

#### Skill 2: campaign-analysis
**File:** `.snowflake/cortex/skills/campaign-analysis/SKILL.md`

| Step | Action | Data Source |
|------|--------|-------------|
| 1 | Resolve client, apply date/type filters | DIM_CLIENT |
| 2 | Channel performance ranking | FACT_CAMPAIGN_METRICS by channel |
| 3 | Campaign type breakdown | FACT_CAMPAIGN_METRICS by campaign_type |
| 4 | Top 3 and bottom 3 campaigns by ROAS | FACT_CAMPAIGN_METRICS |
| 5 | Audience segment performance | BRIDGE + DIM_AUDIENCE_SEGMENT + FACT_CAMPAIGN_METRICS |
| 6 | Monthly seasonality patterns | FACT_CAMPAIGN_METRICS by month |
| 7 | Compile analysis with confidence level | All above |

**Output:** Channel ranking table, top/bottom campaigns, segment insights, seasonal patterns, and confidence level based on sample size.

#### Skill 3: pitch-generator
**File:** `.snowflake/cortex/skills/pitch-generator/SKILL.md`

**Inputs:** client_name, product_name, campaign_objective, channels, budget, segments, performance_context, brand_guidelines

| Step | Action |
|------|--------|
| 1 | Gather missing context (query if not provided) |
| 2 | Select channels (top by ROAS or industry defaults) |
| 3 | Allocate budget by ROAS weights |
| 4 | Project KPIs per channel |
| 5 | Generate 7-section pitch document |
| 6 | Quality checks (ROAS 1-10x, brand compliance, budget sums) |

**Output (7 Sections):**
1. Executive Summary
2. Client and Product Overview
3. Campaign Objective and KPIs
4. Target Audience Analysis
5. Recommended Channel Strategy with budget split
6. Creative Direction (based on brand guidelines)
7. Expected Impact with projected metrics

#### Skill 4: what-if-analysis
**File:** `.snowflake/cortex/skills/what-if-analysis/SKILL.md`

**Inputs:** client_name, current_allocation (channel->budget), proposed_allocation (channel->budget)

| Step | Action |
|------|--------|
| 1 | Resolve client |
| 2 | Get historical channel performance (ROAS, CTR, conv_rate, CPC) |
| 3 | Project metrics for current scenario |
| 4 | Project metrics for proposed scenario |
| 5 | Compute deltas (revenue, impressions, conversions) |
| 6 | Generate comparison report with recommendation |

**Output:** Side-by-side comparison table, channel breakdown, recommendation, and confidence assessment.

---

### Layer 6: Streamlit Dashboard
**Object:** `MARKETING_COPILOT.SEMANTIC.MARKETING_COPILOT_APP`
**File:** `streamlit/streamlit_app.py` (480+ lines, 14 functions)
**Runtime:** Warehouse (Python 3.11)
**Dependencies:** plotly (via environment.yml)

#### Sidebar Controls
- Client selector dropdown (12 brands from DIM_CLIENT)
- Product selector (filtered by selected client from DIM_PRODUCT)
- Campaign Objective: Brand Awareness, Lead Generation, Sales Conversion, Customer Retention
- Budget input (USD number field)
- "Analyze and Recommend" button

#### Tab 1: Client Intelligence (Pure SQL, No Agent)
| Component | Data Source | Query Function |
|-----------|-----------|----------------|
| KPI: Total Campaigns | FACT_CAMPAIGN | `load_client_kpis()` |
| KPI: Avg ROAS | FACT_CAMPAIGN_METRICS | `load_client_kpis()` |
| KPI: Total Spend | FACT_CAMPAIGN_METRICS | `load_client_kpis()` |
| KPI: Avg Sentiment | FACT_CUSTOMER_FEEDBACK | `load_sentiment()` |
| Bar Chart: ROAS by Channel | FACT_CAMPAIGN_METRICS | `load_channel_roas()` |
| Line Chart: Monthly Revenue | FACT_CAMPAIGN_METRICS | `load_monthly_revenue()` |
| Horizontal Bar: Top 5 Campaigns by ROI | FACT_CAMPAIGN_METRICS | `load_top_campaigns()` |
| Pie Chart: Budget by Campaign Type | FACT_CAMPAIGN | `load_budget_by_type()` |

#### Tab 2: Campaign Recommendation (Agent-Powered)
1. User clicks "Analyze and Recommend"
2. Builds prompt: client + product + objective + budget
3. Calls `call_agent()` which invokes `SNOWFLAKE.CORTEX.DATA_AGENT_RUN`
4. Agent orchestrates: CampaignAnalytics --> BrandSearch --> MarketSearch --> synthesize
5. Displays structured recommendation in markdown
6. If response is incomplete (time limit hit), shows "Continue generating" button
7. "Approve Recommendation" button gates Tab 4

#### Tab 3: What-If Analysis (Pure Computation, No Agent)
1. Loads historical channel metrics via `load_channel_history()`
2. Shows top 5 channels with equal-split baseline
3. Sliders for proposed allocation percentages
4. Real-time projection: revenue = budget x historical_ROAS, clicks = budget / CPC, conversions = clicks x conv_rate
5. Grouped bar chart: current vs proposed revenue per channel
6. Delta metrics: projected revenue change, conversion change

#### Tab 4: Generate Pitch (Agent-Powered)
1. Only available after recommendation is approved (human-in-the-loop)
2. Calls agent with 7-section pitch prompt
3. Displays response in expandable section panels
4. Continuation support for incomplete responses
5. Download button exports full pitch as .md file
6. "Start Over" resets all session state

#### Key Technical Details
- All SQL queries use `@st.cache_data(ttl=300)` for 5-minute caching
- Agent calls use `$$` dollar-quoting to prevent SQL injection from special characters in prompts
- Incomplete responses detected by scanning for "time limit", "may be incomplete", etc.
- Session state manages the recommendation --> approval --> pitch workflow

---

## 3. Data Flow: How Everything Connects

```
Data Generation         RAW Schema              ANALYTICS Schema         SEMANTIC Schema
================        ==========              ================         ===============

generate_all.py  --->  @MARKETING_STAGE  --->  11 RAW Tables  --->  10 Dynamic Tables
  (Python)              (Internal Stage)        (COPY INTO)          (TARGET_LAG 1min)
                                                                           |
                                                          +----------------+----------------+
                                                          |                |                |
                                                    Semantic View    BRAND_SEARCH     MARKET_SEARCH
                                                   (CAMPAIGN_        (Cortex          (Cortex
                                                    ANALYTICS)        Search)           Search)
                                                          |                |                |
                                                          +--------+-------+--------+-------+
                                                                   |
                                                             Cortex Agent
                                                          (MARKETING_COPILOT)
                                                                   |
                                                            Streamlit App
                                                       (MARKETING_COPILOT_APP)
```

**Foreign Key Chain:**
```
CLIENT_ID:    DIM_CLIENT --> FACT_CAMPAIGN --> FACT_CAMPAIGN_METRICS
PRODUCT_ID:   DIM_PRODUCT --> FACT_CAMPAIGN
CHANNEL_ID:   DIM_CHANNEL --> FACT_CAMPAIGN_METRICS
SEGMENT_ID:   DIM_AUDIENCE_SEGMENT --> BRIDGE_CAMPAIGN_SEGMENT --> FACT_CAMPAIGN
CAMPAIGN_ID:  FACT_CAMPAIGN --> FACT_CAMPAIGN_METRICS
              FACT_CAMPAIGN --> BRIDGE_CAMPAIGN_SEGMENT
              FACT_CAMPAIGN --> FACT_CUSTOMER_FEEDBACK
CUSTOMER_ID:  DIM_CUSTOMER_PROFILE --> FACT_CUSTOMER_FEEDBACK
```

---

## 4. Snowflake Objects Inventory

| Object Type | Name | Schema | Purpose |
|------------|------|--------|---------|
| Database | MARKETING_COPILOT | - | Project database |
| Schema | RAW | - | Source data tables |
| Schema | STAGING | - | Reserved for future ETL |
| Schema | ANALYTICS | - | Dynamic tables |
| Schema | SEMANTIC | - | AI services |
| Warehouse | MARKETING_WH | - | XS, auto-suspend 60s |
| Stage | MARKETING_STAGE | RAW | CSV file storage |
| Stage | STREAMLIT_STAGE | SEMANTIC | Streamlit app files |
| Stage | SEMANTIC_STAGE | SEMANTIC | Semantic model YAML |
| Tables (11) | RAW_CLIENTS, RAW_PRODUCTS, RAW_CHANNELS, RAW_AUDIENCE_SEGMENTS, RAW_CUSTOMER_PROFILES, RAW_CAMPAIGNS, RAW_BRIDGE_CAMPAIGN_SEGMENT, RAW_CAMPAIGN_METRICS, RAW_CUSTOMER_FEEDBACK, RAW_MARKET_EVENTS, RAW_BRAND_GUIDELINES | RAW | Source data |
| Dynamic Tables (10) | DIM_CLIENT, DIM_PRODUCT, DIM_CHANNEL, DIM_AUDIENCE_SEGMENT, DIM_CUSTOMER_PROFILE, DIM_MARKET_EVENT, FACT_CAMPAIGN, FACT_CAMPAIGN_METRICS, FACT_CUSTOMER_FEEDBACK, FACT_BRAND_GUIDELINES | ANALYTICS | Enriched analytics |
| Semantic View | CAMPAIGN_ANALYTICS | SEMANTIC | Cortex Analyst model |
| Search Service | BRAND_SEARCH | SEMANTIC | Brand guidelines search |
| Search Service | MARKET_SEARCH | SEMANTIC | Market events search |
| Agent | MARKETING_COPILOT | SEMANTIC | AI orchestrator |
| Streamlit | MARKETING_COPILOT_APP | SEMANTIC | Dashboard UI |

---

## 5. Validation and Quality

8 automated assertions in `tests/test_validation.sql`, all passing:

| Test | Assertion | Result |
|------|----------|--------|
| T1 | No NULL client_ids in any fact table | PASS |
| T2 | All ROAS values greater than 0 | PASS |
| T3 | All spend values greater than 0 | PASS |
| T4 | Campaign end_date after start_date | PASS |
| T5 | Sentiment scores within -1.0 to 1.0 | PASS |
| T6 | Allocation percentages sum to 100 per campaign | PASS |
| T7 | Cortex Search BRAND_SEARCH returns results | PASS |
| T8 | Semantic View CAMPAIGN_ANALYTICS is queryable | PASS |

---

## 6. Project File Structure

```
SnowflakeHackathon/
  README.md                                    # Project overview
  .gitignore                                   # Excludes CSVs, secrets, caches
  data/
    generators/generate_all.py                 # Synthetic data generator (864 lines)
    samples/*.csv                              # 11 generated CSV files (gitignored)
  sql/
    ddl/01_setup.sql                           # Database, schemas, warehouse
    ddl/02_tables.sql                          # 11 RAW table definitions
    dml/01_load_data.sql                       # COPY INTO statements
    dml/load_data.py                           # Python upload script
    dynamic_tables/01_analytics_layer.sql      # 10 dynamic table definitions
  semantic_models/
    campaign_analytics.yaml                    # Cortex Analyst semantic view YAML
    campaign_analytics_proto.json              # Generation prototype
    upload_yaml.py                             # Upload helper
  agents/
    marketing_copilot_agent.yaml               # Cortex Agent definition
  streamlit/
    streamlit_app.py                           # 4-tab Streamlit dashboard (480+ lines)
    environment.yml                            # SiS dependencies (plotly)
    upload_streamlit.py                        # Upload helper
  .snowflake/cortex/skills/
    client-intelligence/SKILL.md               # Client briefing skill
    campaign-analysis/SKILL.md                 # Campaign deep-dive skill
    pitch-generator/SKILL.md                   # Pitch document skill
    what-if-analysis/SKILL.md                  # Scenario comparison skill
  tests/
    test_validation.sql                        # 8 data quality assertions
  docs/
    requirements/business-requirements.md      # Business requirements
    architecture/solution-architecture.md      # Technical architecture
    marketing_copilot_complete_documentation.md # This document
```

---

## 7. Demo Walkthrough

**Scenario A -- Client Intelligence:**
Select "LuminaRetail" in the sidebar. Tab 1 instantly shows 50 campaigns, 2.36x avg ROAS, $5.36M total spend, and 0.22 avg sentiment. The ROAS-by-channel chart reveals YouTube and Instagram as top performers. The monthly trend shows seasonal peaks around holidays.

**Scenario B -- Campaign Recommendation:**
Select "UrbanThread", product "UT-EcoThread", objective "Brand Awareness", budget $300,000. Click "Analyze and Recommend". The agent queries UrbanThread's historical data, retrieves fashion brand guidelines (bold, elegant, expressive), finds relevant market events (sustainability moments, fashion weeks), and produces a structured recommendation: Instagram 30%, TikTok 25%, YouTube 20%, Google Search 15%, Email 10% -- with projected 2.5x ROAS and 15K conversions.

**Scenario C -- What-If Analysis:**
On Tab 3, shift 15% from TV to TikTok using the sliders. The dashboard instantly shows projected revenue increases by $45K with 2,300 additional conversions, recommending the proposed allocation based on TikTok's higher historical ROAS for this client.

**Scenario D -- Pitch Generation:**
After approving the recommendation, go to Tab 4 and click "Generate Full Pitch". The agent produces a 7-section pitch document with Executive Summary, audience analysis, channel strategy with budget table, creative direction aligned to brand tone, and projected impact metrics. Download as markdown for presentation.

---

## 8. Tech Stack Summary

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Data Platform | Snowflake | All storage, compute, and AI services |
| AI Orchestration | Cortex Agent | Multi-tool AI orchestrator |
| Structured Analytics | Cortex Analyst (Semantic View) | Natural language to SQL |
| Unstructured Search | Cortex Search Service (x2) | Brand guidelines and market events retrieval |
| Dashboard | Streamlit in Snowflake | 4-tab marketing copilot UI |
| Data Generation | Python (Faker, NumPy, Pandas) | 114K+ rows of synthetic data |
| Skills | CoCo CLI Skills (x4) | Specialized marketing workflows |
| Visualization | Plotly | Dark-themed interactive charts |
| Data Pipeline | Dynamic Tables | Auto-refreshing analytics layer |

---

Built with Snowflake Cortex, CoCo CLI, and Streamlit in Snowflake.
Generated with Cortex Code (https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code)
