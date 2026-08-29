import snowflake.connector

conn = snowflake.connector.connect(connection_name="wfvamnp-ap54607")
cur = conn.cursor()
cur.execute("USE ROLE ACCOUNTADMIN")
cur.execute("USE WAREHOUSE MARKETING_WH")
cur.execute("USE DATABASE MARKETING_COPILOT")
cur.execute("USE SCHEMA SEMANTIC")

# Upload YAML to stage
put_sql = "PUT 'file://c:/Users/majithkumar/SnowflakeHackathon/semantic_models/campaign_analytics.yaml' @SEMANTIC_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
cur.execute(put_sql)
result = cur.fetchall()
print("PUT result:", result)

# List stage to confirm
cur.execute("LIST @SEMANTIC_STAGE/")
for row in cur.fetchall():
    print("Stage file:", row)

cur.close()
conn.close()
print("Done!")
