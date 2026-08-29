-- ============================================================
-- 01_analytics_layer.sql
-- Dynamic Tables in MARKETING_COPILOT.ANALYTICS schema
-- Cleaned, enriched analytics layer over RAW tables
-- ============================================================

USE WAREHOUSE MARKETING_WH;
USE DATABASE MARKETING_COPILOT;

-- 1. DIM_CLIENT
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.DIM_CLIENT
  TARGET_LAG = '1 minute'
  WAREHOUSE = MARKETING_WH
AS
SELECT
    client_id,
    client_name,
    industry,
    region,
    annual_revenue_usd,
    contract_start_date,
    primary_contact,
    UPPER(status) AS status
FROM RAW.RAW_CLIENTS;

-- 2. DIM_PRODUCT
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.DIM_PRODUCT
  TARGET_LAG = '1 minute'
  WAREHOUSE = MARKETING_WH
AS
SELECT
    p.product_id,
    p.client_id,
    c.client_name,
    p.product_name,
    p.category,
    p.launch_date,
    p.price_tier,
    p.description
FROM RAW.RAW_PRODUCTS p
JOIN RAW.RAW_CLIENTS c ON p.client_id = c.client_id;

-- 3. DIM_CHANNEL
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.DIM_CHANNEL
  TARGET_LAG = '1 minute'
  WAREHOUSE = MARKETING_WH
AS
SELECT
    channel_id,
    channel_name,
    channel_type
FROM RAW.RAW_CHANNELS;

-- 4. DIM_AUDIENCE_SEGMENT
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.DIM_AUDIENCE_SEGMENT
  TARGET_LAG = '1 minute'
  WAREHOUSE = MARKETING_WH
AS
SELECT
    s.segment_id,
    s.client_id,
    c.client_name,
    s.segment_name,
    s.age_band,
    s.gender_skew,
    s.income_level,
    TRY_PARSE_JSON(s.interests_json) AS interests,
    s.estimated_size
FROM RAW.RAW_AUDIENCE_SEGMENTS s
JOIN RAW.RAW_CLIENTS c ON s.client_id = c.client_id;

-- 5. DIM_CUSTOMER_PROFILE
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.DIM_CUSTOMER_PROFILE
  TARGET_LAG = '1 minute'
  WAREHOUSE = MARKETING_WH
AS
SELECT
    cp.customer_id,
    cp.segment_id,
    cp.client_id,
    c.client_name,
    s.segment_name,
    cp.age,
    cp.gender,
    cp.geo_region,
    cp.lifetime_value_usd,
    cp.acquisition_channel,
    cp.join_date
FROM RAW.RAW_CUSTOMER_PROFILES cp
JOIN RAW.RAW_CLIENTS c ON cp.client_id = c.client_id
JOIN RAW.RAW_AUDIENCE_SEGMENTS s ON cp.segment_id = s.segment_id;

-- 6. DIM_MARKET_EVENT
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.DIM_MARKET_EVENT
  TARGET_LAG = '1 minute'
  WAREHOUSE = MARKETING_WH
AS
SELECT
    event_id,
    event_type,
    event_name,
    region,
    start_date,
    end_date,
    DATEDIFF('day', start_date, end_date) + 1 AS duration_days,
    impact_level,
    description,
    affected_industries
FROM RAW.RAW_MARKET_EVENTS;

-- 7. FACT_CAMPAIGN
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.FACT_CAMPAIGN
  TARGET_LAG = '1 minute'
  WAREHOUSE = MARKETING_WH
AS
SELECT
    cam.campaign_id,
    cam.client_id,
    c.client_name,
    c.industry,
    cam.product_id,
    p.product_name,
    p.category AS product_category,
    cam.campaign_name,
    cam.campaign_type,
    cam.objective,
    cam.start_date,
    cam.end_date,
    DATEDIFF('day', cam.start_date, cam.end_date) + 1 AS campaign_duration_days,
    cam.total_budget_usd,
    UPPER(cam.status) AS status
FROM RAW.RAW_CAMPAIGNS cam
JOIN RAW.RAW_CLIENTS c ON cam.client_id = c.client_id
JOIN RAW.RAW_PRODUCTS p ON cam.product_id = p.product_id;

-- 8. FACT_CAMPAIGN_METRICS
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.FACT_CAMPAIGN_METRICS
  TARGET_LAG = '1 minute'
  WAREHOUSE = MARKETING_WH
AS
SELECT
    m.metric_id,
    m.campaign_id,
    cam.client_id,
    cl.client_name,
    cam.campaign_name,
    cam.campaign_type,
    m.channel_id,
    ch.channel_name,
    ch.channel_type,
    m.date,
    m.impressions,
    m.clicks,
    m.conversions,
    m.spend_usd,
    m.revenue_usd,
    CASE WHEN m.impressions > 0 THEN ROUND(m.clicks::FLOAT / m.impressions, 6) ELSE 0 END AS ctr,
    CASE WHEN m.spend_usd > 0 THEN ROUND(m.revenue_usd / m.spend_usd, 4) ELSE 0 END AS roas,
    CASE WHEN m.clicks > 0 THEN ROUND(m.spend_usd / m.clicks, 2) ELSE 0 END AS cpc,
    CASE WHEN m.clicks > 0 THEN ROUND(m.conversions::FLOAT / m.clicks, 6) ELSE 0 END AS conversion_rate
FROM RAW.RAW_CAMPAIGN_METRICS m
JOIN RAW.RAW_CAMPAIGNS cam ON m.campaign_id = cam.campaign_id
JOIN RAW.RAW_CLIENTS cl ON cam.client_id = cl.client_id
JOIN RAW.RAW_CHANNELS ch ON m.channel_id = ch.channel_id;

-- 9. FACT_CUSTOMER_FEEDBACK
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.FACT_CUSTOMER_FEEDBACK
  TARGET_LAG = '1 minute'
  WAREHOUSE = MARKETING_WH
AS
SELECT
    f.feedback_id,
    f.customer_id,
    f.campaign_id,
    cam.client_id,
    cl.client_name,
    cam.campaign_name,
    f.feedback_date,
    f.sentiment_score,
    CASE
        WHEN f.sentiment_score > 0.3 THEN 'positive'
        WHEN f.sentiment_score < -0.3 THEN 'negative'
        ELSE 'neutral'
    END AS sentiment_category,
    f.rating,
    f.feedback_text,
    f.feedback_channel
FROM RAW.RAW_CUSTOMER_FEEDBACK f
JOIN RAW.RAW_CAMPAIGNS cam ON f.campaign_id = cam.campaign_id
JOIN RAW.RAW_CLIENTS cl ON cam.client_id = cl.client_id;

-- 10. FACT_BRAND_GUIDELINES
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.FACT_BRAND_GUIDELINES
  TARGET_LAG = '1 minute'
  WAREHOUSE = MARKETING_WH
AS
SELECT
    bg.guideline_id,
    bg.client_id,
    c.client_name,
    c.industry,
    bg.section_title,
    bg.guideline_text,
    bg.dos,
    bg.donts,
    bg.tone_keywords,
    bg.color_palette,
    bg.created_date,
    c.client_name || ' - ' || bg.section_title AS search_title,
    bg.guideline_text || ' Dos: ' || bg.dos || ' Donts: ' || bg.donts AS search_content
FROM RAW.RAW_BRAND_GUIDELINES bg
JOIN RAW.RAW_CLIENTS c ON bg.client_id = c.client_id;
