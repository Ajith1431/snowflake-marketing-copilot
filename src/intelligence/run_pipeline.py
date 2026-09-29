"""
Run the full Event Intelligence pipeline and load results into Snowflake.
Usage: python src/intelligence/run_pipeline.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import snowflake.connector

from config import EVENT_REGISTRY_API_KEY, SNOWFLAKE_CONNECTION
from intelligence_orchestrator import run_full_intelligence
from snowflake_loader import load_intelligence_run

RUNS = [
    {
        "client_name": "UrbanThread",
        "event_name": "FIFA World Cup 2026",
        "event_keywords": ["FIFA 2026", "World Cup 2026", "football shoes", "Nike FIFA", "Adidas World Cup"],
        "competitors": ["Nike", "Adidas", "Puma"],
        "markets": ["US", "GB"],
    },
    {
        "client_name": "LuminaRetail",
        "event_name": "Black Friday 2026",
        "event_keywords": ["Black Friday 2026", "Black Friday deals", "Cyber Monday", "holiday shopping"],
        "competitors": ["Walmart", "Target", "Amazon"],
        "markets": ["US"],
    },
]


class _Query:
    def __init__(self, conn, sql):
        self.conn, self.sql = conn, sql

    def collect(self):
        cur = self.conn.cursor()
        try:
            cur.execute(self.sql)
            return cur.fetchall()
        finally:
            cur.close()


class ConnectorSession:
    """Minimal Snowpark-like wrapper so snowflake_loader works with the Python connector."""

    def __init__(self, conn):
        self.conn = conn

    def sql(self, sql):
        return _Query(self.conn, sql)


def main():
    conn = snowflake.connector.connect(connection_name=SNOWFLAKE_CONNECTION)
    session = ConnectorSession(conn)
    session.sql("USE WAREHOUSE MARKETING_WH").collect()
    try:
        # Optional: pass event name substrings to run a subset, e.g. `run_pipeline.py FIFA`
        filters = [a.lower() for a in sys.argv[1:]]
        for cfg in RUNS:
            if filters and not any(f in cfg["event_name"].lower() for f in filters):
                continue
            result = run_full_intelligence(news_api_key=EVENT_REGISTRY_API_KEY, **cfg)
            load_intelligence_run(session, result)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
