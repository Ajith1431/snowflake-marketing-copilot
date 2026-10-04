"""
Synthetic creative-attribute dataset with planted, documented effects.

Outputs (data/samples/creative/):
  dim_ad.csv                 ~600 ads (Nike, Pepsi, Samsung x UAE, KSA, UK, US, IN)
  fact_ad_attribute.csv      long format: ad_id, attribute_family, value
  fact_ad_weekly.csv         grain = ad x week x age_group x gender
  ground_truth_effects.json  every planted effect, noise levels, confounders, holdout R2 check

Usage: python data/generators/generate_creative.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)
OUT = Path(__file__).resolve().parent.parent / "samples" / "creative"

BRANDS = ["Nike", "Pepsi", "Samsung"]
ADS_PER_BRAND = 200
MARKETS = ["UAE", "KSA", "UK", "US", "IN"]
MARKET_P = [0.18, 0.17, 0.22, 0.25, 0.18]
OBJECTIVES = ["AWARENESS", "LINK_CLICKS", "LEADS"]
AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
GENDERS = ["F", "M"]
WEEK0 = pd.Timestamp("2025-01-06")  # Monday of ISO week 2
N_WEEKS = 52
HOLDOUT_FROM_WEEK = 42              # weeks 42-51 (last ~20% of the calendar) form the time-based holdout

# ---------------------------------------------------------------------------- planted effects
# All CTR / VTR / CVR effects are on the log-odds scale and additive.
CTR_BASE_PLACEMENT = {"feed": -4.20, "reels": -4.55, "stories": -4.85}
CTR_BASE_OBJECTIVE = {"AWARENESS": -0.30, "LINK_CLICKS": 0.30, "LEADS": 0.00}
CTR_BUDGET_PER_SD = 0.12            # confounder: bigger budgets get better targeting/production
FREQ_THRESHOLD, FREQ_PER_UNIT = 6.0, -0.15
WEAK_MARKET, WEAK_MARKET_SCALE = "IN", 0.15   # IN: every attribute effect shrunk to 15%

VTR_BASE = -0.90                    # 3-second view rate, video ads only
VTR_PLACEMENT = {"feed": 0.0, "reels": 0.30, "stories": 0.10}
COMPLETION_BASE = -1.20             # video_p100 / video_views

CVR_BASE_OBJECTIVE = {"AWARENESS": -4.00, "LINK_CLICKS": -3.20, "LEADS": -2.20}
ORDER_VALUE = {"Nike": 95.00, "Pepsi": 18.00, "Samsung": 420.00}

# Noise (log-odds). Tuned so the true-effects model scores R2 ~0.45-0.55 on the holdout.
NOISE = {
    "ctr": {"ad_sd": 0.30, "ad_week_sd": 0.22, "cell_sd": 0.33},
    "vtr": {"ad_sd": 0.25, "ad_week_sd": 0.15, "cell_sd": 0.30},
    "completion": {"ad_sd": 0.25, "ad_week_sd": 0.10, "cell_sd": 0.25},
    "cvr": {"ad_sd": 0.30, "ad_week_sd": 0.15, "cell_sd": 0.30},
}

ATTR_PROBS = {
    # hook_type is budget-dependent (see sample_hook); these are base weights
    "hook_type": {"promo_led": 0.33, "product_led": 0.38, "person_on_camera": 0.25, "ugc_style": 0.04},
    "headline_tone": {"urgent": 0.26, "informational": 0.36, "conversational": 0.345, "playful": 0.035},
    "cta_tone": {"transactional": 0.60, "informational": 0.40},
    "background": {"studio": 0.35, "home": 0.32, "outdoor": 0.29, "retail": 0.04},
    "color_temp": {"warm": 0.40, "cool": 0.35, "neutral": 0.25},
    "word_count_group": {"0-5": 0.35, "6-10": 0.45, "11+": 0.20},
    "has_logo_first_3s": {"Y": 0.45, "N": 0.55},
}
PERSON_ON_CAMERA_BUDGET_LOGIT = 0.90  # per SD of log budget: high budget -> person_on_camera
PLAYFUL_P = {"Nike": 0.01, "Pepsi": 0.09, "Samsung": 0.005}  # rare overall (<5%), concentrated in Pepsi

SEGMENT_ALPHA = {  # Dirichlet concentration over age x gender (12 cells, F then M per age)
    "Nike":    [9, 10, 11, 12, 7, 8, 4, 4, 2, 2, 1, 1],
    "Pepsi":   [10, 9, 10, 9, 7, 7, 5, 5, 3, 3, 2, 2],
    "Samsung": [5, 6, 8, 10, 8, 10, 6, 8, 4, 5, 2, 2],
}
CPM_PLACEMENT = {"feed": 9.0, "reels": 7.0, "stories": 6.0}
CPM_MARKET = {"UAE": 1.10, "KSA": 1.00, "UK": 1.10, "US": 1.20, "IN": 0.40}


def logistic(x):
    return 1.0 / (1.0 + np.exp(-x))


# ---------------------------------------------------------------------------- dim_ad
def build_ads():
    rows = []
    for brand in BRANDS:
        for _ in range(ADS_PER_BRAND):
            platform = rng.choice(["instagram", "facebook"], p=[0.6, 0.4])
            placement = rng.choice(["feed", "reels", "stories"],
                                   p=[0.45, 0.30, 0.25] if platform == "instagram" else [0.60, 0.15, 0.25])
            ad_type = "video" if placement in ("reels", "stories") and rng.random() < 0.85 else rng.choice(
                ["video", "image"], p=[0.45, 0.55])
            if placement in ("reels", "stories"):
                aspect = "9:16"
            else:
                aspect = rng.choice(["4:5", "1:1"], p=[0.6, 0.4] if ad_type == "video" else [0.5, 0.5])
            start = int(rng.integers(0, N_WEEKS - 4))
            duration = int(min(rng.integers(4, 9), N_WEEKS - start))
            rows.append({
                "brand": brand, "market": rng.choice(MARKETS, p=MARKET_P),
                "objective": rng.choice(OBJECTIVES, p=[0.40, 0.40, 0.20]),
                "ad_type": ad_type, "aspect_ratio": aspect, "platform": platform, "placement": placement,
                "start_idx": start, "duration": duration,
                # latent (not exported): weekly budget drives spend, hook choice and CTR
                "weekly_budget": float(rng.lognormal(np.log({"Nike": 1800, "Pepsi": 1500, "Samsung": 2200}[brand]), 0.6)),
            })
    ads = pd.DataFrame(rows)
    ads.insert(0, "ad_id", [f"AD{i:04d}" for i in range(1, len(ads) + 1)])
    ads["start_week"] = (WEEK0 + pd.to_timedelta(ads["start_idx"] * 7, unit="D")).dt.date
    log_b = np.log(ads["weekly_budget"])
    ads["budget_z"] = (log_b - log_b.mean()) / log_b.std()
    return ads


def sample_hook(budget_z):
    names = list(ATTR_PROBS["hook_type"])
    w = np.array([ATTR_PROBS["hook_type"][n] for n in names])
    w[names.index("person_on_camera")] *= np.exp(PERSON_ON_CAMERA_BUDGET_LOGIT * budget_z)
    return rng.choice(names, p=w / w.sum())


def build_attributes(ads):
    attrs = []
    for ad in ads.itertuples():
        hook = sample_hook(ad.budget_z)
        p_playful = PLAYFUL_P[ad.brand]
        tones = {k: v * (1 - p_playful) / (1 - ATTR_PROBS["headline_tone"]["playful"])
                 for k, v in ATTR_PROBS["headline_tone"].items() if k != "playful"}
        tones["playful"] = p_playful
        cta_p = [0.35, 0.65] if ad.objective == "AWARENESS" else [0.70, 0.30]
        a = {
            "hook_type": hook,
            "headline_tone": rng.choice(list(tones), p=np.array(list(tones.values())) / sum(tones.values())),
            "cta_tone": rng.choice(["transactional", "informational"], p=cta_p),
            "background": rng.choice(list(ATTR_PROBS["background"]), p=list(ATTR_PROBS["background"].values())),
            "color_temp": rng.choice(list(ATTR_PROBS["color_temp"]), p=list(ATTR_PROBS["color_temp"].values())),
            "has_person": "Y" if hook in ("person_on_camera", "ugc_style") or rng.random() < 0.25 else "N",
            "word_count_group": rng.choice(list(ATTR_PROBS["word_count_group"]),
                                           p=list(ATTR_PROBS["word_count_group"].values())),
            "has_logo_first_3s": rng.choice(["Y", "N"], p=[0.45, 0.55]),
        }
        for fam, val in a.items():
            attrs.append({"ad_id": ad.ad_id, "attribute_family": fam, "value": str(val)})
    return pd.DataFrame(attrs)


# ---------------------------------------------------------------------------- effects
def ctr_attribute_effect(ad, a, age):
    """Planted attribute effects on CTR log-odds (before market scaling)."""
    e = 0.0
    hook, tone = a["hook_type"], a["headline_tone"]
    if hook == "person_on_camera":
        e += 0.25
    if hook == "promo_led":
        e += {"LINK_CLICKS": 0.30, "AWARENESS": 0.02, "LEADS": 0.15}[ad.objective]
    if tone == "urgent":
        e += {"UK": -0.40, "US": 0.15}.get(ad.market, 0.0)
    if a["word_count_group"] == "11+":
        e += -0.20
    if a["color_temp"] == "warm" and age in ("25-34", "35-44"):
        e += 0.10
    if a["has_logo_first_3s"] == "Y" and ad.objective == "AWARENESS":
        e += 0.10
    # brand-specific increments (added on top of the global effects above)
    if ad.brand == "Nike":
        e += {"person_on_camera": 0.20, "ugc_style": 0.30}.get(hook, 0.0)
        if tone == "urgent":
            e += {"UK": -0.20, "US": 0.15}.get(ad.market, 0.0)
    elif ad.brand == "Pepsi":
        if a["color_temp"] == "warm":
            e += 0.15
        if tone == "playful":
            e += 0.35
        if a["has_logo_first_3s"] == "Y" and ad.objective == "AWARENESS":
            e += 0.15
    elif ad.brand == "Samsung":
        if hook == "product_led":
            e += 0.25
        if tone == "informational":
            e += 0.20
        if a["word_count_group"] == "11+":
            e += 0.12  # net -0.08: long copy hurts Samsung less
    return e


def market_scale(ad):
    return WEAK_MARKET_SCALE if ad.market == WEAK_MARKET else 1.0


def vtr_attribute_effect(ad, a):
    e = {"person_on_camera": 0.20, "ugc_style": 0.15}.get(a["hook_type"], 0.0)
    e += -0.15 if a["has_logo_first_3s"] == "Y" else 0.0
    e += -0.10 if a["word_count_group"] == "11+" else 0.0
    return e


def completion_attribute_effect(ad, a):
    e = 0.20 if ad.aspect_ratio == "9:16" else 0.0
    e += 0.10 if a["hook_type"] == "person_on_camera" else 0.0
    return e


def cvr_attribute_effect(ad, a, age):
    e = 0.30 if a["cta_tone"] == "transactional" else 0.0
    e += 0.20 if a["hook_type"] == "promo_led" else 0.0
    e += 0.15 if age in ("25-34", "35-44") else 0.0
    return e


# ---------------------------------------------------------------------------- fact_ad_weekly
def build_weekly(ads, attrs):
    wide = attrs.pivot(index="ad_id", columns="attribute_family", values="value")
    out = []
    for ad in ads.itertuples():
        a = wide.loc[ad.ad_id]
        shares = rng.dirichlet(np.array(SEGMENT_ALPHA[ad.brand], dtype=float) * 3)
        u = {k: rng.normal(0, NOISE[k]["ad_sd"]) for k in NOISE}
        scale = market_scale(ad)
        for k in range(ad.duration):
            week_idx = ad.start_idx + k
            week_budget = round(ad.weekly_budget * float(np.clip(rng.normal(1, 0.10), 0.7, 1.3)), 2)
            v = {m: rng.normal(0, NOISE[m]["ad_week_sd"]) for m in NOISE}
            # spend reconciles exactly to the ad-week budget (cents)
            cents = np.floor(shares * week_budget * 100).astype(int)
            cents[np.argmax(shares)] += int(round(week_budget * 100)) - cents.sum()
            for i, (age, gender) in enumerate((ag, g) for ag in AGE_GROUPS for g in GENDERS):
                spend = cents[i] / 100
                cpm = CPM_PLACEMENT[ad.placement] * CPM_MARKET[ad.market] * rng.lognormal(0, 0.15)
                impressions = max(int(round(spend / cpm * 1000)), 1 if spend > 0 else 0)
                frequency = float(np.clip(1.3 + 0.9 * k + 0.5 * ad.budget_z + rng.normal(0, 0.6), 1.0, 12.0))

                ctr_det = (CTR_BASE_PLACEMENT[ad.placement] + CTR_BASE_OBJECTIVE[ad.objective]
                           + scale * ctr_attribute_effect(ad, a, age)
                           + CTR_BUDGET_PER_SD * ad.budget_z
                           + FREQ_PER_UNIT * max(0.0, frequency - FREQ_THRESHOLD))
                ctr_logit = ctr_det + u["ctr"] + v["ctr"] + rng.normal(0, NOISE["ctr"]["cell_sd"])
                clicks = int(rng.binomial(impressions, logistic(ctr_logit)))

                video_views = video_p100 = 0
                if ad.ad_type == "video":
                    vtr_logit = (VTR_BASE + VTR_PLACEMENT[ad.placement] + scale * vtr_attribute_effect(ad, a)
                                 + u["vtr"] + v["vtr"] + rng.normal(0, NOISE["vtr"]["cell_sd"]))
                    video_views = int(rng.binomial(impressions, logistic(vtr_logit)))
                    comp_logit = (COMPLETION_BASE + scale * completion_attribute_effect(ad, a)
                                  + u["completion"] + v["completion"] + rng.normal(0, NOISE["completion"]["cell_sd"]))
                    video_p100 = int(rng.binomial(video_views, logistic(comp_logit)))

                cvr_logit = (CVR_BASE_OBJECTIVE[ad.objective] + scale * cvr_attribute_effect(ad, a, age)
                             - 0.05 * max(0.0, frequency - FREQ_THRESHOLD)
                             + u["cvr"] + v["cvr"] + rng.normal(0, NOISE["cvr"]["cell_sd"]))
                conversions = int(rng.binomial(clicks, logistic(cvr_logit)))

                out.append({
                    "ad_id": ad.ad_id, "week": (WEEK0 + pd.Timedelta(weeks=week_idx)).date(),
                    "age_group": age, "gender": gender,
                    "impressions": impressions, "clicks": clicks,
                    "video_views": video_views, "video_p100": video_p100,
                    "spend": spend, "conversions": conversions,
                    "revenue": round(conversions * ORDER_VALUE[ad.brand], 2),
                    "frequency": round(frequency, 2),
                    # evaluation-only columns, dropped before export
                    "_week_idx": week_idx, "_ctr_det": ctr_det, "_ctr_det_ad": ctr_det + u["ctr"],
                })
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------- checks
def holdout_r2(weekly):
    """R2 of the true-effects model on the time-based holdout (cell grain, empirical log-odds CTR)."""
    df = weekly[(weekly["impressions"] >= 200) & (weekly["_week_idx"] >= HOLDOUT_FROM_WEEK)]
    y = np.log((df["clicks"] + 0.5) / (df["impressions"] - df["clicks"] + 0.5))

    def r2(pred):
        return float(1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum())

    return {"holdout_weeks": f">= week index {HOLDOUT_FROM_WEEK}", "holdout_rows": int(len(df)),
            "r2_true_effects_only": round(r2(df["_ctr_det"]), 3),
            "r2_true_effects_plus_known_ad_intercept": round(r2(df["_ctr_det_ad"]), 3)}


def reconcile(ads, weekly):
    assert (weekly["clicks"] <= weekly["impressions"]).all()
    assert (weekly["video_p100"] <= weekly["video_views"]).all()
    assert (weekly["video_views"] <= weekly["impressions"]).all()
    assert (weekly["conversions"] <= weekly["clicks"]).all()
    assert np.allclose(weekly["revenue"], (weekly["conversions"] * weekly["ad_id"].map(
        ads.set_index("ad_id")["brand"]).map(ORDER_VALUE)).round(2))
    per_ad_week = weekly.groupby(["ad_id", "week"]).size()
    assert (per_ad_week == len(AGE_GROUPS) * len(GENDERS)).all(), "every ad-week must have all 12 cells"
    expected_weeks = ads.set_index("ad_id")["duration"]
    assert (weekly.groupby("ad_id")["week"].nunique() == expected_weeks).all()
    first_week = weekly.groupby("ad_id")["week"].min()
    assert (first_week == ads.set_index("ad_id")["start_week"]).all()


def ground_truth(ads, attrs, r2):
    shares = (attrs.groupby(["attribute_family", "value"])["ad_id"].nunique() / len(ads)).round(4)
    rare = [{"attribute_family": f, "value": v, "share_of_ads": float(s)} for (f, v), s in shares.items() if s < 0.05]
    ctr = [
        {"effect": "person_on_camera", "family": "hook_type", "value": "person_on_camera", "condition": "all", "log_odds": 0.25},
        {"effect": "promo_led_link_clicks", "family": "hook_type", "value": "promo_led", "condition": "objective = LINK_CLICKS", "log_odds": 0.30},
        {"effect": "promo_led_awareness", "family": "hook_type", "value": "promo_led", "condition": "objective = AWARENESS", "log_odds": 0.02},
        {"effect": "promo_led_leads", "family": "hook_type", "value": "promo_led", "condition": "objective = LEADS", "log_odds": 0.15,
         "note": "not in the original spec; set halfway between AWARENESS and LINK_CLICKS"},
        {"effect": "urgent_uk", "family": "headline_tone", "value": "urgent", "condition": "market = UK", "log_odds": -0.40},
        {"effect": "urgent_us", "family": "headline_tone", "value": "urgent", "condition": "market = US", "log_odds": 0.15},
        {"effect": "long_copy", "family": "word_count_group", "value": "11+", "condition": "all", "log_odds": -0.20},
        {"effect": "warm_core_ages", "family": "color_temp", "value": "warm", "condition": "age_group in (25-34, 35-44)", "log_odds": 0.10},
        {"effect": "logo_first_3s_awareness", "family": "has_logo_first_3s", "value": "Y", "condition": "objective = AWARENESS", "log_odds": 0.10},
        {"effect": "nike_person_on_camera", "family": "hook_type", "value": "person_on_camera", "condition": "brand = Nike", "log_odds": 0.20, "total_for_condition": 0.45},
        {"effect": "nike_ugc_style", "family": "hook_type", "value": "ugc_style", "condition": "brand = Nike", "log_odds": 0.30},
        {"effect": "nike_urgent_uk", "family": "headline_tone", "value": "urgent", "condition": "brand = Nike AND market = UK", "log_odds": -0.20, "total_for_condition": -0.60},
        {"effect": "nike_urgent_us", "family": "headline_tone", "value": "urgent", "condition": "brand = Nike AND market = US", "log_odds": 0.15, "total_for_condition": 0.30},
        {"effect": "pepsi_warm", "family": "color_temp", "value": "warm", "condition": "brand = Pepsi (all ages)", "log_odds": 0.15,
         "total_for_condition": "0.25 for ages 25-44, 0.15 otherwise"},
        {"effect": "pepsi_playful", "family": "headline_tone", "value": "playful", "condition": "brand = Pepsi", "log_odds": 0.35},
        {"effect": "pepsi_logo_first_3s_awareness", "family": "has_logo_first_3s", "value": "Y", "condition": "brand = Pepsi AND objective = AWARENESS", "log_odds": 0.15, "total_for_condition": 0.25},
        {"effect": "samsung_product_led", "family": "hook_type", "value": "product_led", "condition": "brand = Samsung", "log_odds": 0.25},
        {"effect": "samsung_informational", "family": "headline_tone", "value": "informational", "condition": "brand = Samsung", "log_odds": 0.20},
        {"effect": "samsung_long_copy_offset", "family": "word_count_group", "value": "11+", "condition": "brand = Samsung", "log_odds": 0.12, "total_for_condition": -0.08},
    ]
    return {
        "seed": SEED,
        "scale": "All effects are additive on the log-odds scale. Brand-specific effects are increments on top of the global effects; total_for_condition shows the combined value.",
        "ctr": {
            "base_by_placement": CTR_BASE_PLACEMENT,
            "base_by_objective": CTR_BASE_OBJECTIVE,
            "attribute_effects": ctr,
            "frequency": {"threshold": FREQ_THRESHOLD, "log_odds_per_unit_above": FREQ_PER_UNIT},
            "weak_market": {"market": WEAK_MARKET, "attribute_effect_scale": WEAK_MARKET_SCALE,
                            "note": "In IN every attribute effect (global and brand-specific) is multiplied by 0.15; bases, budget and frequency effects are unchanged."},
            "confounder_budget": {
                "log_odds_per_sd_log_budget": CTR_BUDGET_PER_SD,
                "person_on_camera_selection_logit_per_sd": PERSON_ON_CAMERA_BUDGET_LOGIT,
                "note": "Latent weekly budget is not exported but is observable through spend. High-budget ads are more likely to use person_on_camera AND get higher CTR, so a naive comparison overstates person_on_camera. Budget also raises frequency.",
            },
            "noise_sd": NOISE["ctr"],
        },
        "vtr": {
            "definition": "video_views / impressions (video ads only; image ads have 0 views)",
            "base": VTR_BASE, "placement": VTR_PLACEMENT,
            "attribute_effects": [
                {"family": "hook_type", "value": "person_on_camera", "log_odds": 0.20},
                {"family": "hook_type", "value": "ugc_style", "log_odds": 0.15},
                {"family": "has_logo_first_3s", "value": "Y", "log_odds": -0.15},
                {"family": "word_count_group", "value": "11+", "log_odds": -0.10},
            ],
            "noise_sd": NOISE["vtr"],
        },
        "completion": {
            "definition": "video_p100 / video_views",
            "base": COMPLETION_BASE,
            "attribute_effects": [
                {"family": "aspect_ratio (dim_ad)", "value": "9:16", "log_odds": 0.20},
                {"family": "hook_type", "value": "person_on_camera", "log_odds": 0.10},
            ],
            "noise_sd": NOISE["completion"],
        },
        "conversion_rate": {
            "definition": "conversions / clicks",
            "base_by_objective": CVR_BASE_OBJECTIVE,
            "attribute_effects": [
                {"family": "cta_tone", "value": "transactional", "log_odds": 0.30},
                {"family": "hook_type", "value": "promo_led", "log_odds": 0.20},
                {"family": "age_group", "value": "25-34 or 35-44", "log_odds": 0.15},
            ],
            "frequency": {"threshold": FREQ_THRESHOLD, "log_odds_per_unit_above": -0.05},
            "noise_sd": NOISE["cvr"],
        },
        "revenue": {"definition": "conversions x order_value (fixed per brand)", "order_value": ORDER_VALUE},
        "spend": {"definition": "Ad-week budget split across the 12 age x gender cells by a per-ad Dirichlet share; cells sum exactly to the ad-week budget",
                  "cpm_by_placement": CPM_PLACEMENT, "cpm_market_multiplier": CPM_MARKET},
        "rare_values": rare,
        "holdout_check": r2,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ads = build_ads()
    attrs = build_attributes(ads)
    weekly = build_weekly(ads, attrs)
    reconcile(ads, weekly)
    r2 = holdout_r2(weekly)

    ads[["ad_id", "brand", "market", "objective", "ad_type", "aspect_ratio", "platform", "placement", "start_week"]] \
        .to_csv(OUT / "dim_ad.csv", index=False)
    attrs.to_csv(OUT / "fact_ad_attribute.csv", index=False)
    weekly.drop(columns=[c for c in weekly.columns if c.startswith("_")]).to_csv(OUT / "fact_ad_weekly.csv", index=False)
    (OUT / "ground_truth_effects.json").write_text(json.dumps(ground_truth(ads, attrs, r2), indent=2, default=str))

    print(f"dim_ad: {len(ads)}  fact_ad_attribute: {len(attrs)}  fact_ad_weekly: {len(weekly)}")
    print("holdout R2:", r2)
    print("rare values (<5% of ads):", [(r["attribute_family"], r["value"], r["share_of_ads"]) for r in ground_truth(ads, attrs, r2)["rare_values"]])


if __name__ == "__main__":
    main()
