"""
Run a SQL test file whose test statements return (TEST_NAME, RESULT[, DETAIL]) and print a summary.
Usage: python scripts/run_sql_tests.py tests/test_creative.sql
Exit code is non-zero if any test fails.
"""

import os
import sys
from pathlib import Path

import snowflake.connector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from env_keys import get_secret  # noqa: E402


def main(path):
    name = os.environ.get("SNOWFLAKE_CONNECTION") or get_secret("SNOWFLAKE_CONNECTION", required=False) or None
    conn = snowflake.connector.connect(connection_name=name) if name else snowflake.connector.connect()
    failures = total = 0
    try:
        for cur in conn.execute_string((ROOT / path).read_text(encoding="utf-8"), remove_comments=True):
            if cur.description and cur.description[0][0].upper() == "TEST_NAME":
                for row in cur.fetchall():
                    total += 1
                    failures += row[1] != "PASS"
                    detail = f"  ({row[2]})" if len(row) > 2 and row[2] else ""
                    print(f"  {row[1]}  {row[0]}{detail}")
    finally:
        conn.close()
    print(f"\n{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "tests/test_creative.sql"))
