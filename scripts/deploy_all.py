"""
Build the entire NovaSpark Marketing Co-Pilot in a Snowflake account.

Usage:
    python scripts/deploy_all.py                 # full build (DDL, data, AI layer, app, tests)
    python scripts/deploy_all.py --skip-data     # keep existing RAW data, rebuild everything else
    python scripts/deploy_all.py --app-only      # only re-upload and recreate the Streamlit app

Connection: SNOWFLAKE_CONNECTION env var / .env (name in ~/.snowflake/connections.toml).
The role must be able to create databases, warehouses, agents, MCP servers and security integrations
(ACCOUNTADMIN on a trial account).
"""

import argparse
import os
import re
import sys
from pathlib import Path

import snowflake.connector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from env_keys import get_secret  # noqa: E402

DB = "MARKETING_COPILOT"
CSV_TABLES = [
    "clients", "products", "channels", "audience_segments", "customer_profiles", "campaigns",
    "bridge_campaign_segment", "campaign_metrics", "customer_feedback", "market_events", "brand_guidelines",
]
AGENTS = {
    "MARKETING_COPILOT": "marketing_copilot_agent.yaml",
    "INTERNET_INTELLIGENCE_AGENT": "internet_intelligence_agent.yaml",
    "STRATEGY_SYNTHESIS_AGENT": "strategy_synthesis_agent.yaml",
}


def step(title):
    print(f"\n=== {title} ===")


def run_file(conn, rel_path):
    sql = (ROOT / rel_path).read_text(encoding="utf-8")
    count = sum(1 for _ in conn.execute_string(sql, remove_comments=True))
    print(f"  {rel_path}: {count} statements OK")


def run(conn, sql):
    cur = conn.cursor()
    try:
        cur.execute(sql)
        return cur.fetchall()
    finally:
        cur.close()


def put(conn, local, stage, compress):
    path = (ROOT / local).as_posix()
    run(conn, f"PUT 'file://{path}' {stage} AUTO_COMPRESS={'TRUE' if compress else 'FALSE'} OVERWRITE=TRUE")


def dollar_quoted(text):
    if "$$" in text:
        raise ValueError("Specification text must not contain $$")
    return f"$${text}$$"


def strip_yaml_comments(text):
    return "\n".join(line for line in text.splitlines() if not re.match(r"^\s*#", line))


def deploy_data(conn):
    step("2. Upload CSVs and load RAW tables")
    for name in CSV_TABLES:
        csv = Path("data/samples") / f"{name}.csv"
        if not (ROOT / csv).exists():
            raise SystemExit(f"Missing {csv}. Run: python data/generators/generate_all.py")
        put(conn, csv, f"@{DB}.RAW.MARKETING_STAGE/{name}/", compress=True)
    print(f"  uploaded {len(CSV_TABLES)} CSV files")
    run_file(conn, "sql/dml/01_load_data.sql")
    run_file(conn, "sql/dml/02_reduce_clients.sql")


def deploy_semantic_view(conn):
    step("5. Semantic view CAMPAIGN_ANALYTICS")
    yaml_text = (ROOT / "semantic_models/campaign_analytics.yaml").read_text(encoding="utf-8")
    put(conn, "semantic_models/campaign_analytics.yaml", f"@{DB}.SEMANTIC.SEMANTIC_STAGE/", compress=False)
    run(conn, f"DROP SEMANTIC VIEW IF EXISTS {DB}.SEMANTIC.CAMPAIGN_ANALYTICS")
    print("  " + run(conn, f"CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML('{DB}.SEMANTIC', {dollar_quoted(yaml_text)})")[0][0])


def deploy_agents(conn):
    step("7. Cortex Agents")
    for name, file in AGENTS.items():
        spec = strip_yaml_comments((ROOT / "agents" / file).read_text(encoding="utf-8"))
        run(conn, f"CREATE OR REPLACE AGENT {DB}.SEMANTIC.{name} FROM SPECIFICATION {dollar_quoted(spec)}")
        print(f"  {name} OK")


def deploy_app(conn):
    step("9. Streamlit app")
    for f in ["streamlit/streamlit_app.py", "streamlit/environment.yml"]:
        put(conn, f, f"@{DB}.SEMANTIC.STREAMLIT_STAGE/", compress=False)
    run(conn, f"""
        CREATE OR REPLACE STREAMLIT {DB}.SEMANTIC.MARKETING_COPILOT_APP
          ROOT_LOCATION = '@{DB}.SEMANTIC.STREAMLIT_STAGE'
          MAIN_FILE = 'streamlit_app.py'
          QUERY_WAREHOUSE = MARKETING_WH
          TITLE = 'NovaSpark Marketing Co-Pilot'""")
    print("  MARKETING_COPILOT_APP OK (Snowsight > Projects > Streamlit)")


def run_tests(conn):
    step("10. Validation (tests/test_validation.sql)")
    sql = (ROOT / "tests/test_validation.sql").read_text(encoding="utf-8")
    failures = 0
    for cur in conn.execute_string(sql, remove_comments=True):
        row = cur.fetchone()
        if cur.description and cur.description[0][0].upper() == "TEST_NAME":
            print(f"  {row[1]}  {row[0]}")
            failures += row[1] != "PASS"
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-data", action="store_true", help="do not recreate or reload RAW tables")
    parser.add_argument("--app-only", action="store_true", help="only redeploy the Streamlit app")
    args = parser.parse_args()

    connection = os.environ.get("SNOWFLAKE_CONNECTION") or get_secret("SNOWFLAKE_CONNECTION", required=False) or None
    conn = snowflake.connector.connect(connection_name=connection) if connection else snowflake.connector.connect()
    print(f"Connected: {run(conn, 'SELECT CURRENT_ACCOUNT(), CURRENT_USER(), CURRENT_ROLE()')[0]}")

    try:
        if args.app_only:
            run(conn, "USE WAREHOUSE MARKETING_WH")
            deploy_app(conn)
            return

        step("1. Database, schemas, warehouse, stages, tables")
        run_file(conn, "sql/ddl/01_setup.sql")
        if not args.skip_data:
            run_file(conn, "sql/ddl/02_tables.sql")
        run_file(conn, "sql/ddl/03_event_intelligence_tables.sql")

        if not args.skip_data:
            deploy_data(conn)

        step("3. Dynamic tables (analytics + event analytics)")
        run_file(conn, "sql/dynamic_tables/01_analytics_layer.sql")
        run_file(conn, "sql/dynamic_tables/02_event_analytics.sql")

        step("4. Cortex Search services")
        run_file(conn, "sql/ddl/07_cortex_search.sql")

        deploy_semantic_view(conn)

        step("6. Creative + intelligence stored procedures")
        run_file(conn, "sql/ddl/05_mcp_procedures.sql")

        deploy_agents(conn)

        step("8. MCP server, OAuth integration, MCP_USER_ROLE grants")
        run_file(conn, "sql/ddl/06_mcp_server.sql")

        deploy_app(conn)

        failures = run_tests(conn)
        print(f"\nBuild complete. Validation failures: {failures}")
        print("Next: python src/intelligence/run_pipeline.py  (loads live event intelligence)")
        sys.exit(1 if failures else 0)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
