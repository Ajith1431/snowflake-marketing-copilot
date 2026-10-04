"""
Headless smoke test of streamlit/streamlit_app.py against live Snowflake (no browser).

The Snowpark session is replaced by a thin wrapper over the Python connector, and st.experimental_rerun is
shimmed (removed in newer Streamlit). All tabs execute on every run, so this checks Tabs 3, 6 and 7 for errors,
empty results and rendered elements.

Requires (local only): pip install streamlit plotly pyarrow
Usage: python scripts/smoke_test_app.py
"""

import os
import sys
import types
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != ROOT]  # repo's streamlit/ folder shadows the package
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402
import snowflake.connector  # noqa: E402
import streamlit as st  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

from env_keys import get_secret  # noqa: E402

QUERIES = []


class _Result:
    def __init__(self, conn, sql):
        self.conn, self.sql = conn, sql

    def _run(self):
        cur = self.conn.cursor()
        try:
            cur.execute(self.sql)
            cols = [c[0] for c in cur.description] if cur.description else []
            rows = [tuple(float(v) if isinstance(v, Decimal) else v for v in r) for r in cur.fetchall()]
        finally:
            cur.close()
        QUERIES.append((" ".join(self.sql.split())[:110], len(rows)))
        return cols, rows

    def collect(self):
        return self._run()[1]

    def to_pandas(self):
        cols, rows = self._run()
        return pd.DataFrame(rows, columns=cols)


class _Session:
    def __init__(self, conn):
        self.conn = conn

    def sql(self, sql, params=None):
        return _Result(self.conn, sql)


def install_fakes(conn):
    session = _Session(conn)
    ctx = types.ModuleType("snowflake.snowpark.context")
    ctx.get_active_session = lambda: session
    snowpark = types.ModuleType("snowflake.snowpark")
    snowpark.context = ctx
    sys.modules["snowflake.snowpark"] = snowpark
    sys.modules["snowflake.snowpark.context"] = ctx
    if not hasattr(st, "experimental_rerun"):
        st.experimental_rerun = st.rerun
    # Emulate the older SiS runtime, which rejects st.dataframe(hide_index=)
    if not getattr(st.dataframe, "_sis_compat", False):
        _orig_df = st.dataframe

        def _old_dataframe(*args, **kwargs):
            if "hide_index" in kwargs:
                raise TypeError("dataframe() got an unexpected keyword argument 'hide_index'")
            return _orig_df(*args, **kwargs)
        _old_dataframe._sis_compat = True
        st.dataframe = _old_dataframe


def summary(at, label):
    errs = [str(e.value) for e in at.exception]
    print(f"\n--- {label} ---")
    print(f"  exceptions: {len(errs)}" + ("".join(f"\n    !! {e[:300]}" for e in errs) if errs else ""))
    print(f"  st.error: {[e.value[:120] for e in at.error]}")
    return len(errs)


def find(at, label_start):
    for sb in at.selectbox:
        if sb.label.startswith(label_start):
            return sb
    raise KeyError(label_start)


def main():
    name = os.environ.get("SNOWFLAKE_CONNECTION") or get_secret("SNOWFLAKE_CONNECTION", required=False) or None
    conn = snowflake.connector.connect(connection_name=name) if name else snowflake.connector.connect()
    conn.cursor().execute("USE WAREHOUSE MARKETING_WH")
    install_fakes(conn)
    failures = 0
    try:
        at = AppTest.from_file(str(ROOT / "streamlit" / "streamlit_app.py"), default_timeout=600)
        at.run()
        failures += summary(at, "initial render (all tabs)")
        print(f"  tabs: {[t.label for t in at.tabs]}")

        for brand, market in [("Nike", "UK"), ("Pepsi", "UAE"), ("Samsung", "IN")]:
            QUERIES.clear()
            at.selectbox(key="pdv_brand2").select(brand).run()                 # Tab 7 default view
            failures += summary(at, f"Tab 7: {brand}, all markets")
            md = [m.value for m in at.markdown if m.value.startswith("**Takeaway:**")]
            print(f"  takeaway: {md[0][:160] if md else 'MISSING'}")
            print(f"  best card: {[s.value.splitlines()[0] for s in at.success if 'Best attribute' in s.value] or [i.value[:60] for i in at.info if 'Best attribute' in i.value]}")
            print(f"  worst card: {[e.value.splitlines()[0] for e in at.error if 'Worst attribute' in e.value] or [i.value[:60] for i in at.info if 'Worst attribute' in i.value]}")
            print(f"  plotly charts on page: {len(at.get('plotly_chart'))}")
            at.selectbox(key="pdv_market2").select(market).run()
            failures += summary(at, f"Tab 7: {brand} drill-down market={market}")
            notes = [c.value for c in at.caption if c.value.startswith("Not enough data")]
            print(f"  drill-down 'not enough data' caption present: {bool(notes)}")
            at.selectbox(key="pdv_market2").select("ALL").run()

            at.selectbox(key="cs_ci_brand").select(brand).run()                # Tab 6 hook
            at.selectbox(key="cs_ci_market").select(market).run()
            failures += summary(at, f"Tab 6 brief hook: {brand} / {market}")
            print(f"  caption: {[c.value for c in at.caption if c.value.startswith(('Net helpers', 'No net-helped'))][:1]}")
            for q, n in QUERIES:
                if "CREATIVE." in q:
                    print(f"  rows={n:<4} {q}")

        at.selectbox(key="pdv_brand2").select("ALL brands").run()
        at.selectbox(key="pdv_market2").select("IN").run()
        failures += summary(at, "Tab 7: ALL brands, market=IN (planted: weak drivers)")
        md = [m.value for m in at.markdown if m.value.startswith("**Takeaway:**")]
        print(f"  takeaway: {md[0][:200] if md else 'MISSING'}")
        at.selectbox(key="pdv_market2").select("UK").run()
        md = [m.value for m in at.markdown if m.value.startswith("**Takeaway:**")]
        print(f"  contrast, market=UK takeaway: {md[0][:200] if md else 'MISSING'}")

        for preset in at.selectbox(key="pred_preset").options:                # Tab 3 Predictor presets
            at.selectbox(key="pred_preset").select(preset).run()
            at.button(key="pred_score_btn").click().run()
            failures += summary(at, f"Tab 3: {preset}")
            metrics = [(m.label, m.value) for m in at.metric if "Scenario" in m.label or "Lift" in m.label]
            print(f"  metrics: {metrics}")
            print(f"  changed: {[c.value for c in at.caption if c.value.startswith('Changed in B')]}")
            print(f"  ranges: {[c.value for c in at.caption if c.value.startswith(('p10-p90 range', 'Range:'))]}")
            msgs = [x.value for x in list(at.info) + list(at.warning) + list(at.success)
                    if "Expected difference" in x.value]
            print(f"  message: {msgs}")
    finally:
        conn.close()
    print(f"\nTotal exceptions: {failures}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
