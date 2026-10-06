-- ============================================================
-- 02_reduce_clients.sql
-- Reduce the generated 12-client dataset to the three brands used everywhere in the app:
--   C010 UrbanThread -> Nike, C009 FlavorCo -> Pepsi, C002 TechVista -> Samsung.
-- Deletes the other 9 clients and all their dependent rows (children first), then renames the
-- kept clients in every text column that carries the name. Idempotent; runs after 01_load_data.sql.
-- ============================================================

USE DATABASE MARKETING_COPILOT;
USE SCHEMA RAW;

DELETE FROM RAW_CAMPAIGN_METRICS WHERE campaign_id IN (SELECT campaign_id FROM RAW_CAMPAIGNS WHERE client_id NOT IN ('C002', 'C009', 'C010'));
DELETE FROM RAW_CUSTOMER_FEEDBACK WHERE campaign_id IN (SELECT campaign_id FROM RAW_CAMPAIGNS WHERE client_id NOT IN ('C002', 'C009', 'C010'));
DELETE FROM RAW_BRIDGE_CAMPAIGN_SEGMENT WHERE campaign_id IN (SELECT campaign_id FROM RAW_CAMPAIGNS WHERE client_id NOT IN ('C002', 'C009', 'C010'));
DELETE FROM RAW_CAMPAIGNS WHERE client_id NOT IN ('C002', 'C009', 'C010');
DELETE FROM RAW_CUSTOMER_PROFILES WHERE client_id NOT IN ('C002', 'C009', 'C010');
DELETE FROM RAW_AUDIENCE_SEGMENTS WHERE client_id NOT IN ('C002', 'C009', 'C010');
DELETE FROM RAW_PRODUCTS WHERE client_id NOT IN ('C002', 'C009', 'C010');
DELETE FROM RAW_BRAND_GUIDELINES WHERE client_id NOT IN ('C002', 'C009', 'C010');
DELETE FROM RAW_CLIENTS WHERE client_id NOT IN ('C002', 'C009', 'C010');

UPDATE RAW_CLIENTS SET client_name = CASE client_id WHEN 'C010' THEN 'Nike' WHEN 'C009' THEN 'Pepsi' WHEN 'C002' THEN 'Samsung' END;
UPDATE RAW_CAMPAIGNS SET campaign_name = REPLACE(REPLACE(REPLACE(campaign_name, 'UrbanThread', 'Nike'), 'FlavorCo', 'Pepsi'), 'TechVista', 'Samsung');
UPDATE RAW_BRAND_GUIDELINES SET
    section_title  = REPLACE(REPLACE(REPLACE(section_title,  'UrbanThread', 'Nike'), 'FlavorCo', 'Pepsi'), 'TechVista', 'Samsung'),
    guideline_text = REPLACE(REPLACE(REPLACE(guideline_text, 'UrbanThread', 'Nike'), 'FlavorCo', 'Pepsi'), 'TechVista', 'Samsung'),
    dos            = REPLACE(REPLACE(REPLACE(dos,            'UrbanThread', 'Nike'), 'FlavorCo', 'Pepsi'), 'TechVista', 'Samsung'),
    donts          = REPLACE(REPLACE(REPLACE(donts,          'UrbanThread', 'Nike'), 'FlavorCo', 'Pepsi'), 'TechVista', 'Samsung'),
    tone_keywords  = REPLACE(REPLACE(REPLACE(tone_keywords,  'UrbanThread', 'Nike'), 'FlavorCo', 'Pepsi'), 'TechVista', 'Samsung'),
    color_palette  = REPLACE(REPLACE(REPLACE(color_palette,  'UrbanThread', 'Nike'), 'FlavorCo', 'Pepsi'), 'TechVista', 'Samsung');
