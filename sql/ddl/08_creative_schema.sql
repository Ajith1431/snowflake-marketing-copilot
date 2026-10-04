-- ============================================================
-- 08_creative_schema.sql
-- Creative-attribute analytics schema (synthetic, planted effects)
-- Data: data/generators/generate_creative.py -> data/samples/creative/
-- Load: python scripts/load_creative.py
-- Ground truth (ground_truth_effects.json) is intentionally NOT loaded into Snowflake.
-- ============================================================

USE WAREHOUSE MARKETING_WH;
USE DATABASE MARKETING_COPILOT;

CREATE SCHEMA IF NOT EXISTS MARKETING_COPILOT.CREATIVE
  COMMENT = 'Ad-level creative attributes and weekly delivery (synthetic, planted effects)';

USE SCHEMA MARKETING_COPILOT.CREATIVE;

CREATE STAGE IF NOT EXISTS CREATIVE_STAGE
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);

-- One row per ad
CREATE OR REPLACE TABLE DIM_AD (
    ad_id         VARCHAR(10) NOT NULL,
    brand         VARCHAR(20) NOT NULL,   -- Nike, Pepsi, Samsung
    market        VARCHAR(5)  NOT NULL,   -- UAE, KSA, UK, US, IN
    objective     VARCHAR(20) NOT NULL,   -- AWARENESS, LINK_CLICKS, LEADS
    ad_type       VARCHAR(10) NOT NULL,   -- video, image
    aspect_ratio  VARCHAR(5)  NOT NULL,   -- 9:16, 4:5, 1:1
    platform      VARCHAR(20) NOT NULL,   -- instagram, facebook
    placement     VARCHAR(10) NOT NULL,   -- feed, reels, stories
    start_week    DATE        NOT NULL,   -- Monday of first live week
    PRIMARY KEY (ad_id)
);

-- Long format: 8 families per ad
CREATE OR REPLACE TABLE FACT_AD_ATTRIBUTE (
    ad_id             VARCHAR(10) NOT NULL,
    attribute_family  VARCHAR(30) NOT NULL,  -- hook_type, headline_tone, cta_tone, background,
                                             -- color_temp, has_person, word_count_group, has_logo_first_3s
    value             VARCHAR(30) NOT NULL,
    PRIMARY KEY (ad_id, attribute_family)
);

-- Grain: ad x week x age_group x gender
CREATE OR REPLACE TABLE FACT_AD_WEEKLY (
    ad_id        VARCHAR(10)   NOT NULL,
    week         DATE          NOT NULL,
    age_group    VARCHAR(5)    NOT NULL,  -- 18-24, 25-34, 35-44, 45-54, 55-64, 65+
    gender       VARCHAR(1)    NOT NULL,  -- F, M
    impressions  NUMBER(12,0)  NOT NULL,
    clicks       NUMBER(12,0)  NOT NULL,
    video_views  NUMBER(12,0)  NOT NULL,  -- 0 for image ads
    video_p100   NUMBER(12,0)  NOT NULL,
    spend        NUMBER(12,2)  NOT NULL,
    conversions  NUMBER(12,0)  NOT NULL,
    revenue      NUMBER(14,2)  NOT NULL,  -- conversions x brand order value
    frequency    NUMBER(6,2)   NOT NULL,
    PRIMARY KEY (ad_id, week, age_group, gender)
);
