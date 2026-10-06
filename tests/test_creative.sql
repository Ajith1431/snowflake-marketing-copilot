-- ============================================================
-- test_creative.sql
-- Assertions for MARKETING_COPILOT.CREATIVE (creative intelligence + predictor).
-- Each test returns TEST_NAME, RESULT (PASS/FAIL), DETAIL.
-- Run: python scripts/run_sql_tests.py tests/test_creative.sql
-- ============================================================

USE WAREHOUSE MARKETING_WH;
USE SCHEMA MARKETING_COPILOT.CREATIVE;

-- C1: row counts
SELECT 'C1: row counts (600 ads, 4800 attributes, 42768 weekly, 3564 ad-weeks)' AS test_name,
       IFF((SELECT COUNT(*) FROM DIM_AD) = 600 AND (SELECT COUNT(*) FROM FACT_AD_ATTRIBUTE) = 4800
           AND (SELECT COUNT(*) FROM FACT_AD_WEEKLY) = 42768 AND (SELECT COUNT(*) FROM V_AD_FEATURES) = 3564,
           'PASS', 'FAIL') AS result,
       (SELECT COUNT(*) FROM DIM_AD) || ' / ' || (SELECT COUNT(*) FROM FACT_AD_ATTRIBUTE) || ' / '
         || (SELECT COUNT(*) FROM FACT_AD_WEEKLY) || ' / ' || (SELECT COUNT(*) FROM V_AD_FEATURES) AS detail;

-- C2: no NULL ad_ids anywhere
SELECT 'C2: no NULL ad_ids' AS test_name,
       IFF(n = 0, 'PASS', 'FAIL') AS result, n::VARCHAR AS detail
FROM (SELECT (SELECT COUNT_IF(ad_id IS NULL) FROM DIM_AD) + (SELECT COUNT_IF(ad_id IS NULL) FROM FACT_AD_ATTRIBUTE)
           + (SELECT COUNT_IF(ad_id IS NULL) FROM FACT_AD_WEEKLY) + (SELECT COUNT_IF(ad_id IS NULL) FROM MODEL_PREDICTIONS) AS n);

-- C3: funnel is monotonic (impressions >= clicks >= conversions; impressions >= views >= p100)
SELECT 'C3: funnel monotonic' AS test_name,
       IFF(COUNT(*) = 0, 'PASS', 'FAIL') AS result, COUNT(*)::VARCHAR || ' violating rows' AS detail
FROM FACT_AD_WEEKLY
WHERE clicks > impressions OR conversions > clicks OR video_views > impressions OR video_p100 > video_views;

-- C4: NET_LEAN classes are valid and every row has a class
SELECT 'C4: NET_LEAN classes valid' AS test_name,
       IFF(COUNT_IF(net_lean_class IS NULL OR net_lean_class NOT IN
           ('NET_HELPED', 'NET_HURT', 'MIXED', 'NEGLIGIBLE', 'INCONCLUSIVE', 'INSUFFICIENT_DATA')) = 0
           AND COUNT(*) > 0, 'PASS', 'FAIL') AS result,
       COUNT(*)::VARCHAR || ' rows' AS detail
FROM NET_LEAN;

-- C5: INSUFFICIENT_DATA is used exactly when n_ads_with < 30, and helped/hurt intervals exclude 0
SELECT 'C5: NET_LEAN class rules hold' AS test_name,
       IFF(COUNT_IF((n_ads_with < 30) <> (net_lean_class = 'INSUFFICIENT_DATA')) = 0
           AND COUNT_IF(net_lean_class = 'NET_HELPED' AND (adj_lift_pct <= 3 OR ci_low_pct <= 0)) = 0
           AND COUNT_IF(net_lean_class = 'NET_HURT' AND (adj_lift_pct >= -3 OR ci_high_pct >= 0)) = 0,
           'PASS', 'FAIL') AS result, '' AS detail
FROM NET_LEAN;

-- C12: reference coding: every row names a reference, no value is its own reference, binary families have one row
SELECT 'C12: NET_LEAN reference coding consistent' AS test_name,
       IFF(COUNT_IF(reference_value IS NULL OR reference_value = attribute_value) = 0
           AND (SELECT COUNT(*) FROM (SELECT stratum_type, market, objective, brand, attribute_family FROM NET_LEAN
                WHERE attribute_family IN ('has_person', 'has_logo_first_3s')
                GROUP BY ALL HAVING COUNT(*) <> 1)) = 0
           AND COUNT_IF(NOT reference_is_fallback AND attribute_family = 'hook_type' AND reference_value <> 'promo_led') = 0,
           'PASS', 'FAIL') AS result,
       COUNT_IF(reference_is_fallback)::VARCHAR || ' rows use a fallback reference' AS detail
FROM NET_LEAN;

-- C6: MODEL_METRICS has rows for baseline, ridge, hgb at both levels, and coverage rows
SELECT 'C6: MODEL_METRICS populated' AS test_name,
       IFF(COUNT_IF(model IN ('baseline', 'ridge', 'hgb')) = 6 AND COUNT_IF(p10_p90_coverage IS NOT NULL) >= 2,
           'PASS', 'FAIL') AS result, COUNT(*)::VARCHAR || ' rows' AS detail
FROM MODEL_METRICS;

-- C7: MODEL_PREDICTIONS covers every ad-week with ordered intervals
SELECT 'C7: MODEL_PREDICTIONS complete, p10 <= p90' AS test_name,
       IFF(COUNT(*) = 3564 AND COUNT_IF(p10_ctr > p90_ctr) = 0 AND COUNT_IF(split = 'HOLDOUT') > 0,
           'PASS', 'FAIL') AS result, COUNT(*)::VARCHAR || ' rows' AS detail
FROM MODEL_PREDICTIONS;

-- C8: SCORE_AD returns a non-null result with p10 <= predicted <= p90
CALL SCORE_AD(PARSE_JSON('{"brand":"Pepsi","market":"US","objective":"AWARENESS","placement":"reels","budget":1800,
                          "attributes":{"headline_tone":"playful","color_temp":"warm","has_logo_first_3s":"Y"}}'));
SELECT 'C8: SCORE_AD non-null and p10 <= predicted <= p90' AS test_name,
       IFF(r IS NOT NULL AND r:predicted_ctr IS NOT NULL
           AND r:p10::FLOAT <= r:predicted_ctr::FLOAT AND r:predicted_ctr::FLOAT <= r:p90::FLOAT
           AND ARRAY_SIZE(r:top_drivers) > 0, 'PASS', 'FAIL') AS result,
       'pred=' || r:predicted_ctr::VARCHAR || ' p10=' || r:p10::VARCHAR || ' p90=' || r:p90::VARCHAR AS detail
FROM (SELECT $1 AS r FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())));

-- C9: answer-key table is not readable by agent / MCP roles
SHOW GRANTS ON TABLE EFFECT_RECOVERY;
SELECT 'C9: EFFECT_RECOVERY has no grants beyond ownership' AS test_name,
       IFF(COUNT_IF("privilege" <> 'OWNERSHIP') = 0, 'PASS', 'FAIL') AS result,
       COUNT(*)::VARCHAR || ' grant rows' AS detail
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

-- C10: false-positive check exists and has a total row with a valid share
SELECT 'C10: NULL_EFFECT_CHECK total row present, share in [0,1]' AS test_name,
       IFF(COUNT(*) = 1 AND MIN(false_positive_share) BETWEEN 0 AND 1 AND MIN(n_strata_tested) > 0, 'PASS', 'FAIL') AS result,
       'rate=' || MIN(false_positive_share)::VARCHAR AS detail
FROM NULL_EFFECT_CHECK WHERE attribute_family = 'ALL';

-- C11: false-positive check (derived from the answer key) is not readable by agent / MCP roles
SHOW GRANTS ON TABLE NULL_EFFECT_CHECK;
SELECT 'C11: NULL_EFFECT_CHECK has no grants beyond ownership' AS test_name,
       IFF(COUNT_IF("privilege" <> 'OWNERSHIP') = 0, 'PASS', 'FAIL') AS result,
       COUNT(*)::VARCHAR || ' grant rows' AS detail
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

-- C13: model-level planted-effect check is populated
SELECT 'C13: MODEL_EFFECT_CHECK populated' AS test_name,
       IFF(COUNT(*) >= 20 AND COUNT_IF(direction_match IS NULL) = 0, 'PASS', 'FAIL') AS result,
       COUNT_IF(direction_match)::VARCHAR || '/' || COUNT(*)::VARCHAR || ' direction match' AS detail
FROM MODEL_EFFECT_CHECK;

-- C14: model-level check (derived from the answer key) is not readable by agent / MCP roles
SHOW GRANTS ON TABLE MODEL_EFFECT_CHECK;
SELECT 'C14: MODEL_EFFECT_CHECK has no grants beyond ownership' AS test_name,
       IFF(COUNT_IF("privilege" <> 'OWNERSHIP') = 0, 'PASS', 'FAIL') AS result,
       COUNT(*)::VARCHAR || ' grant rows' AS detail
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
