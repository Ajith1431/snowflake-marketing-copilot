-- ============================================================
-- 02_reduce_clients.sql
-- Reduce the generated 12-client dataset to the three brands used everywhere in the app:
--   C010 UrbanThread -> Nike, C009 FlavorCo -> Pepsi, C002 TechVista -> Samsung.
-- Deletes the other 9 clients and all their dependent rows (children first), then renames the
-- kept clients in every text column that carries the name, then trims each brand to three products
-- (surplus products collapse onto the nearest kept product_id). Idempotent; runs after 01_load_data.sql.
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

-- Products: three per brand, no prefixes. old_id -> kept id (surplus ids collapse onto the nearest kept one)
UPDATE RAW_CAMPAIGNS c SET product_id = m.new_id
FROM (SELECT * FROM VALUES ('P0044','P0043'), ('P0041','P0040'), ('P0039','P0038'), ('P0007','P0005'), ('P0008','P0005')) m(old_id, new_id)
WHERE c.product_id = m.old_id;
DELETE FROM RAW_PRODUCTS WHERE product_id IN ('P0044', 'P0041', 'P0039', 'P0007', 'P0008');
UPDATE RAW_PRODUCTS p SET product_name = v.n, category = v.cat, price_tier = v.tier, launch_date = v.ld::DATE, description = v.d
FROM (SELECT * FROM VALUES
    ('P0043', 'Running Collection',  'Running',               'premium', '2025-06-03', 'Performance running shoes and apparel for road and track.'),
    ('P0042', 'Training Apparel',    'Apparel',               'mid',     '2025-05-17', 'Gym and training wear built for movement and sweat.'),
    ('P0040', 'Lifestyle Sneakers',  'Footwear',              'premium', '2024-11-19', 'Everyday sneakers inspired by sport heritage.'),
    ('P0036', 'Zero Sugar Cola',     'Cola',                  'budget',  '2025-11-20', 'Full cola taste with zero sugar.'),
    ('P0037', 'Sparkling Citrus',    'Sparkling Soft Drinks', 'budget',  '2023-12-08', 'Light, sparkling citrus soft drink.'),
    ('P0038', 'Energy Drink',        'Energy Drinks',         'mid',     '2024-01-30', 'Caffeinated energy drink for an on-the-go lift.'),
    ('P0005', 'Flagship Smartphone', 'Smartphones',           'premium', '2024-10-16', 'Top-of-range smartphone with pro camera and AI features.'),
    ('P0006', 'Smart TV',            'Televisions',           'premium', '2025-01-13', 'Large-screen smart TV with streaming built in.'),
    ('P0009', 'Wearables',           'Wearables',             'mid',     '2025-01-23', 'Smartwatches and earbuds that connect to the phone.')) v(id, n, cat, tier, ld, d)
WHERE p.product_id = v.id;
UPDATE RAW_CUSTOMER_FEEDBACK SET feedback_text =
    REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(feedback_text,
      'UT-EcoThread', 'Running Collection'), 'UT-Essentials', 'Running Collection'), 'UT-ActiveWear', 'Training Apparel'),
      'UT-StreetStyle', 'Lifestyle Sneakers'), 'UT-LuxeLine', 'Lifestyle Sneakers'), 'FC-CraftBrew', 'Zero Sugar Cola'),
      'FC-OrganicBites', 'Sparkling Citrus'), 'FC-SnackAttack', 'Energy Drink'), 'FC-MealPrep Pro', 'Energy Drink'),
      'TV-CloudSync Pro', 'Flagship Smartphone'), 'TV-SecureNet', 'Flagship Smartphone'), 'TV-DevKit Starter', 'Flagship Smartphone'),
      'TV-DataVault', 'Smart TV'), 'TV-AI Insights', 'Wearables');

-- Nike is a sportswear brand: industry and guideline wording (one-word swap, meaning unchanged)
UPDATE RAW_CLIENTS SET industry = 'Sportswear' WHERE client_id = 'C010';
UPDATE RAW_BRAND_GUIDELINES SET
    section_title  = REPLACE(REPLACE(section_title,  'fashion', 'sportswear'), 'Fashion', 'Sportswear'),
    guideline_text = REPLACE(REPLACE(guideline_text, 'fashion', 'sportswear'), 'Fashion', 'Sportswear'),
    dos            = REPLACE(REPLACE(dos,            'fashion', 'sportswear'), 'Fashion', 'Sportswear'),
    donts          = REPLACE(REPLACE(donts,          'fashion', 'sportswear'), 'Fashion', 'Sportswear'),
    tone_keywords  = REPLACE(REPLACE(tone_keywords,  'fashion', 'sportswear'), 'Fashion', 'Sportswear')
WHERE client_id = 'C010';
