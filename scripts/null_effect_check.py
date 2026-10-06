"""
Local only: false-positive check for NET_LEAN, written to CREATIVE.NULL_EFFECT_CHECK.

For every NET_LEAN stratum we rebuild the noise-free planted CTR signal per ad (generator's own effect
functions, via scripts/effect_recovery.py) and run the SAME adjusted-contrast estimator on it, with the same
per-stratum reference values as NET_LEAN (value vs reference). An attribute
value is "null" in a stratum when its planted contrast vs the reference is below 0.03 log-odds (about 3%) in absolute value,
i.e. the answer key plants no CTR effect for it there. For null values with enough data
(class != INSUFFICIENT_DATA) we count how often NET_LEAN still says NET_HELPED or NET_HURT.

The answer key is read locally only; the table holds aggregates and is not granted to agent or MCP roles.
Usage: python scripts/null_effect_check.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import effect_recovery as er  # noqa: E402  (adds src paths, loads generator + answer key)
from common import FAMILIES, adjusted_contrasts  # noqa: E402
from net_lean import strata  # noqa: E402

S = "MARKETING_COPILOT.CREATIVE"
NULL_TOL = 0.03


def main():
    conn = er.connect()
    cur = conn.cursor()
    try:
        cur.execute("USE WAREHOUSE MARKETING_WH")
        ads = er.fetch(cur, er.AD_SQL)
        ads["log_spend_wk"] = np.log(ads.spend / ads.n_weeks)
        truth = er.planted_signals(ads)
        nl = er.fetch(cur, f"SELECT stratum_type, market, objective, brand, attribute_family, attribute_value, "
                           f"net_lean_class FROM {S}.NET_LEAN WHERE net_lean_class <> 'INSUFFICIENT_DATA'")
        nl = nl.set_index(["stratum_type", "market", "objective", "brand", "attribute_family", "attribute_value"])

        rows = []
        for stype, m, o, b, sub in strata(ads):
            if len(sub) < 15:
                continue
            planted = adjusted_contrasts(sub, truth.loc[sub.index, "ctr_all"])
            for (fam, val), pc in planted.items():
                key = (stype, m, o, b, fam, val)
                if abs(pc) < NULL_TOL and key in nl.index:
                    rows.append((fam, val, nl.loc[key, "net_lean_class"]))
        d = pd.DataFrame(rows, columns=["ATTRIBUTE_FAMILY", "ATTRIBUTE_VALUE", "CLS"])
        d["FLAG"] = d.CLS.isin(["NET_HELPED", "NET_HURT"])
        out = (d.groupby(["ATTRIBUTE_FAMILY", "ATTRIBUTE_VALUE"])
                .agg(N_STRATA_TESTED=("FLAG", "size"), N_FALSE_POSITIVE=("FLAG", "sum")).reset_index())
        out["FALSE_POSITIVE_SHARE"] = (out.N_FALSE_POSITIVE / out.N_STRATA_TESTED).round(3)
        planted_fams = {e["family"] for e in er.GT["ctr"]["attribute_effects"]}
        out["NULL_IN_ALL_STRATA"] = ~out.ATTRIBUTE_FAMILY.isin(planted_fams)
        total_n, total_fp = int(out.N_STRATA_TESTED.sum()), int(out.N_FALSE_POSITIVE.sum())

        cur.execute(f"""CREATE OR REPLACE TABLE {S}.NULL_EFFECT_CHECK (
            ATTRIBUTE_FAMILY VARCHAR, ATTRIBUTE_VALUE VARCHAR, N_STRATA_TESTED INT, N_FALSE_POSITIVE INT,
            FALSE_POSITIVE_SHARE FLOAT, NULL_IN_ALL_STRATA BOOLEAN)
            COMMENT = 'False-positive check of NET_LEAN against the answer key (null values only). Owner only.'""")
        cur.executemany(f"INSERT INTO {S}.NULL_EFFECT_CHECK VALUES (%s,%s,%s,%s,%s,%s)",
                        [(r.ATTRIBUTE_FAMILY, r.ATTRIBUTE_VALUE, int(r.N_STRATA_TESTED), int(r.N_FALSE_POSITIVE),
                          float(r.FALSE_POSITIVE_SHARE), bool(r.NULL_IN_ALL_STRATA)) for r in out.itertuples()])
        cur.executemany(f"INSERT INTO {S}.NULL_EFFECT_CHECK VALUES (%s,%s,%s,%s,%s,%s)",
                        [("ALL", "ALL", total_n, total_fp, round(total_fp / total_n, 3), None)])

        pd.set_option("display.width", 200)
        print(out.sort_values(["ATTRIBUTE_FAMILY", "ATTRIBUTE_VALUE"]).to_string(index=False))
        print(f"\nNull (stratum, value) cases with enough data: {total_n}; classified NET_HELPED/NET_HURT: "
              f"{total_fp} = {total_fp / total_n * 100:.1f}%")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
