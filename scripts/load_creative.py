"""
Load the synthetic creative dataset into MARKETING_COPILOT.CREATIVE.

Usage:
    python data/generators/generate_creative.py   # writes data/samples/creative/*.csv
    python scripts/load_creative.py               # DDL + PUT + COPY INTO + checks

Connection: SNOWFLAKE_CONNECTION env var / .env (name in ~/.snowflake/connections.toml).
"""

import os
import sys
from pathlib import Path

import snowflake.connector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from env_keys import get_secret  # noqa: E402

DATA = ROOT / "data" / "samples" / "creative"
SCHEMA = "MARKETING_COPILOT.CREATIVE"
TABLES = {"DIM_AD": "dim_ad.csv", "FACT_AD_ATTRIBUTE": "fact_ad_attribute.csv", "FACT_AD_WEEKLY": "fact_ad_weekly.csv"}

RECONCILE_SQL = f"""
SELECT
  (SELECT COUNT(*) FROM {SCHEMA}.FACT_AD_WEEKLY WHERE clicks > impressions)                    AS clicks_gt_impr,
  (SELECT COUNT(*) FROM {SCHEMA}.FACT_AD_WEEKLY WHERE video_p100 > video_views
                                                   OR video_views > impressions)              AS video_funnel_breaks,
  (SELECT COUNT(*) FROM {SCHEMA}.FACT_AD_WEEKLY WHERE conversions > clicks)                    AS conv_gt_clicks,
  (SELECT COUNT(*) FROM (SELECT ad_id, week FROM {SCHEMA}.FACT_AD_WEEKLY
                         GROUP BY 1, 2 HAVING COUNT(*) <> 12))                                 AS ad_weeks_missing_cells,
  (SELECT COUNT(*) FROM {SCHEMA}.FACT_AD_WEEKLY w LEFT JOIN {SCHEMA}.DIM_AD d USING (ad_id)
    WHERE d.ad_id IS NULL)                                                                     AS orphan_weekly_rows,
  (SELECT COUNT(*) FROM (SELECT ad_id FROM {SCHEMA}.FACT_AD_ATTRIBUTE
                         GROUP BY 1 HAVING COUNT(DISTINCT attribute_family) <> 8))             AS ads_missing_families,
  (SELECT COUNT(*) FROM {SCHEMA}.DIM_AD d
    JOIN (SELECT ad_id, MIN(week) w FROM {SCHEMA}.FACT_AD_WEEKLY GROUP BY 1) f USING (ad_id)
    WHERE f.w <> d.start_week)                                                                 AS start_week_mismatch
"""

SANITY_SQL = f"""
WITH ad_totals AS (
    SELECT ad_id, SUM(clicks) AS clicks, SUM(impressions) AS impressions
    FROM {SCHEMA}.FACT_AD_WEEKLY GROUP BY ad_id
),
per_value AS (
    SELECT v.attribute_family, v.value,
           COUNT(DISTINCT IFF(a.value = v.value, a.ad_id, NULL))                         AS ads_with,
           SUM(IFF(a.value = v.value, t.clicks, 0))
             / NULLIF(SUM(IFF(a.value = v.value, t.impressions, 0)), 0)                  AS ctr_with,
           SUM(IFF(a.value <> v.value, t.clicks, 0))
             / NULLIF(SUM(IFF(a.value <> v.value, t.impressions, 0)), 0)                 AS ctr_without
    FROM (SELECT DISTINCT attribute_family, value FROM {SCHEMA}.FACT_AD_ATTRIBUTE) v
    JOIN {SCHEMA}.FACT_AD_ATTRIBUTE a ON a.attribute_family = v.attribute_family
    JOIN ad_totals t ON t.ad_id = a.ad_id
    GROUP BY v.attribute_family, v.value
)
SELECT attribute_family, value, ads_with,
       ROUND(ctr_with * 100, 3)                                  AS ctr_with_pct,
       ROUND(ctr_without * 100, 3)                               AS ctr_without_pct,
       ROUND((ctr_with / NULLIF(ctr_without, 0) - 1) * 100, 1)   AS lift_pct
FROM per_value
ORDER BY attribute_family, value
"""


def run(cur, sql):
    cur.execute(sql)
    return cur.fetchall(), [c[0] for c in cur.description]


def print_table(rows, cols):
    widths = [max(len(str(c)), *(len(str(r[i])) for r in rows)) for i, c in enumerate(cols)]
    print("  " + "  ".join(str(c).ljust(w) for c, w in zip(cols, widths)))
    for r in rows:
        print("  " + "  ".join(str(v).ljust(w) for v, w in zip(r, widths)))


def main():
    for f in TABLES.values():
        if not (DATA / f).exists():
            raise SystemExit(f"Missing {DATA / f}. Run: python data/generators/generate_creative.py")

    connection = os.environ.get("SNOWFLAKE_CONNECTION") or get_secret("SNOWFLAKE_CONNECTION", required=False) or None
    conn = snowflake.connector.connect(connection_name=connection) if connection else snowflake.connector.connect()
    cur = conn.cursor()
    try:
        rows, cols = run(cur, "SHOW WAREHOUSES LIKE 'MARKETING_WH'")
        size = rows[0][cols.index("size")]
        print(f"Warehouse MARKETING_WH size: {size}")
        if size.upper().replace("-", "") != "XSMALL":
            raise SystemExit("MARKETING_WH is not XSMALL; refusing to load. Resize it back to XSMALL first.")

        for _ in conn.execute_string((ROOT / "sql/ddl/08_creative_schema.sql").read_text(encoding="utf-8"),
                                     remove_comments=True):
            pass
        print("DDL: sql/ddl/08_creative_schema.sql applied")

        print("\nLoad (PUT + COPY INTO):")
        for table, file in TABLES.items():
            path = (DATA / file).as_posix()
            sub = file.removesuffix(".csv")
            cur.execute(f"PUT 'file://{path}' @{SCHEMA}.CREATIVE_STAGE/{sub}/ AUTO_COMPRESS=TRUE OVERWRITE=TRUE")
            cur.execute(f"COPY INTO {SCHEMA}.{table} FROM @{SCHEMA}.CREATIVE_STAGE/{sub}/ "
                        f"ON_ERROR = 'ABORT_STATEMENT' FORCE = TRUE")
            local_rows = sum(1 for _ in open(DATA / file, encoding="utf-8")) - 1
            loaded = run(cur, f"SELECT COUNT(*) FROM {SCHEMA}.{table}")[0][0][0]
            status = "OK" if loaded == local_rows else "MISMATCH"
            print(f"  {table:<18} {loaded:>7} rows (csv {local_rows:>7})  {status}")

        print("\nReconciliation (all should be 0):")
        rows, cols = run(cur, RECONCILE_SQL)
        print_table(rows, cols)

        print("\nSanity: ad-level CTR with vs without each attribute value (naive, unadjusted):")
        rows, cols = run(cur, SANITY_SQL)
        print_table(rows, cols)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
