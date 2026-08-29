-- ============================================================
-- 03_event_intelligence_tables.sql
-- Tables for Event Intelligence feature
-- ============================================================

USE WAREHOUSE MARKETING_WH;
USE DATABASE MARKETING_COPILOT;

-- 1. Intelligence run metadata
CREATE TABLE IF NOT EXISTS RAW.EVENT_INTELLIGENCE_RUNS (
  run_id VARCHAR(30),
  client_name VARCHAR(100),
  event_name VARCHAR(200),
  competitors ARRAY,
  markets ARRAY,
  confidence VARCHAR(10),
  sources_succeeded NUMBER(2,0),
  run_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  status VARCHAR(20) DEFAULT 'COMPLETED',
  PRIMARY KEY (run_id)
);

-- 2. Google Trends data
CREATE TABLE IF NOT EXISTS RAW.GOOGLE_TRENDS_DATA (
  trend_id VARCHAR(30),
  run_id VARCHAR(30),
  keyword VARCHAR(200),
  trend_date DATE,
  interest_score NUMBER(5,2),
  geo VARCHAR(10),
  is_peak BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 3. News articles
CREATE TABLE IF NOT EXISTS RAW.NEWS_ARTICLES (
  article_id VARCHAR(30),
  run_id VARCHAR(30),
  brand_name VARCHAR(100),
  article_type VARCHAR(20),
  title VARCHAR(500),
  source_name VARCHAR(100),
  published_at TIMESTAMP_NTZ,
  description VARCHAR(2000),
  url VARCHAR(1000),
  sentiment VARCHAR(20),
  sentiment_score NUMBER(5,2),
  created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 4. Web intelligence queries
CREATE TABLE IF NOT EXISTS RAW.WEB_INTELLIGENCE (
  intel_id VARCHAR(30),
  run_id VARCHAR(30),
  query_text VARCHAR(500),
  query_type VARCHAR(50),
  summary VARCHAR(2000),
  key_findings VARIANT,
  competitor_activity VARCHAR(2000),
  consumer_sentiment VARCHAR(20),
  recommended_channels VARIANT,
  sources_found VARIANT,
  created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 5. Strategy output (in ANALYTICS schema)
CREATE TABLE IF NOT EXISTS ANALYTICS.EVENT_STRATEGY_OUTPUT (
  strategy_id VARCHAR(30),
  run_id VARCHAR(30),
  client_name VARCHAR(100),
  event_name VARCHAR(200),
  strategy_text VARCHAR(50000),
  competitor_comparison VARIANT,
  recommended_channels VARIANT,
  recommended_budget_split VARIANT,
  timing_recommendation VARCHAR(2000),
  expected_roas_min NUMBER(5,2),
  expected_roas_max NUMBER(5,2),
  projected_impressions NUMBER(15,0),
  confidence_level VARCHAR(10),
  generated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
