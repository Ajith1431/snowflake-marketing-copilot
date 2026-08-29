-- ============================================================
-- 02_tables.sql
-- Creates all RAW tables in MARKETING_COPILOT.RAW
-- ============================================================

USE WAREHOUSE MARKETING_WH;
USE DATABASE MARKETING_COPILOT;
USE SCHEMA RAW;

-- 1. RAW_CLIENTS
CREATE OR REPLACE TABLE RAW_CLIENTS (
    client_id           VARCHAR(10)     NOT NULL,
    client_name         VARCHAR(100)    NOT NULL,
    industry            VARCHAR(50)     NOT NULL,
    region              VARCHAR(50)     NOT NULL,
    annual_revenue_usd  NUMBER(15,2),
    contract_start_date DATE,
    primary_contact     VARCHAR(100),
    status              VARCHAR(20),
    PRIMARY KEY (client_id)
);

-- 2. RAW_PRODUCTS
CREATE OR REPLACE TABLE RAW_PRODUCTS (
    product_id      VARCHAR(10)     NOT NULL,
    client_id       VARCHAR(10)     NOT NULL,
    product_name    VARCHAR(100)    NOT NULL,
    category        VARCHAR(50),
    launch_date     DATE,
    price_tier      VARCHAR(20),
    description     VARCHAR(1000),
    PRIMARY KEY (product_id)
);

-- 3. RAW_CHANNELS
CREATE OR REPLACE TABLE RAW_CHANNELS (
    channel_id      VARCHAR(10)     NOT NULL,
    channel_name    VARCHAR(50)     NOT NULL,
    channel_type    VARCHAR(30)     NOT NULL,
    PRIMARY KEY (channel_id)
);

-- 4. RAW_AUDIENCE_SEGMENTS
CREATE OR REPLACE TABLE RAW_AUDIENCE_SEGMENTS (
    segment_id      VARCHAR(10)     NOT NULL,
    client_id       VARCHAR(10)     NOT NULL,
    segment_name    VARCHAR(100)    NOT NULL,
    age_band        VARCHAR(20),
    gender_skew     VARCHAR(30),
    income_level    VARCHAR(30),
    interests_json  VARIANT,
    estimated_size  INTEGER,
    PRIMARY KEY (segment_id)
);

-- 5. RAW_CUSTOMER_PROFILES
CREATE OR REPLACE TABLE RAW_CUSTOMER_PROFILES (
    customer_id         VARCHAR(12)     NOT NULL,
    segment_id          VARCHAR(10)     NOT NULL,
    client_id           VARCHAR(10)     NOT NULL,
    age                 INTEGER,
    gender              VARCHAR(20),
    geo_region          VARCHAR(50),
    lifetime_value_usd  NUMBER(12,2),
    acquisition_channel VARCHAR(30),
    join_date           DATE,
    PRIMARY KEY (customer_id)
);

-- 6. RAW_CAMPAIGNS
CREATE OR REPLACE TABLE RAW_CAMPAIGNS (
    campaign_id         VARCHAR(10)     NOT NULL,
    client_id           VARCHAR(10)     NOT NULL,
    product_id          VARCHAR(10)     NOT NULL,
    campaign_name       VARCHAR(200)    NOT NULL,
    campaign_type       VARCHAR(30),
    objective           VARCHAR(200),
    start_date          DATE,
    end_date            DATE,
    total_budget_usd    NUMBER(12,2),
    status              VARCHAR(20),
    PRIMARY KEY (campaign_id)
);

-- 7. RAW_BRIDGE_CAMPAIGN_SEGMENT
CREATE OR REPLACE TABLE RAW_BRIDGE_CAMPAIGN_SEGMENT (
    campaign_id     VARCHAR(10)     NOT NULL,
    segment_id      VARCHAR(10)     NOT NULL,
    allocation_pct  NUMBER(5,1),
    PRIMARY KEY (campaign_id, segment_id)
);

-- 8. RAW_CAMPAIGN_METRICS
CREATE OR REPLACE TABLE RAW_CAMPAIGN_METRICS (
    metric_id       VARCHAR(12)     NOT NULL,
    campaign_id     VARCHAR(10)     NOT NULL,
    channel_id      VARCHAR(10)     NOT NULL,
    date            DATE            NOT NULL,
    impressions     INTEGER,
    clicks          INTEGER,
    conversions     INTEGER,
    spend_usd       NUMBER(12,2),
    revenue_usd     NUMBER(12,2),
    ctr             NUMBER(10,6),
    roas            NUMBER(10,4),
    cpc             NUMBER(10,2),
    conversion_rate NUMBER(10,6),
    PRIMARY KEY (metric_id)
);

-- 9. RAW_CUSTOMER_FEEDBACK
CREATE OR REPLACE TABLE RAW_CUSTOMER_FEEDBACK (
    feedback_id     VARCHAR(12)     NOT NULL,
    customer_id     VARCHAR(12)     NOT NULL,
    campaign_id     VARCHAR(10)     NOT NULL,
    feedback_date   DATE,
    sentiment_score NUMBER(6,4),
    rating          INTEGER,
    feedback_text   VARCHAR(500),
    feedback_channel VARCHAR(30),
    PRIMARY KEY (feedback_id)
);

-- 10. RAW_MARKET_EVENTS
CREATE OR REPLACE TABLE RAW_MARKET_EVENTS (
    event_id            VARCHAR(10)     NOT NULL,
    event_type          VARCHAR(30),
    event_name          VARCHAR(200),
    region              VARCHAR(50),
    start_date          DATE,
    end_date            DATE,
    impact_level        VARCHAR(20),
    description         VARCHAR(500),
    affected_industries VARCHAR(500),
    PRIMARY KEY (event_id)
);

-- 11. RAW_BRAND_GUIDELINES
CREATE OR REPLACE TABLE RAW_BRAND_GUIDELINES (
    guideline_id    VARCHAR(10)     NOT NULL,
    client_id       VARCHAR(10)     NOT NULL,
    section_title   VARCHAR(100),
    guideline_text  VARCHAR(5000),
    dos             VARCHAR(500),
    donts           VARCHAR(500),
    tone_keywords   VARCHAR(500),
    color_palette   VARCHAR(200),
    created_date    DATE,
    PRIMARY KEY (guideline_id)
);
