# NovaSpark Marketing Co-Pilot & Pitch Engine — Complete Documentation

**Hackathon:** Snowflake CoCo CLI Hackathon (GCC Edition)
**Project:** NovaSpark Agency Marketing Co-Pilot & Pitch Engine
**Repository:** github.com/Ajith1431/snowflake-marketing-copilot (branch `master`)
**Deployed account:** CLVULGZ-ZJ61620 (AWS ap-south-1), database `MARKETING_COPILOT`
**Team:** Ajithkumar M (ajithkumar.m@wpp.com), with coworker contributions from `sriramnb/Campaign-intelligence-AI-snowflake`

---

## Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Data Layer](#3-data-layer)
4. [AI Layer: Semantic View, Search, Agents](#4-ai-layer-semantic-view-search-agents)
5. [Event Intelligence Pipeline](#5-event-intelligence-pipeline)
6. [Creative Studio and the Cortex Intelligence Layer](#6-creative-studio-and-the-cortex-intelligence-layer)
7. [MCP Server](#7-mcp-server)
8. [Streamlit App (6 Tabs)](#8-streamlit-app-6-tabs)
9. [CoCo Skills](#9-coco-skills)
10. [Build and Deployment Guide](#10-build-and-deployment-guide)
11. [Configuration and Secrets](#11-configuration-and-secrets)
12. [Validation](#12-validation)
13. [Snowflake Objects Inventory](#13-snowflake-objects-inventory)
14. [Repository Structure](#14-repository-structure)
15. [Known Limitations](#15-known-limitations)
16. [Issues Fixed and Technical Decisions](#16-issues-fixed-and-technical-decisions)
17. [Demo Walkthrough](#17-demo-walkthrough)

---

## 1. Project Overview

### What it is
An AI-powered marketing intelligence platform built on Snowflake. It helps agency teams:

- Analyze campaign performance across 3 client brands (Nike, Pepsi, Samsung)
- Generate data-backed campaign recommendations and client pitch documents
- Compare budget-allocation scenarios with projected outcomes
- Pull live market intelligence (Google Trends, news, Cortex web research) for market events
- Build event-specific marketing strategies with competitor analysis
- Produce creative briefs (poster prompt, video storyboard, design system, audio script) grounded in each client's own performance data and brand guidelines
- Expose all of the above to external AI clients (Claude, ChatGPT, Cursor) through a Snowflake-managed MCP server

### The business problem
Agencies spend days assembling performance data, audience insights and competitive intelligence for a single pitch. Analysts, strategists and creatives work from disconnected sources. NovaSpark collapses that workflow into one Snowflake-native app where every recommendation, strategy and creative brief is grounded in the same governed data.

### What it is not
NovaSpark is a marketing intelligence platform at the client-brand, campaign, channel and segment level. It is not a Customer 360: customer profiles and feedback exist (2,522 profiles, 6,316 feedback rows) but there is no individual-level identity resolution or per-customer activation.

---

## 2. Architecture

```
                        ┌───────────────────────────────────────────────┐
                        │  Streamlit in Snowflake: MARKETING_COPILOT_APP │
                        │  1 Client Intel  2 Recommendation  3 What-If   │
                        │  4 Pitch  5 Event Intelligence  6 Creative     │
                        └──────────────┬────────────────────────────────┘
                                       │ SQL / DATA_AGENT_RUN / CALL
     ┌─────────────────────────────────┼──────────────────────────────────────┐
     │                                 │                                      │
┌────▼─────────────┐  ┌────────────────▼──────────┐  ┌─────────────────────────▼──┐
│ MARKETING_COPILOT│  │ INTERNET_INTELLIGENCE_AGENT│  │ STRATEGY_SYNTHESIS_AGENT   │
│ Analyst + Brand/ │  │ web_search + EventNews +   │  │ Analyst + Brand + EventNews│
│ Market Search    │  │ Analyst benchmarks         │  │ + web_search               │
└────┬─────────────┘  └────────────┬───────────────┘  └──────────┬─────────────────┘
     │                             │                             │
     ▼                             ▼                             ▼
 Semantic View            Cortex Search (x3)            Stored procedures (x5)
 CAMPAIGN_ANALYTICS       BRAND / MARKET / EVENT_NEWS   creative + intelligence
     │                             │                             │
     └──────────────┬──────────────┴─────────────────────────────┘
                    ▼
       ANALYTICS: 14 Dynamic Tables (TARGET_LAG 1 minute)
                    ▲
       RAW: 11 base tables (CSV via COPY INTO) + 4 event tables (Python pipeline)
                    ▲                                   ▲
   data/generators/generate_all.py         src/intelligence/run_pipeline.py
   (synthetic agency data)                 (Google Trends, Event Registry, Cortex COMPLETE)

   External AI clients ──OAuth──► MCP server NOVASPARK_MCP (12 tools) ──► agents / analyst / search / procedures
```

### Design principles
- **Everything lives in Snowflake.** Data, transformations, AI services, app and MCP endpoint are all Snowflake objects; the only off-platform pieces are the local Python pipeline (because trial accounts can't create External Access Integrations) and no image generation (Creative Studio stops at the poster prompt).
- **One source of truth for creative and strategy.** Agents and Creative Studio read the same dynamic tables, so a poster prompt and a channel recommendation can't disagree about which channel performs best.
- **Human in the loop.** A recommendation must be approved (Tab 2) before a client pitch can be generated (Tab 4).

---

## 3. Data Layer

### 3.1 Synthetic data generation
**File:** `data/generators/generate_all.py` — generates 11 CSVs (114,365 rows) for the fictional NovaSpark Agency.

The generator produces 12 fictional clients; `sql/dml/02_reduce_clients.sql` (run by `deploy_all.py` right after the load) keeps three and renames them, deleting the other nine and all their dependent rows:

| Client | Industry | Generated as |
|---|---|---|
| Nike | Sportswear | UrbanThread (C010) |
| Pepsi | Food & Beverage | FlavorCo (C009) |
| Samsung | Technology | TechVista (C002) |

Each brand is then trimmed to three products with no prefixes (surplus generated products collapse onto the nearest kept product_id): Nike: Running Collection, Training Apparel, Lifestyle Sneakers; Pepsi: Zero Sugar Cola, Sparkling Citrus, Energy Drink; Samsung: Flagship Smartphone, Smart TV, Wearables. Brand names are labels on synthetic data.

Distributions are realistic and self-consistent: CTR 0.5–5% (beta), ROAS 1.2–7.0 (lognormal), conversion rate 1–8% (beta); clicks = impressions × CTR, conversions = clicks × conversion rate, revenue = spend × ROAS. Channel spend scales by channel type (TV $2K–10K/day, social $100–2K/day, email $50–500/day).

### 3.2 RAW schema (15 tables)
**Files:** `sql/ddl/02_tables.sql`, `sql/ddl/03_event_intelligence_tables.sql`

| Table | Rows | Source | Description |
|---|---|---|---|
| RAW_CLIENTS | 3 | CSV | Client brands |
| RAW_PRODUCTS | 9 | CSV | 3 products per client |
| RAW_CHANNELS | 10 | CSV | Instagram, YouTube, Google Search, Facebook, LinkedIn, TikTok, Email, Programmatic Display, TV, Out-of-Home |
| RAW_AUDIENCE_SEGMENTS | 17 | CSV | 5–8 segments per client, interests as JSON |
| RAW_CUSTOMER_PROFILES | 2,522 | CSV | Customer demographics |
| RAW_CAMPAIGNS | 150 | CSV | 50 campaigns per client, 2023–2025 |
| RAW_BRIDGE_CAMPAIGN_SEGMENT | 467 | CSV | Campaign→segment allocation (sums to 100%) |
| RAW_CAMPAIGN_METRICS | 19,535 | CSV | Daily campaign × channel metrics |
| RAW_CUSTOMER_FEEDBACK | 6,316 | CSV | Sentiment-scored feedback |
| RAW_MARKET_EVENTS | 53 | CSV | Holidays, economic, competitor, regulatory, cultural events (2025) |
| RAW_BRAND_GUIDELINES | 29 | CSV | 8–10 guideline sections per client incl. dos/donts, tone, palette |
| EVENT_INTELLIGENCE_RUNS | 2 | pipeline | One row per intelligence run (client, event, competitors, markets, confidence) |
| GOOGLE_TRENDS_DATA | 837 | pipeline | Daily interest score per keyword, peak flag |
| NEWS_ARTICLES | 73 | pipeline | Event / brand / competitor news with sentiment |
| WEB_INTELLIGENCE | 16 | pipeline | Cortex COMPLETE research: summary, key findings, channels, sentiment |

`ANALYTICS.EVENT_STRATEGY_OUTPUT` is also created by `03_event_intelligence_tables.sql` for the `event-strategy` skill to persist strategies; the Streamlit app does not write to it.

### 3.3 ANALYTICS schema (14 dynamic tables, TARGET_LAG = 1 minute)
**Files:** `sql/dynamic_tables/01_analytics_layer.sql`, `sql/dynamic_tables/02_event_analytics.sql`

| Dynamic table | Built from | Enrichment |
|---|---|---|
| DIM_CLIENT | RAW_CLIENTS | status uppercased |
| DIM_PRODUCT | + RAW_CLIENTS | client_name |
| DIM_CHANNEL | RAW_CHANNELS | passthrough |
| DIM_AUDIENCE_SEGMENT | + RAW_CLIENTS | interests parsed to VARIANT, client_name |
| DIM_CUSTOMER_PROFILE | + clients, segments | client_name, segment_name |
| DIM_MARKET_EVENT | RAW_MARKET_EVENTS | duration_days |
| FACT_CAMPAIGN | + clients, products | product_name, industry, duration |
| FACT_CAMPAIGN_METRICS | + campaigns, clients, channels | recomputed CTR, ROAS, CPC, conversion rate (divide-by-zero safe) |
| FACT_CUSTOMER_FEEDBACK | + campaigns, clients | sentiment_category |
| FACT_BRAND_GUIDELINES | + clients | search_title, search_content |
| DIM_EVENT_TRENDS | GOOGLE_TRENDS_DATA + runs | client, event, interest_level (High/Medium/Low) |
| DIM_NEWS_SENTIMENT | NEWS_ARTICLES + runs | brand_type |
| DIM_WEB_INTELLIGENCE | WEB_INTELLIGENCE + runs | client, event, confidence |
| DIM_COMPETITOR_PRESENCE | NEWS_ARTICLES + runs | article counts, sentiment mix, overall_sentiment, media_presence |

Four of the joins are complex enough that Snowflake auto-selects FULL refresh (DIM_CUSTOMER_PROFILE, FACT_CAMPAIGN, FACT_CAMPAIGN_METRICS, FACT_CUSTOMER_FEEDBACK); the rest refresh incrementally.

---

## 4. AI Layer: Semantic View, Search, Agents

### 4.1 Cortex Analyst semantic view
**Object:** `SEMANTIC.CAMPAIGN_ANALYTICS` — **File:** `semantic_models/campaign_analytics.yaml` (created with `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML`).

7 logical tables and 6 relationships:
```
FACT_CAMPAIGN_METRICS ─CAMPAIGN_ID─► FACT_CAMPAIGN ─CLIENT_ID─► DIM_CLIENT
FACT_CAMPAIGN_METRICS ─CHANNEL_ID──► DIM_CHANNEL   FACT_CAMPAIGN ─PRODUCT_ID─► DIM_PRODUCT
BRIDGE_CAMPAIGN_SEGMENT ─CAMPAIGN_ID─► FACT_CAMPAIGN
BRIDGE_CAMPAIGN_SEGMENT ─SEGMENT_ID──► DIM_AUDIENCE_SEGMENT
```

11 metrics: TOTAL_IMPRESSIONS, TOTAL_CLICKS, TOTAL_CONVERSIONS, TOTAL_SPEND, TOTAL_REVENUE, AVG_CTR, AVG_ROAS, AVG_CPC, AVG_CONVERSION_RATE (FACT_CAMPAIGN_METRICS); TOTAL_BUDGET, CAMPAIGN_COUNT (FACT_CAMPAIGN).

10 verified queries: highest-ROAS campaigns for Nike; spend by channel in 2024; best-converting segment; performance by industry; Samsung monthly revenue; best channel for sportswear; CTR by campaign type; top 5 campaigns by ROI; lowest-CPC segment; budget vs actual spend by client.

### 4.2 Cortex Search services
**File:** `sql/ddl/07_cortex_search.sql` (TARGET_LAG 1 hour, embedding model snowflake-arctic-embed-m-v1.5)

| Service | Search column | Filter attributes | Source | Docs |
|---|---|---|---|---|
| BRAND_SEARCH | GUIDELINE_TEXT | CLIENT_NAME, SECTION_TITLE | FACT_BRAND_GUIDELINES | 110 |
| MARKET_SEARCH | DESCRIPTION | EVENT_TYPE, REGION, IMPACT_LEVEL | DIM_MARKET_EVENT | 53 |
| EVENT_NEWS_SEARCH | SEARCH_TEXT (title + description) | BRAND_NAME, SENTIMENT, ARTICLE_TYPE | RAW.NEWS_ARTICLES | 73 |

### 4.3 Cortex Agents (3)
**Files:** `agents/*.yaml` — each file is the exact `CREATE AGENT … FROM SPECIFICATION` body. All use `orchestration: auto` and a 300 s / 128,000-token budget.

| Agent | Tools | Role |
|---|---|---|
| MARKETING_COPILOT | CampaignAnalytics (Analyst), BrandSearch, MarketSearch, data_to_chart | Campaign Q&A, recommendations, pitches (Tabs 2 and 4) |
| INTERNET_INTELLIGENCE_AGENT | web_search, EventNewsSearch, CampaignBenchmarks (Analyst), data_to_chart | Structured event research report with confidence rating (Tab 5 stage 2) |
| STRATEGY_SYNTHESIS_AGENT | CampaignAnalytics, BrandSearch, EventNewsSearch, web_search, data_to_chart | 9-section event strategy with dual-justified channel allocation (Tab 5 stage 3) |

The Analyst tools set `execution_environment: {type: warehouse, warehouse: MARKETING_WH}`; without it, agent calls return empty responses.

---

## 5. Event Intelligence Pipeline

**Directory:** `src/intelligence/` — runs locally and loads results into Snowflake. (A Snowflake-native version would need External Access Integrations, which trial accounts can't create.)

| Module | Responsibility |
|---|---|
| `run_pipeline.py` | Entry point. Runs the configured events and loads each run. `python src/intelligence/run_pipeline.py [FIFA ...]` runs a subset by event-name substring. |
| `intelligence_orchestrator.py` | `run_full_intelligence()` runs the three pullers, scores confidence (3 sources = HIGH, 2 = MEDIUM, 1 = LOW) and builds a summary. |
| `google_trends_puller.py` | pytrends, last 3 months (`today 3-m`), peak detection, rising queries. |
| `news_puller.py` | Event Registry (primary) + Google News RSS (fallback); event, brand and competitor articles with sentiment. |
| `web_intelligence_puller.py` | 8 research queries per run via `SNOWFLAKE.CORTEX.COMPLETE('claude-sonnet-4-6', messages, {max_tokens: 2048})`; parses JSON findings, channels and sentiment. |
| `snowflake_loader.py` | Inserts into the 4 RAW event tables (batched, escaped). |
| `config.py` | Reads `EVENT_REGISTRY_API_KEY`, `NEWS_API_KEY`, `SNOWFLAKE_CONNECTION` via `src/env_keys.py`. |

Loaded runs:

| Client / event | Competitors | Confidence | Trends | News | Web queries |
|---|---|---|---|---|---|
| Nike / FIFA World Cup 2026 | Adidas, Puma | HIGH | 465 | 39 | 7 |
| Samsung / Black Friday 2026 | Apple, Xiaomi | HIGH | 372 | 31 | 7 |

After a run, the 4 event dynamic tables refresh within a minute and `EVENT_NEWS_SEARCH` within an hour (or immediately with `ALTER CORTEX SEARCH SERVICE … REFRESH`).

---

## 6. Creative Studio and the Cortex Intelligence Layer

**Files:** `sql/ddl/05_mcp_procedures.sql`, Tab 6 in `streamlit/streamlit_app.py`.

### 6.1 Stored procedures (Python 3.11)

| Procedure | Returns | Purpose |
|---|---|---|
| `GET_CREATIVE_INTELLIGENCE(CLIENT_NAME, EVENT_NAME DEFAULT '')` | VARIANT | The Cortex intelligence layer (below) |
| `BUILD_POSTER_PROMPT(8 brief fields, INTEL_JSON DEFAULT '')` | VARCHAR | Poster prompt; enriched when INTEL_JSON is supplied |
| `GENERATE_STORYBOARD(CLIENT, PRODUCT, OBJECTIVE, DIRECTION)` | VARIANT | 4-scene, 5-second video storyboard + video prompt |
| `BUILD_DESIGN_SYSTEM(CLIENT, COLOURS, TONE)` | VARIANT | Palette, tone, dos/donts |
| `BUILD_AUDIO_SCRIPT(CLIENT, PRODUCT, OBJECTIVE, TONE)` | VARIANT | 30-second voiceover script prompt |

### 6.2 What the intelligence layer adds
`GET_CREATIVE_INTELLIGENCE` returns, from live Snowflake data:

| Signal | Source | Used in the poster prompt as |
|---|---|---|
| Top 3 channels by avg ROAS (+ CTR, revenue) | FACT_CAMPAIGN_METRICS | "Compose primarily for YouTube (best channel, avg ROAS 2.64x)…" |
| Highest-converting segment (age, gender skew, income, interests) | metrics × bridge × DIM_AUDIENCE_SEGMENT | "Cast and styling for 'Athleisure Fans' (22-39 … yoga, running)" |
| Most common brand dos / don'ts, tone, palette | FACT_BRAND_GUIDELINES | "Brand dos: … Avoid: …"; palette and tone also pre-fill the form |
| Market timing: event trend peak and launch date (6 weeks before peak); most relevant market event | DIM_EVENT_TRENDS, DIM_MARKET_EVENT | Urgency / seasonal clause |

Rules that keep the output honest:
- If the trend peak is already in the past, `peak_in_past` is set, no launch date is recommended, and the prompt says "ride proven demand" rather than inventing a future date.
- A market event is only described as upcoming if its start date is in the future; otherwise it's labelled "latest relevant market event" and kept out of the prompt.

Example (Nike, FIFA World Cup 2026; figures from the original 12-client build):
> …Event: FIFA World Cup 2026. Cast and styling for the highest-converting segment 'Athleisure Fans' (22-39, Balanced, Medium income; interests: yoga, running, comfortable). Compose primarily for YouTube (best channel, avg ROAS 2.64x): bold focal point, legible at small sizes, clear space for a call to action. Brand dos: Optimize for mobile; … Avoid: Use stock photos; … Ride proven 'World Cup 2026' search demand (peaked 2026-07-19)…

### 6.3 Image generation
Poster images are not generated in the app. Creative Studio produces the intelligence-enriched poster prompt; paste it into an external image tool to create the images. The ZIP download contains the design system, the poster, video and audio prompts and the storyboard; it contains no images.

---

## 7. MCP Server

**Object:** `SEMANTIC.NOVASPARK_MCP` — **File:** `sql/ddl/06_mcp_server.sql`

| Tool | Type | Backed by |
|---|---|---|
| marketing_copilot | CORTEX_AGENT_RUN | MARKETING_COPILOT |
| internet_intelligence | CORTEX_AGENT_RUN | INTERNET_INTELLIGENCE_AGENT |
| strategy_synthesis | CORTEX_AGENT_RUN | STRATEGY_SYNTHESIS_AGENT |
| campaign_analytics | CORTEX_ANALYST_MESSAGE | CAMPAIGN_ANALYTICS |
| brand_search / market_search / event_news_search | CORTEX_SEARCH_SERVICE_QUERY | the 3 search services |
| get_creative_intelligence | GENERIC (procedure) | GET_CREATIVE_INTELLIGENCE |
| generate_storyboard / build_design_system / build_poster_prompt / build_audio_script | GENERIC (procedure) | creative procedures |

Access: OAuth security integration `NOVASPARK_MCP_OAUTH` (redirect URI set for Claude; change it for other clients) and role `MCP_USER_ROLE`, which holds usage on the agents, search services, semantic view, procedures and warehouse. The script grants the role to whoever runs it.

Endpoint:
```
https://<account>.snowflakecomputing.com/api/v2/databases/MARKETING_COPILOT/schemas/SEMANTIC/mcp-servers/NOVASPARK_MCP
```
Get the OAuth client ID and secret with `SELECT SYSTEM$SHOW_OAUTH_CLIENT_SECRETS('NOVASPARK_MCP_OAUTH');`. Re-running `06_mcp_server.sql` recreates the integration, which issues new credentials.

---

## 8. Streamlit App (6 Tabs)

**Object:** `SEMANTIC.MARKETING_COPILOT_APP` (warehouse runtime, `MARKETING_WH`) — **File:** `streamlit/streamlit_app.py` — **Dependencies:** plotly (`environment.yml`).

### 8.1 Shared helpers
| Helper | Purpose |
|---|---|
| `call_named_agent` / `call_agent_with_auto_continue` | `SNOWFLAKE.CORTEX.DATA_AGENT_RUN` with $$-quoted payloads; continues up to 3 times when a response looks cut off |
| `parse_agent_response` | Extracts clean text from any agent response shape; drops thinking and tool blocks |
| `render_agent_markdown` | Renders `## ` sections as expanders |
| `build_html_document` + `js_download_button` | Styled NovaSpark HTML reports downloaded via base64 data URIs (SiS routes `st.download_button` through S3, which breaks) |
| `load_creative_intelligence` | Cached call to `GET_CREATIVE_INTELLIGENCE` |
| `@st.cache_data(ttl=300)` | 5-minute cache on all queries |

**Sidebar:** client, product (filtered by client), campaign objective, budget, "Analyze and Recommend".

### 8.2 Tabs
| Tab | Engine | What it does |
|---|---|---|
| 1. Client Intelligence | SQL | KPI cards (campaigns, avg ROAS, spend, revenue, conversions, sentiment); ROAS by channel, monthly revenue, top 5 campaigns by ROI, budget by campaign type |
| 2. Campaign Recommendation | MARKETING_COPILOT | Recommendation from analytics + brand + market search; download, approve, regenerate |
| 3. What-If Analysis | Python projection | Channel-allocation sliders; projected revenue/conversions from historical ROAS, CPC, conversion rate; comparison chart; HTML download |
| 4. Generate Pitch | MARKETING_COPILOT | 7-section client pitch, unlocked only after approval in Tab 2; HTML download |
| 5. Event Intelligence | INTERNET_INTELLIGENCE_AGENT then STRATEGY_SYNTHESIS_AGENT | Pick an event (FIFA World Cup 2026 and Black Friday 2026 have loaded data), competitors, markets, budget; research report, Google Trends chart, news sentiment, competitor media presence; then 9-section strategy; HTML download |
| 6. Creative Studio | Procedures + intelligence layer | Brief form pre-filled with brand palette/tone; **Cortex Intelligence panel** (top channels, primary segment, brand guardrails, market timing); generates storyboard cards, design system, poster prompt, audio script; ZIP download |

---

## 9. CoCo Skills

**Directory:** `.snowflake/cortex/skills/` — invoked from Cortex Code in this project.

| Skill | Output |
|---|---|
| client-intelligence | Full client briefing: profile, portfolio, performance, sentiment, brand guidelines |
| campaign-analysis | Channel / type / segment breakdown, top and bottom campaigns, seasonality |
| pitch-generator | 7-section pitch with projected KPIs |
| what-if-analysis | Side-by-side scenario comparison |
| event-intelligence | Live data pull for an event, loaded into Snowflake |
| competitor-analysis | Brand vs competitors across news, web and benchmarks (needs an event-intelligence run) |
| event-strategy | 9-section event strategy from internal + live data |

---

## 10. Build and Deployment Guide

### 10.1 Prerequisites
- A Snowflake account and a role that can create databases, warehouses, agents, MCP servers and security integrations (ACCOUNTADMIN on a trial). Cortex Agents, Cortex Search and `claude-sonnet-4-6` must be available in the region (verified on AWS ap-south-1).
- Python 3.10+ with `snowflake-connector-python`. For the event pipeline also: `pytrends`, `requests`, `eventregistry`. For data generation: `faker`, `numpy`, `pandas`.
- A connection in `~/.snowflake/connections.toml`. Password or key-pair auth avoids browser pop-ups during long scripts.

### 10.2 One-command build
```bash
cp .env.example .env                      # set SNOWFLAKE_CONNECTION, EVENT_REGISTRY_API_KEY
python data/generators/generate_all.py    # only if data/samples/*.csv are missing
python scripts/deploy_all.py              # builds everything and runs the 8 validation tests
python src/intelligence/run_pipeline.py   # loads live event intelligence (2 events)
```

`scripts/deploy_all.py` runs these steps in dependency order:

| Step | What | Files |
|---|---|---|
| 1 | Database, 4 schemas, warehouse, 3 stages, RAW + event tables | `sql/ddl/01_setup.sql`, `02_tables.sql`, `03_event_intelligence_tables.sql` |
| 2 | PUT 11 CSVs, COPY INTO RAW tables | `data/samples/*.csv`, `sql/dml/01_load_data.sql` |
| 3 | 14 dynamic tables | `sql/dynamic_tables/01_analytics_layer.sql`, `02_event_analytics.sql` |
| 4 | 3 Cortex Search services | `sql/ddl/07_cortex_search.sql` |
| 5 | Semantic view | `semantic_models/campaign_analytics.yaml` |
| 6 | 5 stored procedures | `sql/ddl/05_mcp_procedures.sql` |
| 7 | 3 Cortex Agents | `agents/*.yaml` |
| 8 | MCP server, OAuth integration, MCP_USER_ROLE | `sql/ddl/06_mcp_server.sql` |
| 9 | Streamlit app | `streamlit/streamlit_app.py`, `environment.yml` |
| 10 | Validation | `tests/test_validation.sql` |

Flags:
- `--skip-data` keeps the existing RAW tables and rebuilds everything else.
- `--app-only` only re-uploads and recreates the Streamlit app.

The script exits non-zero if any validation test fails. Last full run on CLVULGZ-ZJ61620: all steps OK, 8/8 tests PASS.

Re-run behaviour: a full build recreates and reloads the 11 base RAW tables. The 4 event tables use `CREATE TABLE IF NOT EXISTS`, so intelligence runs survive rebuilds.

### 10.3 Not run by the build
`sql/ddl/04_external_access.sql` creates network rules, secrets and External Access Integrations so the pullers could run inside Snowflake. Trial accounts reject External Access Integrations. On a paid account, replace the `<EVENT_REGISTRY_API_KEY>` placeholder at run time and never commit real keys.

### 10.4 Updating the app only
```bash
python scripts/deploy_all.py --app-only
```
Equivalent SQL: `PUT` the app file to `@MARKETING_COPILOT.SEMANTIC.STREAMLIT_STAGE` and `CREATE OR REPLACE STREAMLIT … ROOT_LOCATION='@…STREAMLIT_STAGE' MAIN_FILE='streamlit_app.py' QUERY_WAREHOUSE=MARKETING_WH`. `ALTER STREAMLIT … ADD LIVE VERSION` is not needed.

---

## 11. Configuration and Secrets

No API keys are stored in the repository. `src/env_keys.py` reads them from environment variables, falling back to a gitignored `.env` at the repo root. `.env.example` lists every variable.

| Variable | Used by | Required |
|---|---|---|
| SNOWFLAKE_CONNECTION | `scripts/deploy_all.py`, `src/intelligence/*` | Recommended (defaults to `clvulgz-zj61620` for the pipeline) |
| EVENT_REGISTRY_API_KEY | news puller | For the event pipeline |
| NEWS_API_KEY | news puller | Optional |

Keys committed before this change are still in git history; they must be rotated.

`backend/` (from the coworker repo) is a separate settings module for a FastAPI-style backend. It reads `SNOWFLAKE_*`, `APP_*`, and `JWT_*` via `python-dotenv`. The Streamlit app doesn't use it, and neither do the `animations-lottie/` assets.

---

## 12. Validation

`tests/test_validation.sql` (run automatically by the build):

| Test | Assertion | Result |
|---|---|---|
| T1 | No NULL client_ids in fact tables | PASS |
| T2 | All ROAS values > 0 | PASS |
| T3 | All spend values > 0 | PASS |
| T4 | end_date > start_date for all campaigns | PASS |
| T5 | sentiment_score in [-1, 1] | PASS |
| T6 | Segment allocation sums to 100% per campaign | PASS |
| T7 | BRAND_SEARCH returns results | PASS |
| T8 | CAMPAIGN_ANALYTICS semantic view is queryable | PASS |

Additional checks performed after the build:
- MARKETING_COPILOT answered "best ROAS channel for Nike (then UrbanThread)" with "YouTube, ~2.64x (confidence HIGH)", matching `GET_CREATIVE_INTELLIGENCE`.
- `GET_CREATIVE_INTELLIGENCE` and the 9-argument `BUILD_POSTER_PROMPT` were tested for Nike, Samsung and one since-removed client; the 8-argument call still works.
- The corrected Tab 5 queries return 200 trend rows, 39 news rows and 3 competitors for FIFA World Cup 2026.
- The app UI itself has not been tested by an automated browser run; open it in Snowsight to confirm layout.

---

## 13. Snowflake Objects Inventory

| Type | Count | Names |
|---|---|---|
| Database | 1 | MARKETING_COPILOT |
| Schemas | 4 | RAW, STAGING (reserved, empty), ANALYTICS, SEMANTIC |
| Warehouse | 1 | MARKETING_WH (XSMALL, auto-suspend 60 s) |
| Stages | 3 | RAW.MARKETING_STAGE, SEMANTIC.SEMANTIC_STAGE, SEMANTIC.STREAMLIT_STAGE |
| Tables | 16 | 11 base RAW + 4 event RAW + ANALYTICS.EVENT_STRATEGY_OUTPUT |
| Dynamic tables | 14 | 10 analytics + 4 event analytics |
| Semantic view | 1 | CAMPAIGN_ANALYTICS |
| Cortex Search services | 3 | BRAND_SEARCH, MARKET_SEARCH, EVENT_NEWS_SEARCH |
| Cortex Agents | 3 | MARKETING_COPILOT, INTERNET_INTELLIGENCE_AGENT, STRATEGY_SYNTHESIS_AGENT |
| Stored procedures | 5 | GET_CREATIVE_INTELLIGENCE, BUILD_POSTER_PROMPT, GENERATE_STORYBOARD, BUILD_DESIGN_SYSTEM, BUILD_AUDIO_SCRIPT |
| MCP server | 1 | NOVASPARK_MCP (12 tools) |
| Security integration | 1 | NOVASPARK_MCP_OAUTH |
| Role | 1 | MCP_USER_ROLE |
| Streamlit app | 1 | MARKETING_COPILOT_APP |

---

## 14. Repository Structure

```
SnowflakeHackathon/
├── README.md
├── .env.example                      # all environment variables (copy to .env)
├── .gitignore                        # ignores .env, data/samples/*.csv, connections.toml
├── agents/                           # CREATE AGENT specifications
│   ├── marketing_copilot_agent.yaml
│   ├── internet_intelligence_agent.yaml
│   └── strategy_synthesis_agent.yaml
├── semantic_models/
│   ├── campaign_analytics.yaml       # semantic view definition
│   ├── campaign_analytics_proto.json
│   └── upload_yaml.py
├── sql/
│   ├── ddl/01_setup.sql              # database, schemas, warehouse, stages
│   ├── ddl/02_tables.sql             # 11 RAW tables
│   ├── ddl/03_event_intelligence_tables.sql
│   ├── ddl/04_external_access.sql    # paid accounts only; not run by the build
│   ├── ddl/05_mcp_procedures.sql     # 5 creative + intelligence procedures
│   ├── ddl/06_mcp_server.sql         # MCP server, OAuth, MCP_USER_ROLE
│   ├── ddl/07_cortex_search.sql      # 3 Cortex Search services
│   ├── dml/01_load_data.sql          # COPY INTO
│   ├── dml/load_data.py
│   └── dynamic_tables/01_analytics_layer.sql, 02_event_analytics.sql
├── data/
│   ├── generators/generate_all.py
│   └── samples/*.csv                 # generated (gitignored)
├── src/
│   ├── env_keys.py                   # env / .env key loader
│   ├── intelligence/                 # event intelligence pipeline (section 5)
├── scripts/
│   ├── deploy_all.py                 # one-command build
├── streamlit/
│   ├── streamlit_app.py              # 6-tab app
│   ├── environment.yml
│   └── upload_streamlit.py
├── tests/
│   ├── test_validation.sql           # 8 assertions
│   └── test_event_intelligence.py
├── output/creative/                  # sample creative output (JSON + ZIP)
├── backend/                          # coworker settings module (not used by the app)
├── animations-lottie/                # coworker Lottie assets (not used by the app)
├── .streamlit/config.toml
├── .snowflake/cortex/skills/         # 7 CoCo skills
├── .snowflake/cortex/plans/          # design plans
└── docs/
    ├── marketing_copilot_complete_documentation.md   # this document
    ├── architecture/solution-architecture.md
    └── requirements/business-requirements.md
```

---

## 15. Known Limitations

| Limitation | Impact | Workaround |
|---|---|---|
| Trial accounts can't create External Access Integrations | Pullers can't run inside Snowflake | Run `src/intelligence/run_pipeline.py` locally |
| No image generation in the app | Tab 6 produces the poster prompt, not the images | Poster images are not generated in the app. Creative Studio produces the intelligence-enriched poster prompt; paste it into an external image tool to create the images. |
| Google Trends window is the last 3 months | For past events the "peak" is historical, so no launch date is recommended | Re-run the pipeline closer to an event, or widen `timeframe` in `intelligence_orchestrator.py` |
| Market events dataset covers 2025 only | No "upcoming" market events are shown | Regenerate `market_events.csv` with future dates |
| Google Trends rate-limits rapid repeat pulls | A run can come back with 0 trend rows | Wait 1–2 minutes, re-run that event only (`run_pipeline.py FIFA`) |
| Tab 5 events other than FIFA World Cup 2026 / Black Friday 2026 have no stored data | Charts are empty for those events; agents still research live | Add the event to `RUNS` in `run_pipeline.py` and run it |

---

## 16. Issues Fixed and Technical Decisions

| # | Issue | Root cause | Fix |
|---|---|---|---|
| 1 | Prompts with quotes broke agent SQL | Single-quoted SQL literals | $$-quoting with `$$` → `$ $` sanitising |
| 2 | `st.rerun()` missing | Older Streamlit in SiS warehouse runtime | `st.experimental_rerun()` |
| 3 | Empty agent responses | Analyst tool lacked execution environment | `execution_environment: warehouse MARKETING_WH` |
| 4 | Responses cut off | Low agent budget | 300 s / 128K tokens + auto-continue (3 rounds) |
| 5 | `ARRAY_CONSTRUCT` in VALUES rejected | Snowflake restriction | INSERT … SELECT |
| 6 | Semantic view `verified_at` rejected | Must be epoch seconds | 1724889600 |
| 7 | Download links failed (S3 / XML errors) | SiS routes `st.download_button` through expiring S3 URLs | Base64 data-URI downloads of styled HTML |
| 8 | Nested expander crash | `render_agent_markdown` inside another expander | `parse_agent_response` + `st.markdown` |
| 9 | Widget key collision | Data stored under a widget's key | Separate `ei_*_data` keys |
| 10 | "unrecognized field type" on CREATE AGENT | `type` inside `columns_and_descriptions` | Removed; agent YAMLs now match deployed specs exactly |
| 11 | `st.container(border=True)` TypeError | Not supported in SiS runtime | Removed `border` |
| 12 | Web intelligence always empty | `CORTEX.COMPLETE` with a messages array requires an options argument; response read from the wrong field | Added `{max_tokens: 2048}`; read `choices[0].messages` |
| 13 | Pipeline hard-wired to old account | Connection name hardcoded | `SNOWFLAKE_CONNECTION` setting |
| 14 | Tab 5 trends/news/competitor sections always empty | Queries selected columns that don't exist in the event dynamic tables; errors were swallowed | Aliased real columns; competitor chart excludes event-level rows; loaded events added to the dropdown |
| 15 | Generic poster prompts | Prompt used only free-text brief fields | `GET_CREATIVE_INTELLIGENCE` + enriched `BUILD_POSTER_PROMPT` |
| 16 | Past dates presented as launch / upcoming | 3-month trend window and 2025-only events | `peak_in_past` and `upcoming` flags |
| 17 | API keys committed to git | Hardcoded in scripts, config and SQL | `src/env_keys.py` + `.env`; placeholders in SQL; keys to be rotated |
| 18 | Project not rebuildable from the repo | Search services, stages, semantic view and agents were created by hand | `sql/ddl/07_cortex_search.sql`, stages in `01_setup.sql`, `scripts/deploy_all.py` |

---

## 17. Demo Walkthrough

1. **Client Intelligence:** select Pepsi. Tab 1 shows campaigns, ROAS, spend, revenue and sentiment with channel and trend charts.
2. **Recommendation:** select Nike, a product, "Brand Awareness" and $300,000, then click Analyze and Recommend. The agent combines Nike's channel history, brand guidelines and market events. Approve the recommendation.
3. **What-If:** in Tab 3, move budget from TV to TikTok and compare projected revenue and conversions.
4. **Pitch:** in Tab 4, generate the 7-section pitch and download it as HTML.
5. **Event Intelligence:** in Tab 5, pick FIFA World Cup 2026 with client Nike and competitors "Adidas, Puma". You get the research report, Google Trends chart, news sentiment and competitor media presence. Then generate the 9-section strategy.
6. **Creative Studio:** in Tab 6, with client Nike and event "FIFA World Cup 2026", the intelligence panel shows YouTube as the top channel (2.64x), "Athleisure Fans" as the primary segment, the brand guardrails and the World Cup trend peak. Click Generate Creative Assets, copy the enriched poster prompt into an external image tool, and download the ZIP.
7. **MCP:** connect Claude or Cursor to `NOVASPARK_MCP`, call `get_creative_intelligence` for a client, then `build_poster_prompt` with the result as `intel_json`.

---

Built with Snowflake Cortex, Cortex Code, and Streamlit in Snowflake.
