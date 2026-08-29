# Snowflake Marketing Co-Pilot & Pitch Engine

AI-powered marketing intelligence platform that helps agency teams analyze campaign performance, generate data-backed recommendations, and produce client-ready pitch documents -- all powered by Snowflake Cortex.

**Hackathon:** Snowflake CoCo CLI Hackathon (GCC Edition)
**Agency:** NovaSpark Agency (fictional full-service marketing agency)
**Account:** WFVAMNP-AP54607

---

## Architecture

```
                        +---------------------------+
                        |   Streamlit Dashboard     |
                        |   (4-Tab Marketing UI)    |
                        +------------+--------------+
                                     |
                        +------------v--------------+
                        |     Cortex Agent          |
                        |  (Marketing Co-Pilot)     |
                        +--+--------+--------+------+
                           |        |        |
              +------------+  +-----+-----+  +-------------+
              |               |           |                 |
    +---------v--------+ +---v--------+ +-v-----------+ +--v-----------+
    | Cortex Analyst   | | Cortex     | | Cortex      | | data_to_chart|
    | (Semantic View)  | | Search     | | Search      | | (Viz Tool)   |
    | Campaign         | | Brand      | | Market      | |              |
    | Analytics        | | Guidelines | | Events      | |              |
    +--------+---------+ +-----+------+ +------+------+ +--------------+
             |                 |               |
    +--------v---------+ +----v------+  +------v------+
    | Dynamic Tables   | | FACT_BRAND| | DIM_MARKET  |
    | (Analytics Layer)| | GUIDELINES| | _EVENT      |
    +--------+---------+ +-----------+  +-------------+
             |
    +--------v-----------------+
    | RAW Layer (11 Tables)    |
    | Clients, Products,       |
    | Campaigns, Metrics,      |
    | Segments, Feedback, etc. |
    +---------------------------+
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Data Platform | Snowflake |
| AI Orchestration | Cortex Agent |
| Structured Analytics | Cortex Analyst (Semantic View) |
| Unstructured Search | Cortex Search Service (x2) |
| Dashboard | Streamlit in Snowflake |
| Data Generation | Python (Faker, NumPy, Pandas) |
| Skills | CoCo CLI Skills (x4) |
| Visualization | Plotly |

## Database Objects

| Layer | Objects |
|-------|---------|
| Database | `MARKETING_COPILOT` |
| Schemas | `RAW`, `STAGING`, `ANALYTICS`, `SEMANTIC` |
| RAW Tables | 11 tables (114K+ rows) |
| Dynamic Tables | 10 analytics-layer tables |
| Semantic View | `CAMPAIGN_ANALYTICS` (7 tables, 9 metrics, 10 VQRs) |
| Cortex Search | `BRAND_SEARCH`, `MARKET_SEARCH` |
| Cortex Agent | `MARKETING_COPILOT` |
| Streamlit App | `MARKETING_COPILOT_APP` |
| Warehouse | `MARKETING_WH` (XS, auto-suspend 60s) |

## Setup Instructions

### Step 1: Create Database and Schema
```sql
-- Run sql/ddl/01_setup.sql
CREATE DATABASE IF NOT EXISTS MARKETING_COPILOT;
CREATE SCHEMA IF NOT EXISTS MARKETING_COPILOT.RAW;
CREATE SCHEMA IF NOT EXISTS MARKETING_COPILOT.ANALYTICS;
CREATE SCHEMA IF NOT EXISTS MARKETING_COPILOT.SEMANTIC;
CREATE WAREHOUSE IF NOT EXISTS MARKETING_WH WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=60 AUTO_RESUME=TRUE;
```

### Step 2: Generate and Load Synthetic Data
```bash
pip install faker numpy pandas
python data/generators/generate_all.py
# Then upload CSVs and run COPY INTO (see sql/dml/)
```

### Step 3: Create Analytics Layer
```sql
-- Run sql/dynamic_tables/01_analytics_layer.sql
-- Creates 10 dynamic tables with enriched, joined data
```

### Step 4: Deploy Intelligence Layer
```sql
-- Create Cortex Search services (see search/)
-- Create Semantic View (see semantic_models/campaign_analytics.yaml)
-- Create Cortex Agent (see agents/marketing_copilot_agent.yaml)
```

### Step 5: Deploy Streamlit App
```sql
-- Upload streamlit/streamlit_app.py and environment.yml to stage
-- CREATE STREAMLIT ... FROM '@STREAMLIT_STAGE'
-- ALTER STREAMLIT ... ADD LIVE VERSION FROM LAST
```

## Demo Scenarios

### Scenario 1: Client Intelligence Briefing
> "What is the campaign performance summary for LuminaRetail?"

The agent queries campaign metrics via Cortex Analyst, retrieves brand guidelines via Cortex Search, and produces a comprehensive intelligence briefing with ROAS, channel rankings, and sentiment analysis.

### Scenario 2: Campaign Recommendation
> "Create a campaign recommendation for UrbanThread for their new sustainable fashion line targeting eco-conscious millennials with a $300,000 budget."

The agent analyzes UrbanThread's historical performance, identifies top-performing channels (Instagram, TikTok), retrieves brand guidelines for creative direction, checks market events (sustainability moments), and produces a structured recommendation with budget allocation.

### Scenario 3: What-If Budget Reallocation
> Use the What-If Analysis tab to shift 20% of TV budget to TikTok for DriveMax.

The dashboard instantly recalculates projected revenue, impressions, and conversions for both scenarios, showing the delta and recommending the optimal allocation based on historical channel performance.

## CoCo Skills

| Skill | Description |
|-------|-------------|
| `client-intelligence` | Full client briefing: profile, campaigns, performance, sentiment, brand guidelines |
| `campaign-analysis` | Deep campaign analysis: channel ranking, top/bottom campaigns, segment insights |
| `pitch-generator` | 7-section pitch document with data-backed projections |
| `what-if-analysis` | Scenario comparison with projected metrics |

## Data Model

12 client brands across industries, each with:
- 50 campaigns (600 total) spanning 2023-2025
- Daily campaign metrics across 10 channels (76K+ rows)
- 5-8 audience segments per client (71 total)
- 10,000 customer profiles
- 25,000 customer feedback records
- 53 market events (holidays, economic, competitor, regulatory, cultural)
- 110 brand guideline sections

## Validation

All 8 data quality assertions pass:
- No NULL foreign keys
- Valid metric ranges (ROAS > 0, spend > 0, sentiment in [-1,1])
- Referential integrity (allocation sums to 100%)
- Cortex Search and Analyst services responding

## Project Structure

```
SnowflakeHackathon/
  README.md
  .gitignore
  data/
    generators/generate_all.py       # Synthetic data generator
    samples/                         # 11 CSV files (gitignored)
  sql/
    ddl/01_setup.sql                 # Database, schemas, warehouse
    ddl/02_tables.sql                # 11 RAW table definitions
    dml/01_load_data.sql             # COPY INTO statements
    dynamic_tables/01_analytics_layer.sql  # 10 dynamic tables
  semantic_models/
    campaign_analytics.yaml          # Cortex Analyst semantic view
  agents/
    marketing_copilot_agent.yaml     # Cortex Agent definition
  streamlit/
    streamlit_app.py                 # 4-tab Streamlit dashboard
    environment.yml                  # SiS dependencies
  .snowflake/cortex/skills/
    client-intelligence/SKILL.md
    campaign-analysis/SKILL.md
    pitch-generator/SKILL.md
    what-if-analysis/SKILL.md
  tests/
    test_validation.sql              # 8 data quality assertions
  docs/
    requirements/business-requirements.md
    architecture/solution-architecture.md
```

## Screenshots

> Add screenshots of the Streamlit dashboard here after the demo.

| Tab | Description |
|-----|-------------|
| Client Intelligence | KPI cards, ROAS by channel chart, monthly revenue trend |
| Campaign Recommendation | Agent-generated recommendation with channel allocation |
| What-If Analysis | Scenario comparison with projected metrics |
| Generate Pitch | Full pitch document with expandable sections |

---

Built with Snowflake Cortex, CoCo CLI, and Streamlit in Snowflake.

Generated with [Cortex Code](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code)
