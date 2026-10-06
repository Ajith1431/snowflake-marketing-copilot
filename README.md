# Snowflake Marketing Co-Pilot & Pitch Engine

AI-powered marketing intelligence platform for agency teams. It analyzes campaign performance, generates data-backed recommendations and pitches with consistent KPIs, researches market events live, attributes CTR to creative attributes, predicts CTR for creative scenarios, and produces creative briefs grounded in each client's own data. Built on Snowflake Cortex and Streamlit in Snowflake.

**Hackathon:** Snowflake CoCo CLI Hackathon (GCC Edition)
**Agency:** NovaSpark Agency (fictional; 3 client brands: Nike (Sportswear), Pepsi (Food & Beverage), Samsung (Technology); 3 products each; all data is synthetic and brand names are labels only)
**Deployed account:** CLVULGZ-ZJ61620 · database `MARKETING_COPILOT`

**Full documentation:** [docs/marketing_copilot_complete_documentation.md](docs/marketing_copilot_complete_documentation.md)

---

## Architecture

```
            Streamlit in Snowflake (7 tabs)              External AI clients
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
        RAW: 11 base tables (synthetic CSVs, reduced to 3 clients) + 4 event tables (live pipeline)

        CREATIVE (separate synthetic ad-level dataset, 600 ads)
          V_AD_FEATURES ─► COMPUTE_NET_LEAN (Tab 7)   TRAIN_CTR_MODEL ─► SCORE_AD (Tab 3)
```

## Quick start (build everything)

```bash
cp .env.example .env                      # set SNOWFLAKE_CONNECTION, EVENT_REGISTRY_API_KEY
pip install snowflake-connector-python pytrends requests eventregistry faker numpy pandas
python data/generators/generate_all.py    # only if data/samples/*.csv are missing
python scripts/deploy_all.py              # DDL, data (+ 3-client reduction and 2026-27 event calendar),
                                          # dynamic tables, search, semantic view, procedures, agents,
                                          # MCP server, app, validation tests
python scripts/load_creative.py           # CREATIVE schema: synthetic ad-level dataset
python scripts/deploy_creative_ml.py      # NET_LEAN attribution + CTR model + SCORE_AD
python src/intelligence/run_pipeline.py   # live event intelligence (Nike / FIFA World Cup 2026, Samsung / Black Friday 2026)
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
| 2. Campaign Recommendation | MARKETING_COPILOT agent + channel planner | Channel plan and projected KPIs from pooled historical per-dollar rates (clicks x CPC = budget), then the agent's recommendation; approve to unlock Tab 4 |
| 3. Predictor | `CREATIVE.SCORE_AD` | Compare two creative scenarios: predicted CTR with p10-p90 range and a per-change swap decomposition |
| 4. Generate Pitch | MARKETING_COPILOT agent | 7-section client pitch that reuses the approved Tab 2 plan and KPIs unchanged (HTML download) |
| 5. Event Intelligence | INTERNET_INTELLIGENCE_AGENT + STRATEGY_SYNTHESIS_AGENT | Live research, Google Trends, news sentiment, competitor presence; event strategy with a Sources section. Black Friday 2026 is the live example; FIFA World Cup 2026 is retrospective |
| 6. Creative Studio | Procedures + Cortex intelligence layer | Poster prompt grounded in top channel ROAS, best-converting segment, brand dos/don'ts and market timing; storyboard, design system, audio script, ZIP. No images are generated |
| 7. Performance Drivers | `CREATIVE.NET_LEAN` | Adjusted CTR lift of each creative attribute value vs a stated reference, 95% bootstrap intervals, market strip, model card |

All HTML downloads start at the first heading, render tables as HTML, and drop closing offers. Agents receive today's date: ended events are described as past, and only events starting after today are called upcoming. Channel-ranking confidence is capped at MEDIUM (historical averages, no significance testing).

## Creative intelligence (synthetic)

The `CREATIVE` schema holds a separate synthetic dataset of 600 ads (Nike, Pepsi, Samsung x UAE, KSA, UK, US, IN) with planted effects; the answer key lives only in `tests/fixtures/ground_truth_effects.json` and is never loaded into Snowflake for the app or agents.

- **Attribution (`NET_LEAN`):** ridge-adjusted log-odds contrasts of each attribute value vs a stated reference value (e.g. product_led vs promo_led), controlling for spend, brand, placement, market and objective; 200-draw bootstrap intervals; classes NET_HELPED / NET_HURT / MIXED / NEGLIGIBLE / INCONCLUSIVE / INSUFFICIENT_DATA.
- **Predictor:** HistGradientBoosting on log-odds CTR (holdout R² 0.54 ad-week, 0.66 ad level), conformal p10-p90 ranges.
- **Checks (local, against the answer key):** effect recovery 33/35 direction (94%); false-positive rate 3.3% on null effects; model-level check 20/24 direction, median model/planted ratio 0.77. Results are shown on the Tab 7 model card.

## Snowflake objects

| Layer | Objects |
|---|---|
| Storage | `MARKETING_WH` (XS); schemas `RAW`, `STAGING`, `ANALYTICS`, `SEMANTIC`, `CREATIVE`; stages for data, app, code and model |
| Data | RAW base tables (3 clients, 9 products, 150 campaigns, 19.5K daily metrics) + 4 event tables, 14 dynamic tables, 67 market events (2023-2027) |
| AI | Semantic view `CAMPAIGN_ANALYTICS`; Cortex Search `BRAND_SEARCH`, `MARKET_SEARCH`, `EVENT_NEWS_SEARCH`; agents `MARKETING_COPILOT`, `INTERNET_INTELLIGENCE_AGENT`, `STRATEGY_SYNTHESIS_AGENT` |
| Procedures | `GET_CREATIVE_INTELLIGENCE`, `BUILD_POSTER_PROMPT`, `GENERATE_STORYBOARD`, `BUILD_DESIGN_SYSTEM`, `BUILD_AUDIO_SCRIPT`; `CREATIVE.COMPUTE_NET_LEAN`, `CREATIVE.TRAIN_CTR_MODEL`, `CREATIVE.SCORE_AD` |
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

- `tests/test_validation.sql` (9 assertions, run at the end of every build): no NULL keys, valid metric ranges, allocations sum to 100%, Cortex Search and the semantic view respond, client set is exactly Nike, Pepsi, Samsung.
- `tests/test_creative.sql` (14 assertions): CREATIVE row counts, funnel monotonicity, NET_LEAN class rules and reference coding, model metrics, predictions, SCORE_AD, owner-only answer-key tables.
- `scripts/smoke_test_app.py`: headless run of every tab against live Snowflake (`PYTHONIOENCODING=utf-8` on Windows).
- `scripts/make_example_exports.py`: regenerates the four example HTML exports in `output/examples/`.

Run SQL tests with `python scripts/run_sql_tests.py tests/<file>.sql`.

## Known limitations

- **Synthetic data.** All campaign and creative data is synthetic; brand names are labels. Outputs are illustrations, not forecasts.
- **Pipelines run locally.** Event intelligence runs locally, because trial accounts have no External Access Integrations and Streamlit in Snowflake has no outbound HTTP.
- **No image generation.** Poster images are not generated in the app. Creative Studio produces the intelligence-enriched poster prompt; paste it into an external image tool to create the images.
- **Trend window.** Google Trends covers the last 3 months, so peaks for past events are shown as historical, with no launch date.
- **Competitive claims.** Competitor statements in event strategies come from live web research and need verification.
- **Small cells.** Brand x market cells have 26-54 ads, so Tab 7 falls back to the all-brands view; no multiple-comparison correction is applied (about 1 in 20 null cells is flagged).

See the full documentation for details, the issues-fixed log and the demo walkthrough.

---

Built with Snowflake Cortex, Cortex Code, and Streamlit in Snowflake.
