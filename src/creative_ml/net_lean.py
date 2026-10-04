"""
Snowflake procedure handler: CREATIVE.COMPUTE_NET_LEAN(N_BOOT)
Writes CREATIVE.NET_LEAN, CREATIVE.NET_LEAN_FAMILY, CREATIVE.NET_LEAN_TAKEAWAY.

Lifts are versus a reference value per family (common.REFERENCE; the stratum's most common value when the
reference has < 30 ads there), stored in REFERENCE_VALUE. The reference itself has no row; binary families
have a single Y-vs-N row.

Classification per (stratum, attribute value vs reference), applied in this order:
  INSUFFICIENT_DATA  n_ads_with < 30
  MIXED              (market x objective strata) brand-level lifts vs the same reference disagree in sign (|lift| > 3% each side)
  NET_HELPED         lift > +3% and 95% interval excludes 0
  NET_HURT           lift < -3% and 95% interval excludes 0
  NEGLIGIBLE         95% interval entirely within +-3%
  INCONCLUSIVE       none of the above (interval includes 0 but is wider than +-3%)
"""

import json
import zlib

import numpy as np
import pandas as pd

from common import (AD_LEVEL_SQL, BRANDS, FAMILIES, LOW_N, MARKETS, NEGLIGIBLE_PCT, OBJECTIVES, REFERENCE,
                    adjusted_contrasts, bootstrap_contrasts, prepare_ads, resolve_refs, to_lift_pct)

MIN_STRATUM_ADS = 15
MIN_BRAND_CELL = 10


def strata(ads):
    for m in MARKETS + ["ALL"]:
        for o in OBJECTIVES + ["ALL"]:
            mask = (ads.market == m if m != "ALL" else True) & (ads.objective == o if o != "ALL" else True)
            yield "MARKET_X_OBJECTIVE", m, o, "ALL", ads[mask] if not isinstance(mask, bool) else ads
        for b in BRANDS:
            mask = (ads.market == m if m != "ALL" else True) & (ads.brand == b)
            yield "MARKET_X_BRAND", m, "ALL", b, ads[mask]


def stratum_label(m, o, b):
    parts = [f"market={m}"] + ([f"objective={o}"] if o != "ALL" else []) + ([f"brand={b}"] if b != "ALL" else [])
    return ", ".join(parts)


def brand_lifts(sub, fam, val, refs):
    out = {}
    ref = refs[fam]
    for b in BRANDS:
        s = sub[sub.brand == b]
        n_w, n_r = int((s[fam] == val).sum()), int((s[fam] == ref).sum())
        if n_w >= MIN_BRAND_CELL and n_r >= MIN_BRAND_CELL:
            c = adjusted_contrasts(s, s["y"], controls_cat=("placement", "market", "objective"), refs=refs).get((fam, val))
            if c is not None:
                out[b] = round(float(to_lift_pct(c)), 1)
    return out


def classify(n_with, lift, lo, hi, blifts):
    if n_with < LOW_N or np.isnan(lift):
        return "INSUFFICIENT_DATA"
    pos = [v for v in blifts.values() if v > NEGLIGIBLE_PCT]
    neg = [v for v in blifts.values() if v < -NEGLIGIBLE_PCT]
    if pos and neg:
        return "MIXED"
    if lift > NEGLIGIBLE_PCT and lo > 0:
        return "NET_HELPED"
    if lift < -NEGLIGIBLE_PCT and hi < 0:
        return "NET_HURT"
    if lo >= -NEGLIGIBLE_PCT and hi <= NEGLIGIBLE_PCT:
        return "NEGLIGIBLE"
    return "INCONCLUSIVE"


def compute(ads, n_boot=200):
    rows = []
    for stype, m, o, b, sub in strata(ads):
        n_ads = len(sub)
        refs = resolve_refs(sub)
        if n_ads >= MIN_STRATUM_ADS:
            point, ci = bootstrap_contrasts(sub, n_boot=n_boot, refs=refs,
                                            seed=zlib.crc32(f"{stype}|{m}|{o}|{b}".encode()))
        else:
            point, ci = {}, {}
        for fam in FAMILIES:
            ref = refs[fam]
            n_ref = int((sub[fam] == ref).sum())
            for val in sorted(v for v in ads[fam].astype(str).unique() if v != ref):
                n_with = int((sub[fam] == val).sum())
                c = point.get((fam, val), np.nan)
                lo_c, hi_c = ci.get((fam, val), (np.nan, np.nan))
                lift, lo, hi = (float(to_lift_pct(x)) if not np.isnan(x) else np.nan for x in (c, lo_c, hi_c))
                blifts = brand_lifts(sub, fam, val, refs) if stype == "MARKET_X_OBJECTIVE" and n_with >= LOW_N else {}
                rows.append({
                    "STRATUM_TYPE": stype, "MARKET": m, "OBJECTIVE": o, "BRAND": b,
                    "STRATUM": stratum_label(m, o, b), "ATTRIBUTE_FAMILY": fam, "ATTRIBUTE_VALUE": val,
                    "REFERENCE_VALUE": ref, "REFERENCE_IS_FALLBACK": ref != REFERENCE[fam],
                    "N_ADS": n_ads, "N_ADS_WITH": n_with, "N_ADS_WITHOUT": n_ads - n_with, "N_ADS_REFERENCE": n_ref,
                    "ADJ_LIFT_PCT": None if np.isnan(lift) else round(lift, 2),
                    "CI_LOW_PCT": None if np.isnan(lo) else round(lo, 2),
                    "CI_HIGH_PCT": None if np.isnan(hi) else round(hi, 2),
                    "BRAND_LIFTS_JSON": json.dumps(blifts),
                    "NET_LEAN_CLASS": classify(n_with, lift, lo, hi, blifts),
                })
    return pd.DataFrame(rows)


def family_summary(nl):
    ok = nl[nl.NET_LEAN_CLASS != "INSUFFICIENT_DATA"].dropna(subset=["ADJ_LIFT_PCT"])
    rows = []
    for (stype, m, o, b, fam), g in ok.groupby(["STRATUM_TYPE", "MARKET", "OBJECTIVE", "BRAND", "ATTRIBUTE_FAMILY"]):
        best, worst = g.loc[g.ADJ_LIFT_PCT.idxmax()], g.loc[g.ADJ_LIFT_PCT.idxmin()]
        rows.append({"STRATUM_TYPE": stype, "MARKET": m, "OBJECTIVE": o, "BRAND": b, "ATTRIBUTE_FAMILY": fam,
                     "REFERENCE_VALUE": best.REFERENCE_VALUE,
                     "BEST_VALUE": best.ATTRIBUTE_VALUE, "BEST_LIFT_PCT": best.ADJ_LIFT_PCT, "BEST_CLASS": best.NET_LEAN_CLASS,
                     "WORST_VALUE": worst.ATTRIBUTE_VALUE, "WORST_LIFT_PCT": worst.ADJ_LIFT_PCT, "WORST_CLASS": worst.NET_LEAN_CLASS})
    return pd.DataFrame(rows)


def pretty(fam, val, ref=None):
    return f"{fam.replace('_', ' ')} = {val}" + (f" vs {ref}" if ref else "")


def takeaways(nl):
    rows = []
    for (stype, m, o, b), g in nl.groupby(["STRATUM_TYPE", "MARKET", "OBJECTIVE", "BRAND"]):
        label, n_ads = g.STRATUM.iloc[0], int(g.N_ADS.iloc[0])
        helped = g[g.NET_LEAN_CLASS == "NET_HELPED"].sort_values("ADJ_LIFT_PCT", ascending=False)
        hurt = g[g.NET_LEAN_CLASS == "NET_HURT"].sort_values("ADJ_LIFT_PCT")
        enough = int((g.NET_LEAN_CLASS != "INSUFFICIENT_DATA").sum())
        parts = []
        if len(helped):
            h = helped.iloc[0]
            parts.append(f"{pretty(h.ATTRIBUTE_FAMILY, h.ATTRIBUTE_VALUE, h.REFERENCE_VALUE)} is the strongest net helper "
                         f"({h.ADJ_LIFT_PCT:+.1f}% adjusted CTR, 95% CI {h.CI_LOW_PCT:+.1f}% to {h.CI_HIGH_PCT:+.1f}%)")
        if len(hurt):
            h = hurt.iloc[0]
            parts.append(f"{pretty(h.ATTRIBUTE_FAMILY, h.ATTRIBUTE_VALUE, h.REFERENCE_VALUE)} is the strongest net hurt "
                         f"({h.ADJ_LIFT_PCT:+.1f}%, 95% CI {h.CI_LOW_PCT:+.1f}% to {h.CI_HIGH_PCT:+.1f}%)")
        if parts:
            text = f"In {label} ({n_ads} ads): " + "; ".join(parts) + "."
        elif enough:
            text = (f"In {label} ({n_ads} ads), no attribute value clears the evidence bar "
                    f"(|lift| > 3% with a 95% interval excluding 0).")
        else:
            text = f"In {label} ({n_ads} ads), every attribute value has fewer than {LOW_N} ads: not enough data."
        rows.append({"STRATUM_TYPE": stype, "MARKET": m, "OBJECTIVE": o, "BRAND": b, "STRATUM": label, "N_ADS": n_ads,
                     "TOP_HELPER": None if helped.empty else pretty(helped.iloc[0].ATTRIBUTE_FAMILY, helped.iloc[0].ATTRIBUTE_VALUE, helped.iloc[0].REFERENCE_VALUE),
                     "TOP_HELPER_LIFT_PCT": None if helped.empty else helped.iloc[0].ADJ_LIFT_PCT,
                     "TOP_HURT": None if hurt.empty else pretty(hurt.iloc[0].ATTRIBUTE_FAMILY, hurt.iloc[0].ATTRIBUTE_VALUE, hurt.iloc[0].REFERENCE_VALUE),
                     "TOP_HURT_LIFT_PCT": None if hurt.empty else hurt.iloc[0].ADJ_LIFT_PCT,
                     "N_VALUES_WITH_ENOUGH_DATA": enough, "TAKEAWAY": text})
    return pd.DataFrame(rows)


def run(session, n_boot=200):
    ads = prepare_ads(session.sql(AD_LEVEL_SQL).to_pandas())
    nl = compute(ads, int(n_boot))
    fam = family_summary(nl)
    tk = takeaways(nl)
    for name, df in [("NET_LEAN", nl), ("NET_LEAN_FAMILY", fam), ("NET_LEAN_TAKEAWAY", tk)]:
        session.write_pandas(df, name, database="MARKETING_COPILOT", schema="CREATIVE",
                             auto_create_table=True, overwrite=True, quote_identifiers=False)
    counts = nl.NET_LEAN_CLASS.value_counts().to_dict()
    return {"net_lean_rows": len(nl), "family_rows": len(fam), "takeaway_rows": len(tk), "class_counts": counts}
