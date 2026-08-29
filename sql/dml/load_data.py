"""
Upload CSVs to Snowflake internal stage and COPY INTO RAW tables.
Uses snowflake-connector-python for PUT commands (not available via SQL worksheet).
"""
import os
import snowflake.connector
from pathlib import Path

CSV_DIR = Path(r"c:\Users\majithkumar\SnowflakeHackathon\data\samples")

TABLE_MAP = {
    "clients.csv": "RAW_CLIENTS",
    "products.csv": "RAW_PRODUCTS",
    "channels.csv": "RAW_CHANNELS",
    "audience_segments.csv": "RAW_AUDIENCE_SEGMENTS",
    "customer_profiles.csv": "RAW_CUSTOMER_PROFILES",
    "campaigns.csv": "RAW_CAMPAIGNS",
    "bridge_campaign_segment.csv": "RAW_BRIDGE_CAMPAIGN_SEGMENT",
    "campaign_metrics.csv": "RAW_CAMPAIGN_METRICS",
    "customer_feedback.csv": "RAW_CUSTOMER_FEEDBACK",
    "market_events.csv": "RAW_MARKET_EVENTS",
    "brand_guidelines.csv": "RAW_BRAND_GUIDELINES",
}

def main():
    conn = snowflake.connector.connect(
        connection_name="wfvamnp-ap54607",
    )
    cur = conn.cursor()

    cur.execute("USE ROLE ACCOUNTADMIN")
    cur.execute("USE WAREHOUSE MARKETING_WH")
    cur.execute("USE DATABASE MARKETING_COPILOT")
    cur.execute("USE SCHEMA RAW")

    for csv_file, table_name in TABLE_MAP.items():
        csv_path = CSV_DIR / csv_file
        stage_folder = csv_file.replace(".csv", "")
        stage_path = f"@MARKETING_STAGE/{stage_folder}/"

        print(f"\n{'='*50}")
        print(f"Processing: {csv_file} -> {table_name}")

        # PUT file to stage
        put_sql = f"PUT 'file://{csv_path.as_posix()}' {stage_path} AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
        print(f"  PUT: {put_sql[:80]}...")
        cur.execute(put_sql)
        put_result = cur.fetchall()
        for row in put_result:
            print(f"  PUT result: {row}")

        # COPY INTO table
        copy_sql = f"""
        COPY INTO {table_name} FROM {stage_path}
        FILE_FORMAT = (TYPE='CSV' FIELD_OPTIONALLY_ENCLOSED_BY='"' SKIP_HEADER=1)
        ON_ERROR = 'CONTINUE'
        """
        print(f"  COPY INTO {table_name}...")
        cur.execute(copy_sql)
        copy_result = cur.fetchall()
        for row in copy_result:
            print(f"  COPY result: {row}")

    # Verify row counts
    print(f"\n{'='*50}")
    print("ROW COUNT VERIFICATION")
    print(f"{'='*50}")
    for csv_file, table_name in TABLE_MAP.items():
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cur.fetchone()[0]
        print(f"  {table_name:<35s} {count:>8,d} rows")

    cur.close()
    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
