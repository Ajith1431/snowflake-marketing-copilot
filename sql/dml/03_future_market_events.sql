-- ============================================================
-- 03_future_market_events.sql
-- Adds a forward planning calendar (Nov 2026 - Dec 2027) to RAW_MARKET_EVENTS so agents have
-- upcoming events; the generated 2023-2025 rows stay as past events. Dates are calendar facts or
-- published schedules; movable festivals are approximate and labelled as such. Idempotent.
-- ============================================================

USE DATABASE MARKETING_COPILOT;
USE SCHEMA RAW;

DELETE FROM RAW_MARKET_EVENTS WHERE start_date >= '2026-11-01';

INSERT INTO RAW_MARKET_EVENTS (event_id, event_type, event_name, region, start_date, end_date, impact_level, description, affected_industries)
SELECT * FROM VALUES
 ('EV054', 'holiday',  'Singles Day 2026',            'Asia Pacific',  '2026-11-11'::DATE, '2026-11-11'::DATE, 'high',   'Largest online shopping day in China and much of Asia; heavy discounting on electronics and apparel.', 'Technology,Sportswear,Retail'),
 ('EV055', 'holiday',  'Black Friday 2026',           'North America', '2026-11-27'::DATE, '2026-11-27'::DATE, 'high',   'Day after US Thanksgiving; peak retail discount day across electronics, apparel and beverages.', 'Technology,Sportswear,Food & Beverage,Retail'),
 ('EV056', 'holiday',  'Cyber Monday 2026',           'North America', '2026-11-30'::DATE, '2026-11-30'::DATE, 'high',   'Online follow-up to Black Friday; strongest e-commerce day for consumer electronics.', 'Technology,Retail'),
 ('EV057', 'holiday',  'Holiday Season 2026',         'Global',        '2026-12-01'::DATE, '2026-12-31'::DATE, 'high',   'Gifting season with high consumer spend and media costs.', 'Technology,Sportswear,Food & Beverage,Retail'),
 ('EV058', 'holiday',  'New Year 2027',               'Global',        '2027-01-01'::DATE, '2027-01-02'::DATE, 'medium', 'New Year resolutions drive fitness, health and self-improvement spending.', 'Sportswear,Food & Beverage'),
 ('EV059', 'holiday',  'Ramadan 2027 (approximate)',  'Middle East & Africa', '2027-02-08'::DATE, '2027-03-09'::DATE, 'high', 'Month-long observance; dates depend on moon sighting. Evening consumption and family gatherings rise.', 'Food & Beverage,Retail,Sportswear'),
 ('EV060', 'holiday',  'Valentines Day 2027',         'Global',        '2027-02-14'::DATE, '2027-02-14'::DATE, 'medium', 'Gifting moment for wearables, apparel and treats.', 'Technology,Sportswear,Food & Beverage'),
 ('EV061', 'cultural', 'Earth Day 2027',              'Global',        '2027-04-22'::DATE, '2027-04-22'::DATE, 'medium', 'Sustainability-focused marketing moment.', 'Sportswear,Food & Beverage,Technology'),
 ('EV062', 'holiday',  'Mothers Day 2027 (US)',       'North America', '2027-05-09'::DATE, '2027-05-09'::DATE, 'medium', 'Second Sunday of May in the US; gifting for devices, wearables and apparel.', 'Technology,Sportswear'),
 ('EV063', 'cultural', 'FIFA Womens World Cup 2027',  'Global',        '2027-06-24'::DATE, '2027-07-25'::DATE, 'high',   'Tournament hosted by Brazil; major moment for football sponsorship and sportswear.', 'Sportswear,Food & Beverage,Technology'),
 ('EV064', 'holiday',  'Back to School 2027',         'North America', '2027-08-01'::DATE, '2027-09-10'::DATE, 'high',   'Seasonal spend on laptops, phones, footwear and apparel.', 'Technology,Sportswear,Retail'),
 ('EV065', 'holiday',  'Diwali 2027 (approximate)',   'Asia Pacific',  '2027-10-29'::DATE, '2027-10-29'::DATE, 'high',   'Festival of lights; peak gifting and electronics purchases in India. Date follows the lunar calendar.', 'Technology,Food & Beverage,Retail'),
 ('EV066', 'holiday',  'Black Friday 2027',           'North America', '2027-11-26'::DATE, '2027-11-26'::DATE, 'high',   'Day after US Thanksgiving; peak retail discount day.', 'Technology,Sportswear,Food & Beverage,Retail'),
 ('EV067', 'holiday',  'Holiday Season 2027',         'Global',        '2027-12-01'::DATE, '2027-12-31'::DATE, 'high',   'Gifting season with high consumer spend and media costs.', 'Technology,Sportswear,Food & Beverage,Retail');
