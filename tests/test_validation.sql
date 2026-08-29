-- ============================================================
-- test_validation.sql
-- Data quality assertions for Marketing Co-Pilot
-- Run all assertions and report PASS/FAIL for each
-- ============================================================

USE WAREHOUSE MARKETING_WH;
USE DATABASE MARKETING_COPILOT;

-- Assertion 1: No NULL client_ids in any fact table
SELECT 'T1: No NULL client_ids in fact tables' AS test_name,
    CASE WHEN
        (SELECT COUNT(*) FROM ANALYTICS.FACT_CAMPAIGN WHERE client_id IS NULL) +
        (SELECT COUNT(*) FROM ANALYTICS.FACT_CAMPAIGN_METRICS WHERE client_id IS NULL) +
        (SELECT COUNT(*) FROM ANALYTICS.FACT_CUSTOMER_FEEDBACK WHERE client_id IS NULL) +
        (SELECT COUNT(*) FROM ANALYTICS.FACT_BRAND_GUIDELINES WHERE client_id IS NULL) = 0
    THEN 'PASS' ELSE 'FAIL' END AS result,
    (SELECT COUNT(*) FROM ANALYTICS.FACT_CAMPAIGN WHERE client_id IS NULL) +
    (SELECT COUNT(*) FROM ANALYTICS.FACT_CAMPAIGN_METRICS WHERE client_id IS NULL) +
    (SELECT COUNT(*) FROM ANALYTICS.FACT_CUSTOMER_FEEDBACK WHERE client_id IS NULL) +
    (SELECT COUNT(*) FROM ANALYTICS.FACT_BRAND_GUIDELINES WHERE client_id IS NULL) AS null_count;

-- Assertion 2: All ROAS values > 0
SELECT 'T2: All ROAS values > 0' AS test_name,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS result,
    COUNT(*) AS violations
FROM ANALYTICS.FACT_CAMPAIGN_METRICS
WHERE roas <= 0 OR roas IS NULL;

-- Assertion 3: All spend values > 0
SELECT 'T3: All spend values > 0' AS test_name,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS result,
    COUNT(*) AS violations
FROM ANALYTICS.FACT_CAMPAIGN_METRICS
WHERE spend_usd <= 0 OR spend_usd IS NULL;

-- Assertion 4: Campaign end_date > start_date
SELECT 'T4: end_date > start_date for all campaigns' AS test_name,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS result,
    COUNT(*) AS violations
FROM ANALYTICS.FACT_CAMPAIGN
WHERE end_date <= start_date;

-- Assertion 5: sentiment_score between -1.0 and 1.0
SELECT 'T5: sentiment_score in [-1.0, 1.0]' AS test_name,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS result,
    COUNT(*) AS violations
FROM ANALYTICS.FACT_CUSTOMER_FEEDBACK
WHERE sentiment_score < -1.0 OR sentiment_score > 1.0;

-- Assertion 6: allocation_pct sums to 100 per campaign
SELECT 'T6: allocation_pct sums to 100 per campaign' AS test_name,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS result,
    COUNT(*) AS violations
FROM (
    SELECT campaign_id, ROUND(SUM(allocation_pct), 1) AS total_pct
    FROM RAW.RAW_BRIDGE_CAMPAIGN_SEGMENT
    GROUP BY campaign_id
    HAVING ROUND(SUM(allocation_pct), 1) != 100.0
);

-- Assertion 7: Cortex Search returns results for brand guidelines query
SELECT 'T7: Cortex Search BRAND_SEARCH returns results' AS test_name,
    CASE WHEN ARRAY_SIZE(PARSE_JSON(
        SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
            'MARKETING_COPILOT.SEMANTIC.BRAND_SEARCH',
            '{"query": "brand guidelines tone of voice", "columns": ["client_name", "section_title"], "limit": 1}'
        )
    ):results) > 0 THEN 'PASS' ELSE 'FAIL' END AS result;

-- Assertion 8: Cortex Analyst semantic view is queryable
SELECT 'T8: Semantic view CAMPAIGN_ANALYTICS is queryable' AS test_name,
    CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END AS result,
    COUNT(*) AS row_count
FROM SEMANTIC_VIEW(
    MARKETING_COPILOT.SEMANTIC.CAMPAIGN_ANALYTICS
    METRICS total_spend
    DIMENSIONS fact_campaign_metrics.client_name
);
