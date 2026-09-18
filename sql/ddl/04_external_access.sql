-- ============================================
-- External Access Integrations for MCP Tools
-- Enables stored procedures to call external APIs
-- ============================================

USE ROLE ACCOUNTADMIN;
USE DATABASE MARKETING_COPILOT;
USE SCHEMA SEMANTIC;
USE WAREHOUSE MARKETING_WH;

-- ============================================
-- 1. Network Rules (egress to external APIs)
-- ============================================

CREATE OR REPLACE NETWORK RULE gemini_api_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('generativelanguage.googleapis.com:443');

CREATE OR REPLACE NETWORK RULE event_registry_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('eventregistry.org:443', 'www.eventregistry.org:443');

CREATE OR REPLACE NETWORK RULE google_news_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('news.google.com:443');

CREATE OR REPLACE NETWORK RULE google_trends_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('trends.google.com:443');

-- ============================================
-- 2. Secrets (API keys stored securely)
-- ============================================

CREATE OR REPLACE SECRET gemini_api_key
  TYPE = GENERIC_STRING
  SECRET_STRING = 'AQ.Ab8RN6lg3t1W6dv-ce1eItUjeKsRAWy5bqRjJG1MJCsoF_82gg';

CREATE OR REPLACE SECRET event_registry_api_key
  TYPE = GENERIC_STRING
  SECRET_STRING = '009d88db-708b-40c9-b175-047c12cebb23';

-- ============================================
-- 3. External Access Integrations
-- ============================================

CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION gemini_access
  ALLOWED_NETWORK_RULES = (gemini_api_rule)
  ALLOWED_AUTHENTICATION_SECRETS = (gemini_api_key)
  ENABLED = TRUE;

CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION news_access
  ALLOWED_NETWORK_RULES = (event_registry_rule, google_news_rule)
  ALLOWED_AUTHENTICATION_SECRETS = (event_registry_api_key)
  ENABLED = TRUE;

CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION trends_access
  ALLOWED_NETWORK_RULES = (google_trends_rule)
  ENABLED = TRUE;
