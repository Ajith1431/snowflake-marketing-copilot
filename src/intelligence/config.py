import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from env_keys import get_secret

EVENT_REGISTRY_API_KEY = get_secret("EVENT_REGISTRY_API_KEY")
NEWS_API_KEY = get_secret("NEWS_API_KEY", required=False)  # Optional: get from newsapi.org if needed
SNOWFLAKE_CONNECTION = os.environ.get("SNOWFLAKE_CONNECTION", "clvulgz-zj61620")  # name in ~/.snowflake/connections.toml
