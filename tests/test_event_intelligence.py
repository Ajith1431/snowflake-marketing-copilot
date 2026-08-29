"""
End-to-end test: run intelligence, load to Snowflake, verify counts.
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "intelligence"))

from intelligence_orchestrator import run_full_intelligence
from snowflake_loader import load_intelligence_run
from config import EVENT_REGISTRY_API_KEY

import snowflake.connector


def main():
    print("=" * 60)
    print("END-TO-END EVENT INTELLIGENCE TEST")
    print("=" * 60)

    # Step 1: Run intelligence
    print("\n[Step 1] Running intelligence collection...")
    result = run_full_intelligence(
        client_name="UrbanThread",
        event_name="FIFA World Cup 2026",
        event_keywords=["FIFA 2026", "World Cup 2026", "football shoes",
                        "Nike FIFA", "Adidas World Cup"],
        competitors=["Nike", "Adidas", "Puma"],
        markets=["US", "GB"],
        news_api_key=EVENT_REGISTRY_API_KEY,
    )

    # Step 2: Connect to Snowflake and load
    print("\n[Step 2] Connecting to Snowflake...")
    conn = snowflake.connector.connect(connection_name="wfvamnp-ap54607")
    cur = conn.cursor()
    cur.execute("USE ROLE ACCOUNTADMIN")
    cur.execute("USE WAREHOUSE MARKETING_WH")
    cur.execute("USE DATABASE MARKETING_COPILOT")

    # Create a simple session wrapper that has a .sql().collect() interface
    class SessionWrapper:
        def __init__(self, cursor):
            self._cursor = cursor
        def sql(self, query):
            return QueryResult(self._cursor, query)

    class QueryResult:
        def __init__(self, cursor, query):
            self._cursor = cursor
            self._query = query
        def collect(self):
            self._cursor.execute(self._query)
            return self._cursor.fetchall()

    session = SessionWrapper(cur)

    print("\n[Step 3] Loading to Snowflake...")
    load_result = load_intelligence_run(session, result)
    print(f"\nLoad result: {load_result}")

    # Step 3: Wait for dynamic tables
    print("\n[Step 4] Waiting 90 seconds for dynamic tables to refresh...")
    time.sleep(90)

    # Step 4: Verify counts
    print("\n[Step 5] Verifying row counts...")
    tables = [
        ("RAW", "EVENT_INTELLIGENCE_RUNS"),
        ("RAW", "GOOGLE_TRENDS_DATA"),
        ("RAW", "NEWS_ARTICLES"),
        ("RAW", "WEB_INTELLIGENCE"),
        ("ANALYTICS", "DIM_EVENT_TRENDS"),
        ("ANALYTICS", "DIM_NEWS_SENTIMENT"),
        ("ANALYTICS", "DIM_COMPETITOR_PRESENCE"),
    ]

    print(f"\n{'Table':<45} | {'Rows':>6}")
    print("-" * 55)
    all_ok = True
    for schema, table in tables:
        cur.execute(f"SELECT COUNT(*) FROM MARKETING_COPILOT.{schema}.{table}")
        count = cur.fetchone()[0]
        status = "OK" if count > 0 else "EMPTY"
        if count == 0:
            all_ok = False
        print(f"{schema}.{table:<40} | {count:>6} {status}")

    print("-" * 55)
    print(f"Overall: {'ALL TABLES POPULATED' if all_ok else 'SOME TABLES EMPTY (dynamic tables may still be refreshing)'}")

    cur.close()
    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
