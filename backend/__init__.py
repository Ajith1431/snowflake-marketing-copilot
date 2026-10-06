"""Campaign Intelligence Platform — FastAPI Backend.

To run locally:
    uvicorn backend.main:app --reload --port 8000

To run in production:
    uvicorn backend.main:app --host 0.0.0.0 --port $PORT

Prerequisites (see requirements.txt):
    fastapi, uvicorn, pydantic, python-dotenv, snowflake-connector-python

Environment (copy .env.example -> .env):
    SNOWFLAKE_ACCOUNT=BEWLIMS-GP86073
    SNOWFLAKE_USER=SRIRAMBASKARAN77
    SNOWFLAKE_PASSWORD=...
    SNOWFLAKE_ROLE=ACCOUNTADMIN
    SNOWFLAKE_WAREHOUSE=CAMPAIGN_WH
    SNOWFLAKE_DATABASE=CampaignIntelligenceAI
    APP_USERNAME=admin
    APP_PASSWORD=admin
"""
