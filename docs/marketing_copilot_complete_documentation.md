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
- Pull live internet intelligence (Google Trends, news, web research) for market events
- Generate event-specific marketing strategies with competitive analysis

### The Business Problem
Marketing agencies waste days manually assembling performance data, audience insights, and competitive intelligence to produce a single client pitch. Analysts query multiple sources, strategists interpret trends, and creatives package the narrative -- all disconnected. This project collapses that into minutes with a unified AI-powered platform that combines internal campaign data with live market intelligence.

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
        |     Marketing Co-Pilot Agent (auto-continue up to 3 rounds)
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
        |     Structured Recommendation --> Download as styled HTML
        |         |
        |        Yes (Approve)
        |         |
        +---> [Tab 4: Generate Pitch]
        |         |
        |         v
        |     Marketing Co-Pilot Agent --> 7-Section Pitch --> Download as styled HTML
        |
        +---> [Tab 3: What-If Analysis]
        |         |
        |         v
        |     Budget Sliders --> Historical Metrics --> Projected Revenue + Conversions
        |         |
        |         v
        |     Scenario Comparison Chart --> Download as styled HTML
        |
        +---> [Tab 5: Event Intelligence]  *** NEW ***
                  |
                  v
              Internet Intelligence Agent (auto-continue)
                |         |           |
                v         v           v
            Web Search  Event News  Campaign
            (Live)      Search      Benchmarks
                |
                v
              Trend/News/Competitor Data from Snowflake Tables
                |
                v
              Strategy Synthesis Agent (auto-continue)
                |         |           |           |
                v         v           v           v
            Campaign   Brand       Event News  Web Search
            Analytics  Search      Search      (Live)
                |
                v
              9-Section Event Strategy --> Download as styled HTML
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
**Files:** `sql/ddl/02_tables.sql`, `sql/ddl/03_event_intelligence_tables.sql`

16 tables total (11 base + 5 event intelligence), loaded via `COPY INTO` from internal stages:

#### Base Tables (11)

| Table | Primary Key | Rows | Description |
|-------|------------|------|-------------|
| RAW_CLIENTS | client_id | 12 | Client brands |
| RAW_PRODUCTS | product_id | 52 | Products per client |
| RAW_CHANNELS | channel_id | 10 | Marketing channels |
| RAW_AUDIENCE_SEGMENTS | segment_id | 71 | Audience segments |
| RAW_CUSTOMER_PROFILES | customer_id | 10,000 | Customer demographics |
| RAW_CAMPAIGNS | campaign_id | 600 | Campaigns 2023-2025 |
| RAW_BRIDGE_CAMPAIGN_SEGMENT | campaign_id+segment_id | 1,789 | Campaign-segment allocation |
| RAW_CAMPAIGN_METRICS | metric_id | 76,668 | Daily channel metrics |
| RAW_CUSTOMER_FEEDBACK | feedback_id | 25,000 | Customer feedback with sentiment |
| RAW_MARKET_EVENTS | event_id | 53 | Market events calendar |
| RAW_BRAND_GUIDELINES | guideline_id | 110 | Brand guidelines per section |

#### Event Intelligence Tables (5) -- NEW

| Table | Description |
|-------|-------------|
| RAW_INTELLIGENCE_RUNS | Tracks each intelligence run (run_id, client, event, timestamps, confidence) |
| RAW_EVENT_TRENDS | Google Trends data (keyword, date, interest_score, is_peak, rising_queries) |
| RAW_NEWS_ARTICLES | News articles from Event Registry + Google News RSS (title, source, sentiment, URL) |
| RAW_WEB_INTELLIGENCE | Cortex Complete web research queries and responses |
| RAW_COMPETITOR_INTEL | Competitor analysis (name, mentions, sentiment, platforms, themes, threat_level) |

---

### Layer 3: Analytics (Dynamic Tables)
**Schema:** `ANALYTICS`
**Files:** `sql/dynamic_tables/01_analytics_layer.sql`, `sql/dynamic_tables/02_event_analytics.sql`
**Refresh:** TARGET_LAG = 1 minute

14 Dynamic Tables total (10 base + 4 event analytics):

#### Base Dynamic Tables (10)

| Dynamic Table | Source Tables | Key Enrichments |
|--------------|--------------|-----------------|
| DIM_CLIENT | RAW_CLIENTS | Status uppercased |
| DIM_PRODUCT | RAW_PRODUCTS + RAW_CLIENTS | Added client_name |
| DIM_CHANNEL | RAW_CHANNELS | Clean passthrough |
| DIM_AUDIENCE_SEGMENT | RAW_AUDIENCE_SEGMENTS + RAW_CLIENTS | interests parsed to VARIANT, added client_name |
| DIM_CUSTOMER_PROFILE | RAW_CUSTOMER_PROFILES + RAW_CLIENTS + RAW_AUDIENCE_SEGMENTS | Added client_name, segment_name |
| DIM_MARKET_EVENT | RAW_MARKET_EVENTS | Added duration_days |
| FACT_CAMPAIGN | RAW_CAMPAIGNS + RAW_CLIENTS + RAW_PRODUCTS | Added product_name, industry, campaign_duration_days |
| FACT_CAMPAIGN_METRICS | RAW_CAMPAIGN_METRICS + RAW_CAMPAIGNS + RAW_CLIENTS + RAW_CHANNELS | Recomputed CTR, ROAS, CPC, conversion_rate; added client_name, campaign_name, channel_name |
| FACT_CUSTOMER_FEEDBACK | RAW_CUSTOMER_FEEDBACK + RAW_CAMPAIGNS + RAW_CLIENTS | Added sentiment_category, client_name |
| FACT_BRAND_GUIDELINES | RAW_BRAND_GUIDELINES + RAW_CLIENTS | Added search_title, search_content for Cortex Search |

#### Event Analytics Dynamic Tables (4) -- NEW

| Dynamic Table | Source | Purpose |
|--------------|--------|---------|
| DIM_EVENT_TRENDS | RAW_EVENT_TRENDS + RAW_INTELLIGENCE_RUNS | Enriched trend data with event context, peak detection |
| DIM_NEWS_SENTIMENT | RAW_NEWS_ARTICLES + RAW_INTELLIGENCE_RUNS | News with sentiment labels, relevance scores |
| DIM_COMPETITOR_PRESENCE | RAW_COMPETITOR_INTEL + RAW_INTELLIGENCE_RUNS | Competitor mentions, threat levels, market share indicators |
| FACT_INTELLIGENCE_SUMMARY | RAW_INTELLIGENCE_RUNS | Run-level summary with confidence scores |

---

### Layer 4: Intelligence (Semantic Schema)

#### 4A. Cortex Analyst -- Semantic View
**Object:** `MARKETING_COPILOT.SEMANTIC.CAMPAIGN_ANALYTICS`
**File:** `semantic_models/campaign_analytics.yaml`

The semantic view defines the business ontology that lets Cortex Analyst translate natural language questions into SQL.

**7 Logical Tables:**
```
FACT_CAMPAIGN_METRICS ---[CAMPAIGN_ID]---> FACT_CAMPAIGN
FACT_CAMPAIGN ---[CLIENT_ID]---> DIM_CLIENT
FACT_CAMPAIGN ---[PRODUCT_ID]---> DIM_PRODUCT
FACT_CAMPAIGN_METRICS ---[CHANNEL_ID]---> DIM_CHANNEL
BRIDGE_CAMPAIGN_SEGMENT ---[CAMPAIGN_ID]---> FACT_CAMPAIGN
BRIDGE_CAMPAIGN_SEGMENT ---[SEGMENT_ID]---> DIM_AUDIENCE_SEGMENT
```

**11 Metrics:**

| Metric | Expression | Table |
|--------|-----------|-------|
| TOTAL_IMPRESSIONS | SUM(IMPRESSIONS) | FACT_CAMPAIGN_METRICS |
| TOTAL_CLICKS | SUM(CLICKS) | FACT_CAMPAIGN_METRICS |
| TOTAL_CONVERSIONS | SUM(CONVERSIONS) | FACT_CAMPAIGN_METRICS |
| TOTAL_SPEND | SUM(SPEND_USD) | FACT_CAMPAIGN_METRICS |
| TOTAL_REVENUE | SUM(REVENUE_USD) | FACT_CAMPAIGN_METRICS |
| AVG_CTR | AVG(CTR) | FACT_CAMPAIGN_METRICS |
| AVG_ROAS | AVG(ROAS) | FACT_CAMPAIGN_METRICS |
| AVG_CPC | AVG(CPC) | FACT_CAMPAIGN_METRICS |
| AVG_CONVERSION_RATE | AVG(CONVERSION_RATE) | FACT_CAMPAIGN_METRICS |
| TOTAL_BUDGET | SUM(TOTAL_BUDGET_USD) | FACT_CAMPAIGN |
| CAMPAIGN_COUNT | COUNT(CAMPAIGN_ID) | FACT_CAMPAIGN |

**10 Verified Queries (VQRs):**

| # | Question | Tables Involved |
|---|---------|----------------|
| 1 | Highest ROAS campaigns for LuminaRetail | METRICS + CAMPAIGN, filtered by client |
| 2 | Total spend by channel in 2024 | METRICS, filtered by year |
| 3 | Highest conversion rate audience segment | METRICS + BRIDGE + SEGMENT |
| 4 | Performance by industry across all clients | METRICS + CAMPAIGN, grouped by industry |
| 5 | Monthly revenue trend for TechVista | METRICS, filtered by client, grouped by month |
| 6 | Best channel for fashion clients | METRICS + CAMPAIGN, filtered by industry |
| 7 | Average CTR by campaign type | METRICS, grouped by campaign_type |
| 8 | Top 5 campaigns by ROI % | METRICS + CAMPAIGN, computed ROI |
| 9 | Lowest CPC market segment | METRICS + BRIDGE + SEGMENT |
| 10 | Budget allocated vs actual spend by client | CAMPAIGN + METRICS, grouped by client |

#### 4B. Cortex Search Services (3)

| Service | Object | Source | Documents | Purpose |
|---------|--------|--------|-----------|---------|
| BRAND_SEARCH | `SEMANTIC.BRAND_SEARCH` | FACT_BRAND_GUIDELINES | 110 | Brand guidelines (voice, tone, visual identity, messaging) |
| MARKET_SEARCH | `SEMANTIC.MARKET_SEARCH` | DIM_MARKET_EVENT | 53 | Market events (holidays, economic, competitor, cultural) |
| EVENT_NEWS_SEARCH | `SEMANTIC.EVENT_NEWS_SEARCH` | RAW_NEWS_ARTICLES | varies | News articles from intelligence runs (NEW) |

#### 4C. Cortex Agents (3)

**Agent 1: MARKETING_COPILOT** (Primary)
- **Object:** `SEMANTIC.MARKETING_COPILOT`
- **Model:** auto
- **Budget:** 300 seconds, 128,000 tokens
- **Tools:** CampaignAnalytics (Analyst), BrandSearch (Search), MarketSearch (Search), data_to_chart
- **Role:** Answers campaign questions, generates recommendations and pitches using all internal data

**Agent 2: INTERNET_INTELLIGENCE_AGENT** (NEW)
- **Object:** `SEMANTIC.INTERNET_INTELLIGENCE_AGENT`
- **Model:** auto
- **Budget:** 300 seconds, 128,000 tokens
- **Tools:** web_search (live internet), EventNewsSearch (Search), CampaignBenchmarks (Analyst), data_to_chart
- **Role:** Researches market events using live web data, produces structured intelligence reports with trend analysis, news sentiment, competitor activity, and confidence ratings

**Agent 3: STRATEGY_SYNTHESIS_AGENT** (NEW)
- **Object:** `SEMANTIC.STRATEGY_SYNTHESIS_AGENT`
- **Model:** auto
- **Budget:** 300 seconds, 128,000 tokens
- **Tools:** CampaignAnalytics (Analyst), BrandSearch (Search), EventNewsSearch (Search), web_search (live), data_to_chart
- **Role:** Combines internal campaign data with live market intelligence to produce 9-section event marketing strategies with channel allocation, creative direction, timeline, and competitive positioning

**Agent Orchestration Pattern:**
```
User Question
     |
     v
[Marketing Co-Pilot]          [Internet Intelligence]       [Strategy Synthesis]
     |                              |                              |
     v                              v                              v
1. CampaignAnalytics         1. web_search (live)          1. CampaignAnalytics
2. BrandSearch               2. EventNewsSearch            2. BrandSearch
3. MarketSearch              3. CampaignBenchmarks         3. EventNewsSearch
4. data_to_chart             4. data_to_chart              4. web_search (live)
     |                              |                      5. data_to_chart
     v                              v                              |
Recommendation/Pitch         Intelligence Report                   v
                                                          9-Section Strategy
```

---

### Layer 5: Event Intelligence Pipeline (NEW)
**Directory:** `src/intelligence/`

A Python-based pipeline that pulls live internet data and loads it into Snowflake:

| Module | Lines | Function | Description |
|--------|-------|----------|-------------|
| `intelligence_orchestrator.py` | 177 | `run_full_intelligence()` | Orchestrates all 3 pullers, aggregates results |
| `snowflake_loader.py` | 181 | `load_intelligence_run()` | Loads results into 5 RAW tables |
| `google_trends_puller.py` | 123 | `get_trend_data()` | Pulls Google Trends via pytrends |
| `news_puller.py` | ~200 | `get_news()` | Event Registry (primary) + Google News RSS (fallback) |
| `web_intelligence_puller.py` | 228 | `get_web_intelligence()` | Cortex Complete (claude-sonnet-4-6) for web research |
| `config.py` | 3 | - | API keys for Event Registry |

**Data Flow:**
```
Event Registry API  --->  news_puller.py     --->  RAW_NEWS_ARTICLES
Google News RSS     --->  (fallback)         --->
Google Trends API   --->  google_trends.py   --->  RAW_EVENT_TRENDS
Cortex Complete     --->  web_intel.py       --->  RAW_WEB_INTELLIGENCE
                                             --->  RAW_COMPETITOR_INTEL
                                             --->  RAW_INTELLIGENCE_RUNS
```

---

### Layer 6: CoCo Skills (7 Skills)
**Directory:** `.snowflake/cortex/skills/`

Skills are structured instruction sets that CoCo Desktop uses for specialized workflows.

#### Original Skills (4)

| Skill | File | Steps | Output |
|-------|------|-------|--------|
| client-intelligence | `client-intelligence/SKILL.md` | 7 steps: resolve client, campaign portfolio, performance snapshot, channel ranking, sentiment, brand guidelines, compile briefing | Structured markdown briefing |
| campaign-analysis | `campaign-analysis/SKILL.md` | 7 steps: resolve client, channel ranking, type breakdown, top/bottom campaigns, segment performance, seasonality, compile with confidence | Channel tables, campaign rankings, seasonal patterns |
| pitch-generator | `pitch-generator/SKILL.md` | 6 steps: gather context, select channels, allocate budget, project KPIs, generate 7-section document, quality checks | 7-section pitch document |
| what-if-analysis | `what-if-analysis/SKILL.md` | 6 steps: resolve client, historical metrics, current projection, proposed projection, compute deltas, comparison report | Side-by-side scenario comparison |

#### New Skills (3) -- EVENT INTELLIGENCE

| Skill | File | Steps | Output |
|-------|------|-------|--------|
| event-intelligence | `event-intelligence/SKILL.md` | Orchestrate live data pull for event + client, load to Snowflake, produce intelligence report | Google Trends, news articles, web intelligence, confidence rating |
| competitor-analysis | `competitor-analysis/SKILL.md` | Compare client vs competitors across news sentiment, web presence, campaign benchmarks | Competitor ranking, threat assessment, opportunity gaps |
| event-strategy | `event-strategy/SKILL.md` | Synthesize internal campaign data + live intelligence into complete event strategy | 9-section strategy: opportunity, competitors, position, channels, creative, timeline, audience, impact, confidence |

---

### Layer 7: Streamlit Dashboard (5 Tabs)
**Object:** `MARKETING_COPILOT.SEMANTIC.MARKETING_COPILOT_APP`
**File:** `streamlit/streamlit_app.py` (~900 lines)
**Runtime:** Warehouse (Python 3.11)
**Dependencies:** plotly (via environment.yml)

#### Key Technical Features
- **parse_agent_response()** -- Robust parser that extracts clean text from any Cortex agent response format (dict, string, list, JSON, nested content arrays). Filters out thinking blocks and tool_use blocks. Never crashes.
- **call_agent_with_auto_continue()** -- Calls agent and automatically retries up to 3 times if response is detected as incomplete (scanning for "time limit", "token limit", etc.)
- **build_html_document()** -- Generates styled HTML documents with NovaSpark branding, dark theme, metadata pills, markdown-to-HTML conversion for downloads
- **js_download_button()** -- JavaScript-based browser download using base64 data URIs. Bypasses Snowflake's S3 presigned URL pipeline entirely, preventing XML/expiry errors
- **render_agent_markdown()** -- Renders agent text as formatted markdown with expandable sections for `## ` headers
- **$$dollar-quoting$$** -- All agent calls use dollar-quoting to prevent SQL injection from special characters in prompts
- **st.experimental_rerun()** -- Used instead of st.rerun() for SiS warehouse runtime compatibility
- **@st.cache_data(ttl=300)** -- 5-minute caching on all SQL queries

#### Sidebar Controls
- Client selector dropdown (12 brands from DIM_CLIENT)
- Product selector (filtered by selected client from DIM_PRODUCT)
- Campaign Objective: Brand Awareness, Lead Generation, Sales Conversion, Customer Retention
- Budget input (USD number field)
- "Analyze and Recommend" button

#### Tab 1: Client Intelligence (Pure SQL, No Agent)

| Component | Data Source | Visualization |
|-----------|-----------|---------------|
| Client Overview (Industry, Region, Products) | DIM_CLIENT, DIM_PRODUCT | st.metric cards |
| Total Campaigns | FACT_CAMPAIGN | st.metric |
| Avg ROAS | FACT_CAMPAIGN_METRICS | st.metric |
| Total Spend | FACT_CAMPAIGN_METRICS | st.metric |
| Total Revenue | FACT_CAMPAIGN_METRICS | st.metric |
| Total Conversions | FACT_CAMPAIGN_METRICS | st.metric |
| Avg Sentiment | FACT_CUSTOMER_FEEDBACK | st.metric |
| ROAS by Channel | FACT_CAMPAIGN_METRICS | Plotly bar chart |
| Monthly Revenue Trend | FACT_CAMPAIGN_METRICS | Plotly line chart |
| Top 5 Campaigns by ROI | FACT_CAMPAIGN_METRICS | Plotly horizontal bar |
| Budget by Campaign Type | FACT_CAMPAIGN | Plotly pie chart |

#### Tab 2: Campaign Recommendation (Agent-Powered)
1. User clicks "Analyze and Recommend"
2. Builds prompt: client + product + objective + budget
3. Calls `call_agent_with_auto_continue()` (auto-retries up to 3x)
4. Agent orchestrates: CampaignAnalytics --> BrandSearch --> MarketSearch --> synthesize
5. Displays structured recommendation via `render_agent_markdown()`
6. Context bar: Client, Product, Objective, Budget, Date
7. Three action buttons: Download as HTML | Approve | Regenerate
8. Download generates styled HTML via `js_download_button()` (no S3)

#### Tab 3: What-If Analysis (Pure Computation, No Agent)
1. Loads historical channel metrics via `load_channel_history()`
2. Shows top 5 channels with equal-split baseline (markdown bullets)
3. Sliders for proposed allocation percentages
4. Real-time projection: revenue = budget x historical_ROAS, clicks = budget / CPC, conversions = clicks x conv_rate
5. Recommendation box (success/warning based on outcome)
6. Grouped bar chart: current vs proposed revenue per channel
7. Delta metrics: projected revenue change, conversion change
8. Download scenario analysis as styled HTML

#### Tab 4: Generate Pitch (Agent-Powered)
1. Only available after recommendation is approved (human-in-the-loop gate)
2. Context bar: Client, Product, Budget, Date
3. Calls agent with 7-section pitch prompt via `call_agent_with_auto_continue()`
4. Displays response via `render_agent_markdown()` with expandable section panels
5. Download as styled HTML with NovaSpark branding
6. "Start Over" resets all session state

#### Tab 5: Event Intelligence (NEW -- Agent-Powered, 3 Stages)

**Stage 1: Input Panel**
- Event selector (Super Bowl, Black Friday, Holiday Season, etc.)
- Keywords, competitors, markets text inputs
- Event budget and objective
- "How It Works" info card explaining the 3-phase process

**Stage 2: Research and Intelligence**
1. Calls Internet Intelligence Agent via `call_agent_with_auto_continue()`
2. Progress bar tracks each step (10% --> 40% --> 80% --> 100%)
3. Queries DIM_EVENT_TRENDS, DIM_NEWS_SENTIMENT, DIM_COMPETITOR_PRESENCE
4. Displays in expandable sections:
   - Intelligence Agent Findings (parsed markdown)
   - Google Trends Analysis (Plotly line chart by keyword, peak detection)
   - News Sentiment Overview (metric cards + pie chart + data table)
   - Competitor Landscape (bar chart by mentions, colored by threat level)

**Stage 3: Strategy Synthesis**
1. Calls Strategy Synthesis Agent via `call_agent_with_auto_continue()`
2. Agent combines internal ROAS data + brand guidelines + live intelligence
3. Displays 9-section strategy via `render_agent_markdown()`
4. Download as styled HTML with event/client/budget metadata
5. "New Research" button resets event intelligence state

---

## 3. Data Flow: Complete System

```
Data Generation         RAW Schema              ANALYTICS Schema         SEMANTIC Schema
================        ==========              ================         ===============

generate_all.py  --->  @MARKETING_STAGE  --->  11 RAW Tables  --->  10 Dynamic Tables
  (Python)              (Internal Stage)        (COPY INTO)          (TARGET_LAG 1min)
                                                                           |
Live Intelligence  --->  5 Event RAW Tables  --->  4 Event Dynamic Tables  |
  (Python pullers)       (INSERT INTO)             (TARGET_LAG 1min)       |
                                                                           |
                                                          +----------------+----+
                                                          |                |    |
                                                    Semantic View    3 Cortex   3 Cortex
                                                   (CAMPAIGN_        Search     Agents
                                                    ANALYTICS)       Services
                                                          |                     |
                                                          +--------+------------+
                                                                   |
                                                            Streamlit App
                                                       (5-Tab Dashboard)
                                                                   |
                                                         Styled HTML Downloads
                                                       (JS data URI, no S3)
```

---

## 4. Snowflake Objects Inventory

| Object Type | Count | Names | Schema |
|------------|-------|-------|--------|
| Database | 1 | MARKETING_COPILOT | - |
| Schemas | 4 | RAW, STAGING, ANALYTICS, SEMANTIC | - |
| Warehouse | 1 | MARKETING_WH (XS, auto-suspend 60s) | - |
| Stages | 3 | MARKETING_STAGE, STREAMLIT_STAGE, SEMANTIC_STAGE | RAW, SEMANTIC, SEMANTIC |
| RAW Tables | 16 | 11 base + 5 event intelligence | RAW |
| Dynamic Tables | 14 | 10 base + 4 event analytics | ANALYTICS |
| Semantic View | 1 | CAMPAIGN_ANALYTICS (7 tables, 11 metrics, 10 VQRs) | SEMANTIC |
| Cortex Search | 3 | BRAND_SEARCH, MARKET_SEARCH, EVENT_NEWS_SEARCH | SEMANTIC |
| Cortex Agents | 3 | MARKETING_COPILOT, INTERNET_INTELLIGENCE_AGENT, STRATEGY_SYNTHESIS_AGENT | SEMANTIC |
| Streamlit | 1 | MARKETING_COPILOT_APP | SEMANTIC |
| **Total Objects** | **47** | | |

---

## 5. Bugs Fixed and Technical Decisions

Throughout development, we encountered and resolved significant issues:

| # | Issue | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | SQL injection in agent calls | Product names like "CW-VitaBoost" broke single-quoted SQL | Switched to $$dollar-quoting$$ with .replace("$$", "$ $") sanitization |
| 2 | st.rerun() not available | SiS warehouse runtime uses older Streamlit | Replaced all with st.experimental_rerun() |
| 3 | Agent empty responses (391920) | Missing execution_environment on Analyst tool | Added execution_environment: {type: warehouse, warehouse: MARKETING_WH} |
| 4 | Responses cut short mid-generation | Agent budget too low (60s/32K tokens) | Increased all 3 agents to 300s/128K tokens + auto-continue (3 retries) |
| 5 | ARRAY_CONSTRUCT in VALUES clause | Snowflake doesn't allow it | Changed INSERT...VALUES to INSERT...SELECT |
| 6 | Semantic view verified_at field | Must be int64 epoch seconds, not date string | Changed to 1724889600 |
| 7 | S3 presigned URL errors on downloads | SiS routes st.download_button through S3 which expires | Replaced with JS data URI downloads (base64 in browser) |
| 8 | Nested expanders crash | render_agent_markdown creates expanders; can't nest inside another | Used parse_agent_response + st.markdown inside outer expander |
| 9 | Session state key collision | st.session_state["ei_competitors"] collided with widget key="ei_competitors" | Renamed data storage keys to ei_comp_data |
| 10 | Agent spec "unrecognized field type" | type field in columns_and_descriptions not valid in CREATE AGENT | Removed type fields from tool_resources |
| 11 | News API key mismatch | UUID-format key was for Event Registry, not NewsAPI | Rewrote news_puller to use Event Registry (primary) + Google News RSS (fallback) |
| 12 | Google Trends 429 rate limit | Expected in automated environments | Added retry logic (wait 10s, retry once) |

---

## 6. Validation and Quality

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

## 7. Project File Structure

```
SnowflakeHackathon/
  README.md
  .gitignore
  data/
    generators/generate_all.py                 # Synthetic data generator (864 lines)
    samples/*.csv                              # 11 generated CSV files (gitignored)
  sql/
    ddl/01_setup.sql                           # Database, schemas, warehouse
    ddl/02_tables.sql                          # 11 RAW table definitions
    ddl/03_event_intelligence_tables.sql       # 5 event intelligence tables (NEW)
    dml/01_load_data.sql                       # COPY INTO statements
    dml/load_data.py                           # Python upload script
    dynamic_tables/01_analytics_layer.sql      # 10 dynamic table definitions
    dynamic_tables/02_event_analytics.sql      # 4 event dynamic tables (NEW)
  semantic_models/
    campaign_analytics.yaml                    # Cortex Analyst semantic view YAML
  agents/
    marketing_copilot_agent.yaml               # Marketing Co-Pilot agent (300s/128K)
    internet_intelligence_agent.yaml           # Internet research agent (NEW)
    strategy_synthesis_agent.yaml              # Strategy builder agent (NEW)
  src/intelligence/                            # Event intelligence pipeline (NEW)
    intelligence_orchestrator.py               # Orchestrates all 3 pullers
    snowflake_loader.py                        # Loads results to Snowflake
    google_trends_puller.py                    # Google Trends data
    news_puller.py                             # Event Registry + Google News RSS
    web_intelligence_puller.py                 # Cortex Complete web research
    config.py                                  # API keys
  streamlit/
    streamlit_app.py                           # 5-tab dashboard (~900 lines)
    environment.yml                            # SiS dependencies (plotly)
    upload_streamlit.py                        # Upload helper
  .snowflake/cortex/skills/
    client-intelligence/SKILL.md               # Client briefing skill
    campaign-analysis/SKILL.md                 # Campaign deep-dive skill
    pitch-generator/SKILL.md                   # Pitch document skill
    what-if-analysis/SKILL.md                  # Scenario comparison skill
    event-intelligence/SKILL.md                # Event research skill (NEW)
    competitor-analysis/SKILL.md               # Competitor analysis skill (NEW)
    event-strategy/SKILL.md                    # Event strategy skill (NEW)
  tests/
    test_validation.sql                        # 8 data quality assertions
  docs/
    requirements/business-requirements.md
    architecture/solution-architecture.md
    marketing_copilot_complete_documentation.md # This document
```

---

## 8. Demo Walkthrough

**Scenario A -- Client Intelligence:**
Select "LuminaRetail" in the sidebar. Tab 1 instantly shows 50 campaigns, 2.36x avg ROAS, $5.36M total spend, and 0.22 avg sentiment. The ROAS-by-channel chart reveals YouTube and Instagram as top performers. The monthly trend shows seasonal peaks around holidays.

**Scenario B -- Campaign Recommendation:**
Select "UrbanThread", product "UT-EcoThread", objective "Brand Awareness", budget $300,000. Click "Analyze and Recommend". The agent queries UrbanThread's historical data, retrieves fashion brand guidelines, finds relevant market events, and produces a structured recommendation with channel allocation, projected ROAS, and conversions. Download as a styled HTML document with NovaSpark branding.

**Scenario C -- What-If Analysis:**
On Tab 3, shift 15% from TV to TikTok using the sliders. The dashboard instantly shows projected revenue increases with additional conversions, and displays a recommendation box indicating whether the proposed scenario is recommended.

**Scenario D -- Pitch Generation:**
After approving the recommendation, go to Tab 4 and click "Generate Full Pitch". The agent produces a 7-section pitch document with Executive Summary, audience analysis, channel strategy, creative direction, and projected impact. Download as styled HTML.

**Scenario E -- Event Intelligence (NEW):**
On Tab 5, select "Super Bowl 2025", enter competitors "Nike, Adidas, Pepsi", markets "US, UK". Click "Run Event Intelligence". The Internet Intelligence Agent researches the event using live web search and stored news articles, displaying progress in real-time. Results show Google Trends charts, news sentiment breakdown, and competitor mention analysis. Then click "Generate Event Strategy" -- the Strategy Synthesis Agent combines internal campaign ROAS data with the live intelligence to produce a 9-section strategy with channel allocation, creative direction, timeline, and competitive positioning. Download the complete strategy as a styled HTML document.

---

## 9. Tech Stack Summary

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Data Platform | Snowflake | All storage, compute, and AI services |
| AI Orchestration | Cortex Agents (x3) | Multi-tool AI orchestrators |
| Structured Analytics | Cortex Analyst (Semantic View) | Natural language to SQL |
| Unstructured Search | Cortex Search Service (x3) | Brand guidelines, market events, and news retrieval |
| Live Intelligence | web_search tool + Python pullers | Real-time internet research |
| Dashboard | Streamlit in Snowflake | 5-tab marketing copilot UI |
| Data Generation | Python (Faker, NumPy, Pandas) | 114K+ rows of synthetic data |
| Skills | CoCo CLI Skills (x7) | Specialized marketing workflows |
| Visualization | Plotly | Dark-themed interactive charts |
| Data Pipeline | Dynamic Tables (x14) | Auto-refreshing analytics layer |
| Downloads | JavaScript data URI (base64) | Styled HTML exports, S3-free |

---

## 10. What Makes This Project Unique

1. **3-Agent Architecture** -- Three specialized Cortex Agents collaborate: one for internal data analysis, one for live internet research, and one for strategy synthesis. This mirrors how real agencies work (research team, analytics team, strategy team).

2. **Live + Historical Fusion** -- The Event Intelligence pipeline combines live Google Trends, news articles, and web research with historical campaign performance data from Snowflake, producing strategies grounded in both real-time market conditions and proven performance metrics.

3. **Human-in-the-Loop Design** -- The recommendation-to-pitch workflow requires explicit approval before generating client-facing documents. This ensures human oversight of AI-generated content before it reaches clients.

4. **Auto-Continue for Long Outputs** -- All agent calls automatically retry up to 3 times if responses are cut short, with intelligent continuation prompts that prevent section repetition. Combined with 300s/128K token budgets, this ensures complete output for complex documents.

5. **S3-Free Downloads** -- JavaScript data URI downloads bypass Snowflake's S3 presigned URL pipeline entirely, generating styled HTML documents with full NovaSpark branding that open in any browser.

6. **114K+ Rows of Realistic Data** -- Synthetic data uses proper statistical distributions (beta for CTR, lognormal for ROAS) with self-consistent metrics (clicks = impressions x CTR, revenue = spend x ROAS), making the analytics genuinely useful for demonstrating the platform.

7. **7 CoCo Skills** -- Each skill is a structured workflow that CoCo Desktop users can invoke directly, extending the platform beyond the Streamlit UI.

---

Built with Snowflake Cortex, CoCo CLI, and Streamlit in Snowflake.
Generated with Cortex Code (https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code)
