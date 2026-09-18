-- ============================================
-- Snowflake-Managed MCP Server: NOVASPARK_MCP
-- 11 tools exposing all NovaSpark capabilities
-- ============================================

USE ROLE ACCOUNTADMIN;
USE DATABASE MARKETING_COPILOT;
USE SCHEMA SEMANTIC;

CREATE OR REPLACE MCP SERVER NOVASPARK_MCP
  FROM SPECIFICATION $$
tools:
  # === 3 Cortex Agents ===
  - name: "marketing_copilot"
    type: "CORTEX_AGENT_RUN"
    identifier: "MARKETING_COPILOT.SEMANTIC.MARKETING_COPILOT"
    title: "Marketing Co-Pilot"
    description: "Answers campaign performance questions, generates recommendations and pitches for 12 client brands."

  - name: "internet_intelligence"
    type: "CORTEX_AGENT_RUN"
    identifier: "MARKETING_COPILOT.SEMANTIC.INTERNET_INTELLIGENCE_AGENT"
    title: "Internet Intelligence Agent"
    description: "Researches market events using live web search, stored news articles, and campaign benchmarks."

  - name: "strategy_synthesis"
    type: "CORTEX_AGENT_RUN"
    identifier: "MARKETING_COPILOT.SEMANTIC.STRATEGY_SYNTHESIS_AGENT"
    title: "Strategy Synthesis Agent"
    description: "Combines internal campaign data with live intelligence to build event marketing strategies."

  # === Cortex Analyst ===
  - name: "campaign_analytics"
    type: "CORTEX_ANALYST_MESSAGE"
    identifier: "MARKETING_COPILOT.SEMANTIC.CAMPAIGN_ANALYTICS"
    title: "Campaign Analytics"
    description: "Natural language SQL queries against campaign metrics (ROAS, CTR, conversions, spend, revenue)."

  # === 3 Cortex Search Services ===
  - name: "brand_search"
    type: "CORTEX_SEARCH_SERVICE_QUERY"
    identifier: "MARKETING_COPILOT.SEMANTIC.BRAND_SEARCH"
    title: "Brand Guidelines Search"
    description: "Search brand guidelines for voice, tone, visual identity, messaging framework."

  - name: "market_search"
    type: "CORTEX_SEARCH_SERVICE_QUERY"
    identifier: "MARKETING_COPILOT.SEMANTIC.MARKET_SEARCH"
    title: "Market Events Search"
    description: "Search market events including holidays, economic events, competitor launches."

  - name: "event_news_search"
    type: "CORTEX_SEARCH_SERVICE_QUERY"
    identifier: "MARKETING_COPILOT.SEMANTIC.EVENT_NEWS_SEARCH"
    title: "Event News Search"
    description: "Search news articles from intelligence runs."

  # === 4 Custom Tools (stored procedures) ===
  - name: "generate_storyboard"
    type: "GENERIC"
    identifier: "MARKETING_COPILOT.SEMANTIC.GENERATE_STORYBOARD"
    title: "Generate Video Storyboard"
    description: "Generate a 4-scene video storyboard for a brand campaign."
    config:
      type: "procedure"
      warehouse: "MARKETING_WH"
      input_schema:
        type: "object"
        properties:
          client_name: {type: "string", description: "Client brand name"}
          product_name: {type: "string", description: "Product name"}
          objective: {type: "string", description: "Campaign objective"}
          creative_direction: {type: "string", description: "Creative direction"}

  - name: "build_design_system"
    type: "GENERIC"
    identifier: "MARKETING_COPILOT.SEMANTIC.BUILD_DESIGN_SYSTEM"
    title: "Build Design System"
    description: "Generate a brand design system with palette, tone, dos and donts."
    config:
      type: "procedure"
      warehouse: "MARKETING_WH"
      input_schema:
        type: "object"
        properties:
          client_name: {type: "string"}
          brand_colours: {type: "string", description: "Comma-separated hex codes"}
          tone_keywords: {type: "string", description: "Comma-separated tone keywords"}

  - name: "build_poster_prompt"
    type: "GENERIC"
    identifier: "MARKETING_COPILOT.SEMANTIC.BUILD_POSTER_PROMPT"
    title: "Build Poster Prompt"
    description: "Generate an optimized prompt for Gemini Imagen 3 poster generation."
    config:
      type: "procedure"
      warehouse: "MARKETING_WH"
      input_schema:
        type: "object"
        properties:
          client_name: {type: "string"}
          product_name: {type: "string"}
          objective: {type: "string"}
          target_audience: {type: "string"}
          brand_colours: {type: "string"}
          tone_keywords: {type: "string"}
          creative_direction: {type: "string"}
          event_name: {type: "string"}

  - name: "build_audio_script"
    type: "GENERIC"
    identifier: "MARKETING_COPILOT.SEMANTIC.BUILD_AUDIO_SCRIPT"
    title: "Build Audio Script"
    description: "Generate a 30-second voiceover script prompt."
    config:
      type: "procedure"
      warehouse: "MARKETING_WH"
      input_schema:
        type: "object"
        properties:
          client_name: {type: "string"}
          product_name: {type: "string"}
          objective: {type: "string"}
          tone_keywords: {type: "string"}
$$;

-- ============================================
-- OAuth Security Integration for MCP Clients
-- ============================================

-- Note: Update OAUTH_REDIRECT_URI to match your MCP client
-- Claude: https://claude.ai/api/mcp/auth_callback
-- ChatGPT: shown during connector setup
-- Cursor: localhost callback

CREATE OR REPLACE SECURITY INTEGRATION NOVASPARK_MCP_OAUTH
  TYPE = OAUTH
  OAUTH_CLIENT = CUSTOM
  ENABLED = TRUE
  OAUTH_CLIENT_TYPE = 'CONFIDENTIAL'
  OAUTH_REDIRECT_URI = 'https://claude.ai/api/mcp/auth_callback'
  OAUTH_USE_SECONDARY_ROLES = NONE;

-- ============================================
-- Access Control
-- ============================================

CREATE ROLE IF NOT EXISTS MCP_USER_ROLE;

-- Core access
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_AGENT_USER TO ROLE MCP_USER_ROLE;
GRANT USAGE ON WAREHOUSE MARKETING_WH TO ROLE MCP_USER_ROLE;
GRANT USAGE ON DATABASE MARKETING_COPILOT TO ROLE MCP_USER_ROLE;
GRANT USAGE ON SCHEMA MARKETING_COPILOT.SEMANTIC TO ROLE MCP_USER_ROLE;
GRANT USAGE ON SCHEMA MARKETING_COPILOT.ANALYTICS TO ROLE MCP_USER_ROLE;

-- MCP server access
GRANT USAGE ON MCP SERVER MARKETING_COPILOT.SEMANTIC.NOVASPARK_MCP TO ROLE MCP_USER_ROLE;

-- Agent access
GRANT USAGE ON AGENT MARKETING_COPILOT.SEMANTIC.MARKETING_COPILOT TO ROLE MCP_USER_ROLE;
GRANT USAGE ON AGENT MARKETING_COPILOT.SEMANTIC.INTERNET_INTELLIGENCE_AGENT TO ROLE MCP_USER_ROLE;
GRANT USAGE ON AGENT MARKETING_COPILOT.SEMANTIC.STRATEGY_SYNTHESIS_AGENT TO ROLE MCP_USER_ROLE;

-- Search service access
GRANT USAGE ON CORTEX SEARCH SERVICE MARKETING_COPILOT.SEMANTIC.BRAND_SEARCH TO ROLE MCP_USER_ROLE;
GRANT USAGE ON CORTEX SEARCH SERVICE MARKETING_COPILOT.SEMANTIC.MARKET_SEARCH TO ROLE MCP_USER_ROLE;
GRANT USAGE ON CORTEX SEARCH SERVICE MARKETING_COPILOT.SEMANTIC.EVENT_NEWS_SEARCH TO ROLE MCP_USER_ROLE;

-- Semantic view access
GRANT SELECT ON SEMANTIC VIEW MARKETING_COPILOT.SEMANTIC.CAMPAIGN_ANALYTICS TO ROLE MCP_USER_ROLE;

-- Procedure access
GRANT USAGE ON PROCEDURE MARKETING_COPILOT.SEMANTIC.GENERATE_STORYBOARD(VARCHAR, VARCHAR, VARCHAR, VARCHAR) TO ROLE MCP_USER_ROLE;
GRANT USAGE ON PROCEDURE MARKETING_COPILOT.SEMANTIC.BUILD_DESIGN_SYSTEM(VARCHAR, VARCHAR, VARCHAR) TO ROLE MCP_USER_ROLE;
GRANT USAGE ON PROCEDURE MARKETING_COPILOT.SEMANTIC.BUILD_POSTER_PROMPT(VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR) TO ROLE MCP_USER_ROLE;
GRANT USAGE ON PROCEDURE MARKETING_COPILOT.SEMANTIC.BUILD_AUDIO_SCRIPT(VARCHAR, VARCHAR, VARCHAR, VARCHAR) TO ROLE MCP_USER_ROLE;

-- Grant role to user
GRANT ROLE MCP_USER_ROLE TO USER AJITHKUMAR;
