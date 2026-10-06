# Snowflake Marketing Co-Pilot & Pitch Engine

AI-powered marketing intelligence platform for agency teams. It analyzes campaign performance, generates data-backed recommendations and pitches, researches market events live, and produces creative briefs grounded in each client's own data. Built on Snowflake Cortex and Streamlit in Snowflake.

**Hackathon:** Snowflake CoCo CLI Hackathon (GCC Edition)
**Agency:** NovaSpark Agency (fictional; 3 client brands: Nike, Pepsi, Samsung; data is synthetic)
**Deployed account:** CLVULGZ-ZJ61620 · database `MARKETING_COPILOT`

**Full documentation:** [docs/marketing_copilot_complete_documentation.md](docs/marketing_copilot_complete_documentation.md)

---

## Architecture

```
            Streamlit in Snowflake (6 tabs)              External AI clients
                        │                                        │ OAuth
        ┌───────────────┼────────────────┐              MCP server NOVASPARK_MCP (12 tools)
        ▼               ▼                ▼                       │
  Marketing        Internet Intel    Strategy Synthesis ◄────────┘
  Co-Pilot agent   agent             agent
        │               │                │
        ▼               ▼                ▼
  Semantic view   Cortex Search x3   Procedures x5 (creative + intelligence layer)
        └───────────────┴────────────────┘
                        ▼
        ANALYTICS: 14 dynamic tables (1-minute lag)
                        ▲
        RAW: 11 base tables (synthetic CSVs) + 4 event tables (live pipeline)
```

## Quick start (build everything)

```bash
cp .env.example .env                      # set SNOWFLAKE_CONNECTION, EVENT_REGISTRY_API_KEY
pip install snowflake-connector-python pytrends requests eventregistry faker numpy pandas
python data/generators/generate_all.py    # only if data/samples/*.csv are missing
python scripts/deploy_all.py              # DDL, data, dynamic tables, search, semantic view,
                                          # procedures, agents, MCP server, app, 8 validation tests
python src/intelligence/run_pipeline.py   # load live event intelligence (FIFA WC 2026, Black Friday 2026)
```

Open the app in Snowsight under **Projects → Streamlit → NovaSpark Marketing Co-Pilot**.

Useful flags:
- `python scripts/deploy_all.py --skip-data` rebuilds everything except the RAW tables.
- `python scripts/deploy_all.py --app-only` redeploys only the Streamlit app.

The role needs to create databases, warehouses, agents, MCP servers and security integrations (ACCOUNTADMIN on a trial account).

## What's in the app

| Tab | Powered by | What it does |
|---|---|---|
| 1. Client Intelligence | SQL on dynamic tables | KPIs, ROAS by channel, revenue trend, top campaigns, budget mix |
| 2. Campaign Recommendation | MARKETING_COPILOT agent | Recommendation from performance data, brand guidelines and market events; approve to unlock Tab 4 |
| 3. What-If Analysis | Historical channel metrics | Budget-reallocation sliders with projected revenue and conversions |
| 4. Generate Pitch | MARKETING_COPILOT agent | 7-section client pitch (HTML download) |
| 5. Event Intelligence | INTERNET_INTELLIGENCE_AGENT + STRATEGY_SYNTHESIS_AGENT | Live research, Google Trends, news sentiment, competitor presence, 9-section event strategy |
| 6. Creative Studio | Procedures + Cortex intelligence layer | Poster prompt grounded in top channel ROAS, best-converting segment, brand dos/don'ts and market timing; storyboard, design system, audio script, ZIP |

## Snowflake objects

| Layer | Objects |
|---|---|
| Storage | `MARKETING_WH` (XS); schemas `RAW`, `STAGING`, `ANALYTICS`, `SEMANTIC`; 3 stages |
| Data | 16 tables (114K+ base rows + event intelligence), 14 dynamic tables |
| AI | Semantic view `CAMPAIGN_ANALYTICS`; Cortex Search `BRAND_SEARCH`, `MARKET_SEARCH`, `EVENT_NEWS_SEARCH`; agents `MARKETING_COPILOT`, `INTERNET_INTELLIGENCE_AGENT`, `STRATEGY_SYNTHESIS_AGENT` |
| Procedures | `GET_CREATIVE_INTELLIGENCE`, `BUILD_POSTER_PROMPT`, `GENERATE_STORYBOARD`, `BUILD_DESIGN_SYSTEM`, `BUILD_AUDIO_SCRIPT` |
| Access | MCP server `NOVASPARK_MCP`, OAuth integration `NOVASPARK_MCP_OAUTH`, role `MCP_USER_ROLE` |
| App | Streamlit `MARKETING_COPILOT_APP` |

## MCP server

`MARKETING_COPILOT.SEMANTIC.NOVASPARK_MCP` exposes 12 tools: the 3 agents, Cortex Analyst, the 3 search services, and 5 procedures (including `get_creative_intelligence`).

```
URL:   https://<account>.snowflakecomputing.com/api/v2/databases/MARKETING_COPILOT/schemas/SEMANTIC/mcp-servers/NOVASPARK_MCP
OAuth: SELECT SYSTEM$SHOW_OAUTH_CLIENT_SECRETS('NOVASPARK_MCP_OAUTH');
```

## CoCo skills

`client-intelligence`, `campaign-analysis`, `pitch-generator`, `what-if-analysis`, `event-intelligence`, `competitor-analysis`, `event-strategy` (in `.snowflake/cortex/skills/`).

## Secrets

No API keys are committed. `src/env_keys.py` reads them from environment variables or a gitignored `.env` (see `.env.example`). `sql/ddl/04_external_access.sql` uses placeholders and is not run by the build, because trial accounts can't create External Access Integrations.

## Validation

`tests/test_validation.sql` runs at the end of every build. All 8 assertions pass: no NULL keys, valid metric ranges, allocations sum to 100%, Cortex Search and the semantic view respond.

## Known limitations

- **Pipelines run locally.** Event intelligence runs locally, because trial accounts have no External Access Integrations and Streamlit in Snowflake has no outbound HTTP.
- **No image generation.** Poster images are not generated in the app. Creative Studio produces the intelligence-enriched poster prompt; paste it into an external image tool to create the images.
- **Trend window.** Google Trends covers the last 3 months, so peaks for past events are shown as historical, with no launch date.
- **Market events.** The dataset covers 2025 only, so no upcoming events appear.

See the full documentation for details, the issues-fixed log and the demo walkthrough.

---

Built with Snowflake Cortex, Cortex Code, and Streamlit in Snowflake.
