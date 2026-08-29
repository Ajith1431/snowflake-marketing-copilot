import snowflake.connector

conn = snowflake.connector.connect(connection_name="wfvamnp-ap54607")
cur = conn.cursor()
cur.execute("USE ROLE ACCOUNTADMIN")
cur.execute("USE WAREHOUSE MARKETING_WH")
cur.execute("USE DATABASE MARKETING_COPILOT")
cur.execute("USE SCHEMA SEMANTIC")

files = [
    (r"c:/Users/majithkumar/SnowflakeHackathon/streamlit/streamlit_app.py", "@STREAMLIT_STAGE/"),
    (r"c:/Users/majithkumar/SnowflakeHackathon/streamlit/environment.yml", "@STREAMLIT_STAGE/"),
]

for local_path, stage_path in files:
    put_sql = f"PUT 'file://{local_path}' {stage_path} AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
    print(f"Uploading {local_path}...")
    cur.execute(put_sql)
    for row in cur.fetchall():
        print(f"  Result: {row}")

cur.execute("LIST @STREAMLIT_STAGE/")
for row in cur.fetchall():
    print(f"  Stage: {row}")

cur.close()
conn.close()
print("Done!")
