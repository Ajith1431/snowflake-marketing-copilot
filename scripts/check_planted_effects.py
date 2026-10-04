"""
Check every planted effect in ground_truth_effects.json against MARKETING_COPILOT.CREATIVE.

Method: rate = SUM(numerator)/SUM(denominator) per ad (or per ad within a cell subset), then compare the
mean ad-level rate for ads WITH vs WITHOUT the attribute value inside the stratum the effect applies to.
"Without" = other values of the same attribute family in the same stratum. Read-only: no data is changed.

Usage: python scripts/check_planted_effects.py
"""

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import snowflake.connector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from env_keys import get_secret  # noqa: E402

S = "MARKETING_COPILOT.CREATIVE"
DATA = ROOT / "data" / "samples" / "creative"
GT = json.loads((ROOT / "tests" / "fixtures" / "ground_truth_effects.json").read_text())  # answer key; never loaded into Snowflake
SMALL_N = 30
NEAR_ZERO_PCT = 5.0  # planted ~0 effects "match" when |observed lift| is within this band

AD_SQL = f"""
WITH w AS (
  SELECT ad_id,
         SUM(impressions) impr, SUM(clicks) clk, SUM(video_views) vv, SUM(video_p100) p100,
         SUM(conversions) conv, SUM(spend) spend,
         SUM(IFF(age_group IN ('25-34','35-44'), clicks, 0))       clk_core,
         SUM(IFF(age_group IN ('25-34','35-44'), impressions, 0))  impr_core,
         SUM(IFF(age_group IN ('25-34','35-44'), 0, clicks))       clk_other,
         SUM(IFF(age_group IN ('25-34','35-44'), 0, impressions))  impr_other,
         SUM(IFF(frequency > 6, clicks, 0))        clk_hi,  SUM(IFF(frequency > 6, impressions, 0))  impr_hi,
         SUM(IFF(frequency > 6, 0, clicks))        clk_lo,  SUM(IFF(frequency > 6, 0, impressions))  impr_lo,
         AVG(IFF(frequency > 6, frequency - 6, NULL))  avg_excess_freq,
         COUNT(DISTINCT week) n_weeks
  FROM {S}.FACT_AD_WEEKLY GROUP BY ad_id
),
a AS (
  SELECT * FROM {S}.FACT_AD_ATTRIBUTE
  PIVOT (MAX(value) FOR attribute_family IN ('hook_type','headline_tone','cta_tone','background','color_temp',
                                             'has_person','word_count_group','has_logo_first_3s'))
    AS p (ad_id, hook_type, headline_tone, cta_tone, background, color_temp, has_person, word_count_group, has_logo_first_3s)
)
SELECT d.*, a.hook_type, a.headline_tone, a.cta_tone, a.background, a.color_temp, a.has_person,
       a.word_count_group, a.has_logo_first_3s, w.*  EXCLUDE (ad_id)
FROM {S}.DIM_AD d JOIN a USING (ad_id) JOIN w USING (ad_id)
"""

RECON_SQL = f"""
WITH cell AS (
  SELECT ad_id, SUM(impressions) i, SUM(clicks) c, SUM(spend) s FROM {S}.FACT_AD_WEEKLY GROUP BY ad_id
),
by_week AS (
  SELECT ad_id, SUM(i) i, SUM(c) c, SUM(s) s FROM (
    SELECT ad_id, week, SUM(impressions) i, SUM(clicks) c, SUM(spend) s FROM {S}.FACT_AD_WEEKLY GROUP BY 1, 2)
  GROUP BY ad_id
),
by_age AS (
  SELECT ad_id, SUM(i) i, SUM(c) c, SUM(s) s FROM (
    SELECT ad_id, age_group, SUM(impressions) i, SUM(clicks) c, SUM(spend) s FROM {S}.FACT_AD_WEEKLY GROUP BY 1, 2)
  GROUP BY ad_id
),
by_gender AS (
  SELECT ad_id, SUM(i) i, SUM(c) c, SUM(s) s FROM (
    SELECT ad_id, gender, SUM(impressions) i, SUM(clicks) c, SUM(spend) s FROM {S}.FACT_AD_WEEKLY GROUP BY 1, 2)
  GROUP BY ad_id
)
SELECT COUNT(*) ads,
  COUNT_IF(cell.i <> w.i OR cell.c <> w.c OR cell.s <> w.s)   mismatch_vs_ad_week_rollup,
  COUNT_IF(cell.i <> a.i OR cell.c <> a.c OR cell.s <> a.s)   mismatch_vs_ad_age_rollup,
  COUNT_IF(cell.i <> g.i OR cell.c <> g.c OR cell.s <> g.s)   mismatch_vs_ad_gender_rollup
FROM cell JOIN by_week w USING (ad_id) JOIN by_age a USING (ad_id) JOIN by_gender g USING (ad_id)
"""


def connect():
    name = os.environ.get("SNOWFLAKE_CONNECTION") or get_secret("SNOWFLAKE_CONNECTION", required=False) or None
    return snowflake.connector.connect(connection_name=name) if name else snowflake.connector.connect()


def query(conn, sql):
    cur = conn.cursor()
    try:
        cur.execute("USE WAREHOUSE MARKETING_WH")
        cur.execute(sql)
        return pd.DataFrame(cur.fetchall(), columns=[c[0].lower() for c in cur.description])
    finally:
        cur.close()


def ratio(num, den):
    return np.where(den > 0, num / den.where(den > 0, 1), np.nan)


def planted(log_odds):
    if abs(log_odds) < 0.05:
        return f"~0 ({log_odds:+.2f} log-odds)"
    return f"{log_odds:+.2f} log-odds (~{(np.exp(log_odds) - 1) * 100:+.0f}%)"


def compare(df, metric, stratum_mask, family, value):
    s = df[stratum_mask & df[metric].notna()]
    with_, without = s[s[family] == value], s[s[family] != value]
    if len(with_) == 0 or len(without) == 0:
        return np.nan, len(with_), len(without)
    return (with_[metric].mean() / without[metric].mean() - 1) * 100, len(with_), len(without)


def main():
    conn = connect()
    try:
        ads = query(conn, AD_SQL)
        recon = query(conn, RECON_SQL)
    finally:
        conn.close()

    num_cols = [c for c in ads.columns if ads[c].dtype == object and c not in (
        "ad_id", "brand", "market", "objective", "ad_type", "aspect_ratio", "platform", "placement", "start_week",
        "hook_type", "headline_tone", "cta_tone", "background", "color_temp", "has_person", "word_count_group",
        "has_logo_first_3s")]
    ads[num_cols] = ads[num_cols].astype(float)

    ads["ctr"] = ratio(ads.clk, ads.impr)
    ads["ctr_core"] = ratio(ads.clk_core, ads.impr_core)
    ads["ctr_other_ages"] = ratio(ads.clk_other, ads.impr_other)
    ads["vtr"] = np.where(ads.ad_type == "video", ratio(ads.vv, ads.impr), np.nan)
    ads["completion"] = np.where(ads.ad_type == "video", ratio(ads.p100, ads.vv), np.nan)
    ads["cvr"] = ratio(ads.conv, ads.clk)
    ads["is_9x16"] = np.where(ads.aspect_ratio == "9:16", "Y", "N")
    ads["log_spend_wk"] = np.log(ads.spend / ads.n_weeks)
    ads["budget_tier"] = np.where(ads.log_spend_wk >= ads.log_spend_wk.quantile(2 / 3), "top_third", "rest")

    allm = pd.Series(True, index=ads.index)
    B = lambda b: ads.brand == b                      # noqa: E731
    M = lambda m: ads.market == m                     # noqa: E731
    O = lambda o: ads.objective == o                  # noqa: E731
    not_in = ads.market != "IN"

    # (effect_id, metric, stratum label, stratum mask, family, value, planted log-odds, near-zero?)
    effects = [
        ("ctr_base_reels_vs_feed", "ctr", "placement in (feed, reels)", ads.placement.isin(["feed", "reels"]), "placement", "reels", -0.35, False),
        ("ctr_base_stories_vs_feed", "ctr", "placement in (feed, stories)", ads.placement.isin(["feed", "stories"]), "placement", "stories", -0.65, False),
        ("ctr_base_link_clicks_vs_awareness", "ctr", "objective in (AWARENESS, LINK_CLICKS)", ads.objective.isin(["AWARENESS", "LINK_CLICKS"]), "objective", "LINK_CLICKS", 0.60, False),
        ("ctr_base_leads_vs_awareness", "ctr", "objective in (AWARENESS, LEADS)", ads.objective.isin(["AWARENESS", "LEADS"]), "objective", "LEADS", 0.30, False),
        ("person_on_camera | Nike", "ctr", "brand = Nike", B("Nike"), "hook_type", "person_on_camera", 0.45, False),
        ("person_on_camera | Pepsi", "ctr", "brand = Pepsi", B("Pepsi"), "hook_type", "person_on_camera", 0.25, False),
        ("person_on_camera | Samsung", "ctr", "brand = Samsung", B("Samsung"), "hook_type", "person_on_camera", 0.25, False),
        ("promo_led | LINK_CLICKS", "ctr", "objective = LINK_CLICKS", O("LINK_CLICKS"), "hook_type", "promo_led", 0.30, False),
        ("promo_led | AWARENESS", "ctr", "objective = AWARENESS", O("AWARENESS"), "hook_type", "promo_led", 0.02, True),
        ("promo_led | LEADS", "ctr", "objective = LEADS", O("LEADS"), "hook_type", "promo_led", 0.15, False),
        ("urgent | UK (Pepsi, Samsung)", "ctr", "market = UK, brand <> Nike", M("UK") & ~B("Nike"), "headline_tone", "urgent", -0.40, False),
        ("urgent | US (Pepsi, Samsung)", "ctr", "market = US, brand <> Nike", M("US") & ~B("Nike"), "headline_tone", "urgent", 0.15, False),
        ("urgent | UK, Nike", "ctr", "market = UK, brand = Nike", M("UK") & B("Nike"), "headline_tone", "urgent", -0.60, False),
        ("urgent | US, Nike", "ctr", "market = US, brand = Nike", M("US") & B("Nike"), "headline_tone", "urgent", 0.30, False),
        ("word_count 11+ | Nike, Pepsi", "ctr", "brand in (Nike, Pepsi)", ~B("Samsung"), "word_count_group", "11+", -0.20, False),
        ("word_count 11+ | Samsung", "ctr", "brand = Samsung", B("Samsung"), "word_count_group", "11+", -0.08, False),
        ("warm | ages 25-44 (Nike, Samsung)", "ctr_core", "age 25-44 cells, brand <> Pepsi", ~B("Pepsi"), "color_temp", "warm", 0.10, False),
        ("warm | other ages (Nike, Samsung)", "ctr_other_ages", "age not 25-44, brand <> Pepsi", ~B("Pepsi"), "color_temp", "warm", 0.00, True),
        ("warm | Pepsi, ages 25-44", "ctr_core", "age 25-44 cells, brand = Pepsi", B("Pepsi"), "color_temp", "warm", 0.25, False),
        ("warm | Pepsi, other ages", "ctr_other_ages", "age not 25-44, brand = Pepsi", B("Pepsi"), "color_temp", "warm", 0.15, False),
        ("logo_first_3s | AWARENESS (Nike, Samsung)", "ctr", "objective = AWARENESS, brand <> Pepsi", O("AWARENESS") & ~B("Pepsi"), "has_logo_first_3s", "Y", 0.10, False),
        ("logo_first_3s | AWARENESS, Pepsi", "ctr", "objective = AWARENESS, brand = Pepsi", O("AWARENESS") & B("Pepsi"), "has_logo_first_3s", "Y", 0.25, False),
        ("logo_first_3s | not AWARENESS", "ctr", "objective <> AWARENESS", ~O("AWARENESS"), "has_logo_first_3s", "Y", 0.00, True),
        ("ugc_style | Nike", "ctr", "brand = Nike", B("Nike"), "hook_type", "ugc_style", 0.30, False),
        ("playful | Pepsi", "ctr", "brand = Pepsi", B("Pepsi"), "headline_tone", "playful", 0.35, False),
        ("product_led | Samsung", "ctr", "brand = Samsung", B("Samsung"), "hook_type", "product_led", 0.25, False),
        ("informational headline | Samsung", "ctr", "brand = Samsung", B("Samsung"), "headline_tone", "informational", 0.20, False),
        ("budget top third (confounder)", "ctr", "all ads", allm, "budget_tier", "top_third", 0.12, False),
        ("IN: person_on_camera (x0.15)", "ctr", "market = IN", M("IN"), "hook_type", "person_on_camera", 0.25 * 0.15, True),
        ("IN: word_count 11+ (x0.15)", "ctr", "market = IN", M("IN"), "word_count_group", "11+", -0.20 * 0.15, True),
        ("IN: product_led, Samsung (x0.15)", "ctr", "market = IN, brand = Samsung", M("IN") & B("Samsung"), "hook_type", "product_led", 0.25 * 0.15, True),
        ("vtr: person_on_camera", "vtr", "video ads", allm, "hook_type", "person_on_camera", 0.20, False),
        ("vtr: ugc_style", "vtr", "video ads", allm, "hook_type", "ugc_style", 0.15, False),
        ("vtr: logo_first_3s", "vtr", "video ads", allm, "has_logo_first_3s", "Y", -0.15, False),
        ("vtr: word_count 11+", "vtr", "video ads", allm, "word_count_group", "11+", -0.10, False),
        ("completion: 9:16", "completion", "video ads", allm, "is_9x16", "Y", 0.20, False),
        ("completion: person_on_camera", "completion", "video ads", allm, "hook_type", "person_on_camera", 0.10, False),
        ("cvr: transactional CTA", "cvr", "all ads (excl. IN)", not_in, "cta_tone", "transactional", 0.30, False),
        ("cvr: promo_led", "cvr", "all ads (excl. IN)", not_in, "hook_type", "promo_led", 0.20, False),
    ]

    rows = []
    for eid, metric, label, mask, fam, val, lo, near_zero in effects:
        lift, n_w, n_wo = compare(ads, metric, mask, fam, val)
        if near_zero:
            match = "Y" if abs(lift) <= NEAR_ZERO_PCT else "N"
        else:
            match = "Y" if np.sign(lift) == np.sign(lo) else "N"
        rows.append({"effect_id": eid, "metric": metric, "stratum": label, "planted_direction_and_size": planted(lo),
                     "observed_lift_%": round(lift, 1), "n_ads_with": n_w, "n_ads_without": n_wo,
                     "direction_match": match, "low_n_flag": "n<30" if n_w < SMALL_N else ""})

    # frequency > 6: within-ad comparison of high- vs low-frequency cells
    f = ads[(ads.impr_hi > 0) & (ads.impr_lo > 0)]
    hi, lo_ = ratio(f.clk_hi, f.impr_hi), ratio(f.clk_lo, f.impr_lo)
    excess = f.avg_excess_freq.mean()
    lift = (np.nanmean(hi) / np.nanmean(lo_) - 1) * 100
    rows.append({"effect_id": "frequency > 6 (-0.15 per unit)", "metric": "ctr",
                 "stratum": "within-ad: cells freq>6 vs freq<=6", "planted_direction_and_size":
                 f"-0.15/unit x avg excess {excess:.2f} = {-0.15 * excess:+.2f} log-odds (~{(np.exp(-0.15 * excess) - 1) * 100:+.0f}%)",
                 "observed_lift_%": round(lift, 1), "n_ads_with": len(f),
                 "n_ads_without": int(((ads.impr_hi == 0) | (ads.impr_lo == 0)).sum()),
                 "direction_match": "Y" if lift < 0 else "N", "low_n_flag": "n<30" if len(f) < SMALL_N else ""})

    out = pd.DataFrame(rows)
    pd.set_option("display.width", 250, "display.max_colwidth", 60, "display.max_rows", 100)
    print(out.to_string(index=False))
    m = (out.direction_match == "Y").mean() * 100
    big = out[out.low_n_flag == ""]
    print(f"\nDirection match: {(out.direction_match == 'Y').sum()}/{len(out)} = {m:.0f}%  "
          f"(excluding n<30 rows: {(big.direction_match == 'Y').sum()}/{len(big)} = {(big.direction_match == 'Y').mean() * 100:.0f}%)")
    out.to_csv(DATA / "planted_effects_check.csv", index=False)

    # reconciliation: Snowflake ad-level totals vs weekly rollups, and vs the local CSV
    print("\nReconciliation in Snowflake (cell sums vs ad-week / ad-age / ad-gender rollups):")
    print(recon.to_string(index=False))
    local = pd.read_csv(DATA / "fact_ad_weekly.csv").groupby("ad_id")[["impressions", "clicks", "spend"]].sum()
    sf = ads.set_index("ad_id")[["impr", "clk", "spend"]].rename(columns={"impr": "impressions", "clk": "clicks"})
    joined = local.join(sf, rsuffix="_sf", how="outer")
    bad = joined[(joined.impressions != joined.impressions_sf) | (joined.clicks != joined.clicks_sf)
                 | ((joined.spend - joined.spend_sf).abs() > 0.005)]
    print(f"Snowflake ad totals vs local fact_ad_weekly.csv: {len(joined)} ads compared, {len(bad)} mismatches")
    print(f"Grand totals (Snowflake): impressions={int(sf.impressions.sum()):,}  clicks={int(sf.clicks.sum()):,}  spend=${sf.spend.sum():,.2f}")


if __name__ == "__main__":
    main()
