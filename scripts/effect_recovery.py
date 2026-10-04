"""
Step 5 (local only): compare estimated effects with the answer key and write CREATIVE.EFFECT_RECOVERY.

estimated = adjusted log-odds contrast inside the effect's stratum (same ridge estimator as NET_LEAN:
            all 8 attribute families + log weekly spend + brand + placement, "with v vs other values").
planted   = the SAME estimator applied to the noise-free planted signal, rebuilt per ad from the
            generator's effect functions, so both numbers are on the same contrast scale.
            planted_raw_log_odds is the size as written in tests/fixtures/ground_truth_effects.json.
direction_match: same sign (if |planted| < 0.03, match means |estimated| <= 0.10).
size_match:      |estimated - planted| <= max(0.10, 0.5 * |planted|).

The answer key is read locally only. No role other than the owner is granted access to EFFECT_RECOVERY.
Usage: python scripts/effect_recovery.py
"""

import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import snowflake.connector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "creative_ml"))
from env_keys import get_secret  # noqa: E402
from common import FAMILIES, adjusted_contrasts, logit_rate  # noqa: E402

GT = json.loads((ROOT / "tests" / "fixtures" / "ground_truth_effects.json").read_text())
spec = importlib.util.spec_from_file_location("gen", ROOT / "data" / "generators" / "generate_creative.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)  # module import only; main() is not run, nothing is regenerated

S = "MARKETING_COPILOT.CREATIVE"
CORE = ("25-34", "35-44")

AD_SQL = f"""
WITH w AS (
  SELECT ad_id,
    SUM(impressions) impr, SUM(clicks) clk, SUM(video_views) vv, SUM(video_p100) p100, SUM(conversions) conv,
    SUM(spend) spend, COUNT(DISTINCT week) n_weeks,
    SUM(IFF(age_group IN ('25-34','35-44'), impressions, 0)) impr_core, SUM(IFF(age_group IN ('25-34','35-44'), clicks, 0)) clk_core,
    SUM(IFF(age_group IN ('25-34','35-44'), 0, impressions)) impr_oth,  SUM(IFF(age_group IN ('25-34','35-44'), 0, clicks)) clk_oth
  FROM {S}.FACT_AD_WEEKLY GROUP BY ad_id
)
SELECT f.*, w.* EXCLUDE (ad_id) FROM (
  SELECT ad_id, ANY_VALUE(brand) brand, ANY_VALUE(market) market, ANY_VALUE(objective) objective,
         ANY_VALUE(placement) placement, ANY_VALUE(ad_type) ad_type, ANY_VALUE(aspect_ratio) aspect_ratio,
         ANY_VALUE(hook_type) hook_type, ANY_VALUE(headline_tone) headline_tone, ANY_VALUE(cta_tone) cta_tone,
         ANY_VALUE(background) background, ANY_VALUE(color_temp) color_temp, ANY_VALUE(has_person) has_person,
         ANY_VALUE(word_count_group) word_count_group, ANY_VALUE(has_logo_first_3s) has_logo_first_3s
  FROM {S}.V_AD_FEATURES GROUP BY ad_id) f
JOIN w USING (ad_id)
"""
WEEK_SQL = f"SELECT ad_id, week, impressions, clicks, frequency FROM {S}.V_AD_FEATURES"


def connect():
    name = os.environ.get("SNOWFLAKE_CONNECTION") or get_secret("SNOWFLAKE_CONNECTION", required=False) or None
    return snowflake.connector.connect(connection_name=name) if name else snowflake.connector.connect()


def fetch(cur, sql):
    cur.execute(sql)
    df = pd.DataFrame(cur.fetchall(), columns=[c[0].lower() for c in cur.description])
    for c in df.columns:
        if df[c].dtype == object and c not in ("ad_id", "week") and not isinstance(df[c].iloc[0], str):
            df[c] = df[c].astype(float)
    return df


def planted_signals(ads):
    """Noise-free planted log-odds components per ad, using the generator's own effect functions."""
    out = {k: [] for k in ["ctr_all", "ctr_core", "ctr_oth", "vtr", "completion", "cvr"]}
    for r in ads.itertuples():
        a = {f: getattr(r, f) for f in FAMILIES}
        ad = type("Ad", (), {"brand": r.brand, "market": r.market, "objective": r.objective,
                             "aspect_ratio": r.aspect_ratio})
        scale = gen.market_scale(ad)
        core = scale * gen.ctr_attribute_effect(ad, a, "25-34")
        oth = scale * gen.ctr_attribute_effect(ad, a, "45-54")
        w = r.impr_core / r.impr if r.impr else 0.0
        out["ctr_core"].append(core)
        out["ctr_oth"].append(oth)
        out["ctr_all"].append(w * core + (1 - w) * oth)
        out["vtr"].append(scale * gen.vtr_attribute_effect(ad, a))
        out["completion"].append(scale * gen.completion_attribute_effect(ad, a))
        out["cvr"].append(scale * gen.cvr_attribute_effect(ad, a, "45-54"))
    return pd.DataFrame(out, index=ads.index)


def main():
    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute("USE WAREHOUSE MARKETING_WH")
        ads = fetch(cur, AD_SQL)
        weeks = fetch(cur, WEEK_SQL)

        ads["log_spend_wk"] = np.log(ads.spend / ads.n_weeks)
        ads["y_ctr"] = logit_rate(ads.clk, ads.impr)
        ads["y_ctr_core"] = logit_rate(ads.clk_core, ads.impr_core)
        ads["y_ctr_oth"] = logit_rate(ads.clk_oth, ads.impr_oth)
        ads["y_vtr"] = np.where(ads.ad_type == "video", logit_rate(ads.vv, ads.impr), np.nan)
        ads["y_completion"] = np.where(ads.ad_type == "video", logit_rate(ads.p100, ads.vv), np.nan)
        ads["y_cvr"] = logit_rate(ads.conv, ads.clk)
        truth = planted_signals(ads)
        target = {"ctr": ("y_ctr", "ctr_all"), "ctr_core": ("y_ctr_core", "ctr_core"), "ctr_oth": ("y_ctr_oth", "ctr_oth"),
                  "vtr": ("y_vtr", "vtr"), "completion": ("y_completion", "completion"), "cvr": ("y_cvr", "cvr")}

        B = lambda b: ads.brand == b              # noqa: E731
        M = lambda m: ads.market == m             # noqa: E731
        O = lambda o: ads.objective == o          # noqa: E731
        video = ads.ad_type == "video"
        everything = pd.Series(True, index=ads.index)
        effects = [
            ("person_on_camera | Nike", "ctr", B("Nike"), "hook_type", "person_on_camera", 0.45),
            ("person_on_camera | Pepsi", "ctr", B("Pepsi"), "hook_type", "person_on_camera", 0.25),
            ("person_on_camera | Samsung", "ctr", B("Samsung"), "hook_type", "person_on_camera", 0.25),
            ("promo_led | LINK_CLICKS", "ctr", O("LINK_CLICKS"), "hook_type", "promo_led", 0.30),
            ("promo_led | AWARENESS", "ctr", O("AWARENESS"), "hook_type", "promo_led", 0.02),
            ("promo_led | LEADS", "ctr", O("LEADS"), "hook_type", "promo_led", 0.15),
            ("urgent | UK (Pepsi, Samsung)", "ctr", M("UK") & ~B("Nike"), "headline_tone", "urgent", -0.40),
            ("urgent | US (Pepsi, Samsung)", "ctr", M("US") & ~B("Nike"), "headline_tone", "urgent", 0.15),
            ("urgent | UK, Nike", "ctr", M("UK") & B("Nike"), "headline_tone", "urgent", -0.60),
            ("urgent | US, Nike", "ctr", M("US") & B("Nike"), "headline_tone", "urgent", 0.30),
            ("word_count 11+ | Nike, Pepsi", "ctr", ~B("Samsung"), "word_count_group", "11+", -0.20),
            ("word_count 11+ | Samsung", "ctr", B("Samsung"), "word_count_group", "11+", -0.08),
            ("warm | ages 25-44 (Nike, Samsung)", "ctr_core", ~B("Pepsi"), "color_temp", "warm", 0.10),
            ("warm | other ages (Nike, Samsung)", "ctr_oth", ~B("Pepsi"), "color_temp", "warm", 0.00),
            ("warm | Pepsi, ages 25-44", "ctr_core", B("Pepsi"), "color_temp", "warm", 0.25),
            ("warm | Pepsi, other ages", "ctr_oth", B("Pepsi"), "color_temp", "warm", 0.15),
            ("logo_first_3s | AWARENESS (Nike, Samsung)", "ctr", O("AWARENESS") & ~B("Pepsi"), "has_logo_first_3s", "Y", 0.10),
            ("logo_first_3s | AWARENESS, Pepsi", "ctr", O("AWARENESS") & B("Pepsi"), "has_logo_first_3s", "Y", 0.25),
            ("logo_first_3s | not AWARENESS", "ctr", ~O("AWARENESS"), "has_logo_first_3s", "Y", 0.00),
            ("ugc_style | Nike", "ctr", B("Nike"), "hook_type", "ugc_style", 0.30),
            ("playful | Pepsi", "ctr", B("Pepsi"), "headline_tone", "playful", 0.35),
            ("product_led | Samsung", "ctr", B("Samsung"), "hook_type", "product_led", 0.25),
            ("informational headline | Samsung", "ctr", B("Samsung"), "headline_tone", "informational", 0.20),
            ("IN: person_on_camera (x0.15)", "ctr", M("IN"), "hook_type", "person_on_camera", 0.25 * 0.15),
            ("IN: word_count 11+ (x0.15)", "ctr", M("IN"), "word_count_group", "11+", -0.20 * 0.15),
            ("IN: product_led, Samsung (x0.15)", "ctr", M("IN") & B("Samsung"), "hook_type", "product_led", 0.25 * 0.15),
            ("vtr: person_on_camera", "vtr", video, "hook_type", "person_on_camera", 0.20),
            ("vtr: ugc_style", "vtr", video, "hook_type", "ugc_style", 0.15),
            ("vtr: logo_first_3s", "vtr", video, "has_logo_first_3s", "Y", -0.15),
            ("vtr: word_count 11+", "vtr", video, "word_count_group", "11+", -0.10),
            ("completion: 9:16", "completion", video, "aspect_ratio", "9:16", 0.20),
            ("completion: person_on_camera", "completion", video, "hook_type", "person_on_camera", 0.10),
            ("cvr: transactional CTA", "cvr", ~M("IN"), "cta_tone", "transactional", 0.30),
            ("cvr: promo_led", "cvr", ~M("IN"), "hook_type", "promo_led", 0.20),
        ]

        rows = []
        for eid, metric, mask, fam, val, raw in effects:
            y_col, t_col = target[metric]
            sub = ads[mask & ads[y_col].notna()]
            fams = FAMILIES + (["aspect_ratio"] if fam == "aspect_ratio" else [])
            est = adjusted_contrasts(sub, sub[y_col], families=fams).get((fam, val), np.nan)
            pl = adjusted_contrasts(sub, truth.loc[sub.index, t_col], families=fams).get((fam, val), np.nan)
            rows.append((eid, metric, raw, pl, est, int((sub[fam] == val).sum()), len(sub)))

        # frequency > 6: within-ad slope (ad fixed effects) on ad-week log-odds CTR
        wk = weeks.copy()
        wk["y"] = logit_rate(wk.clicks, wk.impressions)
        wk["x"] = np.maximum(0.0, wk.frequency - 6.0)
        d = wk[["y", "x"]] - wk.groupby("ad_id")[["y", "x"]].transform("mean")
        slope = float((d.x * d.y).sum() / (d.x ** 2).sum())
        rows.append(("frequency > 6 (per unit)", "ctr", -0.15, -0.15, slope,
                     int((wk.groupby("ad_id").x.max() > 0).sum()), wk.ad_id.nunique()))

        out = pd.DataFrame(rows, columns=["EFFECT_ID", "METRIC", "PLANTED_RAW_LOG_ODDS", "PLANTED",
                                          "ESTIMATED", "N_ADS_WITH", "N_ADS_IN_STRATUM"])
        near_zero = out.PLANTED.abs() < 0.03
        out["DIRECTION_MATCH"] = np.where(near_zero, out.ESTIMATED.abs() <= 0.10,
                                          np.sign(out.ESTIMATED) == np.sign(out.PLANTED))
        out["SIZE_MATCH"] = (out.ESTIMATED - out.PLANTED).abs() <= np.maximum(0.10, 0.5 * out.PLANTED.abs())
        out["MATCH"] = np.where(out.DIRECTION_MATCH, "Y", "N")
        out["LOW_N_FLAG"] = np.where(out.N_ADS_WITH < 30, "n<30", "")
        for c in ["PLANTED_RAW_LOG_ODDS", "PLANTED", "ESTIMATED"]:
            out[c] = out[c].round(3)

        cur.execute(f"""CREATE OR REPLACE TABLE {S}.EFFECT_RECOVERY (
            EFFECT_ID VARCHAR, METRIC VARCHAR, PLANTED_RAW_LOG_ODDS FLOAT, PLANTED FLOAT, ESTIMATED FLOAT,
            N_ADS_WITH INT, N_ADS_IN_STRATUM INT, DIRECTION_MATCH BOOLEAN, SIZE_MATCH BOOLEAN, MATCH VARCHAR, LOW_N_FLAG VARCHAR)
            COMMENT = 'Answer-key comparison. Owner only: do not grant to agent or MCP roles.'""")
        cur.executemany(f"INSERT INTO {S}.EFFECT_RECOVERY VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        [tuple(None if (isinstance(v, float) and np.isnan(v)) else (bool(v) if isinstance(v, np.bool_) else
                         (int(v) if isinstance(v, np.integer) else (float(v) if isinstance(v, np.floating) else v))) for v in r)
                         for r in out.itertuples(index=False)])

        pd.set_option("display.width", 250, "display.max_rows", 100)
        print(out[["EFFECT_ID", "METRIC", "PLANTED_RAW_LOG_ODDS", "PLANTED", "ESTIMATED", "N_ADS_WITH",
                   "MATCH", "SIZE_MATCH", "LOW_N_FLAG"]].to_string(index=False))
        big = out[out.LOW_N_FLAG == ""]
        print(f"\nRecovery (direction): {out.DIRECTION_MATCH.sum()}/{len(out)} = {out.DIRECTION_MATCH.mean() * 100:.0f}%"
              f"  | n>=30 only: {big.DIRECTION_MATCH.sum()}/{len(big)} = {big.DIRECTION_MATCH.mean() * 100:.0f}%")
        print(f"Recovery (size within tolerance): {out.SIZE_MATCH.sum()}/{len(out)} = {out.SIZE_MATCH.mean() * 100:.0f}%")
        cur.execute(f"SHOW GRANTS ON TABLE {S}.EFFECT_RECOVERY")
        print("Grants on EFFECT_RECOVERY:", [(g[1], g[5]) for g in cur.fetchall()])
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
