-- ============================================================
-- 09_creative_features.sql
-- One row per ad-week with rates computed from sums, plus all attributes.
-- ============================================================

USE WAREHOUSE MARKETING_WH;
USE SCHEMA MARKETING_COPILOT.CREATIVE;

CREATE OR REPLACE VIEW V_AD_FEATURES
  COMMENT = 'Ad-week features (synthetic data). Rates are ratios of sums; frequency is impression-weighted.'
AS
WITH wk AS (
    SELECT ad_id, week,
           SUM(impressions) AS impressions, SUM(clicks) AS clicks,
           SUM(video_views) AS video_views, SUM(video_p100) AS video_p100,
           SUM(conversions) AS conversions, SUM(spend) AS spend, SUM(revenue) AS revenue,
           SUM(frequency * impressions) / NULLIF(SUM(impressions), 0) AS frequency
    FROM FACT_AD_WEEKLY
    GROUP BY ad_id, week
),
attr AS (
    SELECT * FROM FACT_AD_ATTRIBUTE
    PIVOT (MAX(value) FOR attribute_family IN ('hook_type', 'headline_tone', 'cta_tone', 'background',
                                               'color_temp', 'has_person', 'word_count_group', 'has_logo_first_3s'))
      AS p (ad_id, hook_type, headline_tone, cta_tone, background, color_temp, has_person,
            word_count_group, has_logo_first_3s)
)
SELECT
    w.ad_id, w.week,
    d.brand, d.market, d.objective, d.placement, d.ad_type, d.aspect_ratio, d.platform,
    a.hook_type, a.headline_tone, a.cta_tone, a.background, a.color_temp, a.has_person,
    a.word_count_group, a.has_logo_first_3s,
    w.impressions, w.clicks, w.video_views, w.video_p100, w.conversions, w.spend, w.revenue,
    w.clicks / NULLIF(w.impressions, 0)                                   AS ctr,
    IFF(d.ad_type = 'video', w.video_views / NULLIF(w.impressions, 0), NULL) AS vtr,
    IFF(d.ad_type = 'video', w.video_p100 / NULLIF(w.video_views, 0), NULL)  AS completion_rate,
    w.conversions / NULLIF(w.clicks, 0)                                   AS conversion_rate,
    w.spend / NULLIF(w.impressions, 0) * 1000                             AS cpm,
    w.frequency,
    LN(NULLIF(w.spend, 0))                                                AS log_spend,
    DATEDIFF('week', d.start_week, w.week)                                AS weeks_since_start
FROM wk w
JOIN DIM_AD d USING (ad_id)
JOIN attr a USING (ad_id);
