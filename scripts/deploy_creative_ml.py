"""
Deploy and run the creative intelligence layer in MARKETING_COPILOT.CREATIVE.

Usage:
    python scripts/deploy_creative_ml.py              # views, procedures, NET_LEAN, model training
    python scripts/deploy_creative_ml.py --procs-only # just re-upload code and recreate procedures
"""

import argparse
import json
import os
import sys
from pathlib import Path

import snowflake.connector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from env_keys import get_secret  # noqa: E402

CODE_FILES = ["common.py", "net_lean.py", "train_model.py", "score_ad.py"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs-only", action="store_true")
    ap.add_argument("--n-boot", type=int, default=200)
    args = ap.parse_args()

    name = os.environ.get("SNOWFLAKE_CONNECTION") or get_secret("SNOWFLAKE_CONNECTION", required=False) or None
    conn = snowflake.connector.connect(connection_name=name) if name else snowflake.connector.connect()
    cur = conn.cursor()
    try:
        cur.execute("USE WAREHOUSE MARKETING_WH")
        for f in ["sql/ddl/09_creative_features.sql", "sql/ddl/10_creative_ml.sql"]:
            if f.endswith("10_creative_ml.sql"):
                cur.execute("CREATE STAGE IF NOT EXISTS MARKETING_COPILOT.CREATIVE.CODE_STAGE")
                for code in CODE_FILES:
                    path = (ROOT / "src" / "creative_ml" / code).as_posix()
                    cur.execute(f"PUT 'file://{path}' @MARKETING_COPILOT.CREATIVE.CODE_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE")
            for _ in conn.execute_string((ROOT / f).read_text(encoding="utf-8"), remove_comments=True):
                pass
            print(f"applied {f}")
        if args.procs_only:
            return
        cur.execute(f"CALL MARKETING_COPILOT.CREATIVE.COMPUTE_NET_LEAN({args.n_boot})")
        print("COMPUTE_NET_LEAN:", cur.fetchone()[0])
        cur.execute("CALL MARKETING_COPILOT.CREATIVE.TRAIN_CTR_MODEL()")
        res = json.loads(cur.fetchone()[0])
        print("TRAIN_CTR_MODEL chosen point model:", res["chosen"], "|", res["meta"])
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
