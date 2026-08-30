-- ============================================================
-- 02_event_analytics.sql
-- Dynamic Tables for Event Intelligence analytics layer
-- ============================================================

USE WAREHOUSE MARKETING_WH;
USE DATABASE MARKETING_COPILOT;

-- 1. DIM_EVENT_TRENDS
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.DIM_EVENT_TRENDS
  TARGET_LAG = '1 minute'
  WAREHOUSE = MARKETING_WH
AS
SELECT t.trend_id, t.run_id, r.client_name, r.event_name, t.keyword,
  t.trend_date, t.interest_score, t.geo, t.is_peak,
  CASE WHEN t.interest_score >= 75 THEN 'High'
       WHEN t.interest_score >= 40 THEN 'Medium' ELSE 'Low' END AS interest_level,
  r.confidence, r.run_timestamp
FROM RAW.GOOGLE_TRENDS_DATA t
JOIN RAW.EVENT_INTELLIGENCE_RUNS r ON t.run_id = r.run_id;

-- 2. DIM_NEWS_SENTIMENT
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.DIM_NEWS_SENTIMENT
  TARGET_LAG = '1 minute'
  WAREHOUSE = MARKETING_WH
AS
SELECT n.article_id, n.run_id, r.client_name, r.event_name, n.brand_name,
  n.article_type, n.title, n.source_name, n.published_at, n.description, n.url,
  n.sentiment, n.sentiment_score,
  CASE WHEN n.brand_name = r.client_name THEN 'OUR_BRAND' ELSE 'COMPETITOR' END AS brand_type,
  r.confidence
FROM RAW.NEWS_ARTICLES n
JOIN RAW.EVENT_INTELLIGENCE_RUNS r ON n.run_id = r.run_id;

-- 3. DIM_WEB_INTELLIGENCE
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.DIM_WEB_INTELLIGENCE
  TARGET_LAG = '1 minute'
  WAREHOUSE = MARKETING_WH
AS
SELECT w.intel_id, w.run_id, r.client_name, r.event_name, w.query_text,
  w.query_type, w.summary, w.key_findings, w.competitor_activity,
  w.consumer_sentiment, w.recommended_channels, r.confidence, r.run_timestamp
FROM RAW.WEB_INTELLIGENCE w
JOIN RAW.EVENT_INTELLIGENCE_RUNS r ON w.run_id = r.run_id;

-- 4. DIM_COMPETITOR_PRESENCE
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.DIM_COMPETITOR_PRESENCE
  TARGET_LAG = '1 minute'
  WAREHOUSE = MARKETING_WH
AS
WITH news_sentiment AS (
  SELECT run_id, brand_name, COUNT(*) AS total_articles,
    SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) AS positive_count,
    SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) AS negative_count,
    SUM(CASE WHEN sentiment = 'neutral' THEN 1 ELSE 0 END) AS neutral_count,
    ROUND(AVG(sentiment_score), 2) AS avg_sentiment_score
  FROM RAW.NEWS_ARTICLES GROUP BY run_id, brand_name
)
SELECT ns.run_id, r.client_name, r.event_name, ns.brand_name,
  CASE WHEN ns.brand_name = r.client_name THEN 'OUR_BRAND' ELSE 'COMPETITOR' END AS brand_type,
  ns.total_articles, ns.positive_count, ns.negative_count, ns.neutral_count,
  ns.avg_sentiment_score,
  CASE WHEN ns.avg_sentiment_score > 0.3 THEN 'Positive'
       WHEN ns.avg_sentiment_score < -0.3 THEN 'Negative' ELSE 'Neutral' END AS overall_sentiment,
  CASE WHEN ns.total_articles >= 8 THEN 'High'
       WHEN ns.total_articles >= 4 THEN 'Medium' ELSE 'Low' END AS media_presence
FROM news_sentiment ns
JOIN RAW.EVENT_INTELLIGENCE_RUNS r ON ns.run_id = r.run_id;
