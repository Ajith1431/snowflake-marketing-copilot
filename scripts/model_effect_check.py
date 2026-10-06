"""
Local only: does the deployed CTR model reproduce planted effects? Writes CREATIVE.MODEL_EFFECT_CHECK.

For each effect we build a typical ad for the stratum (modal values of the other attributes among the
stratum's ads, median weekly spend, feed placement, LINK_CLICKS unless the effect sets them, modal market
unless the effect sets it), score scenario A and B with CREATIVE.SCORE_AD and compare
  model lift   = predicted_ctr(B) / predicted_ctr(A) - 1
  planted lift = exp(planted log-odds difference) - 1, from the generator's own effect functions
                 (age-specific effects weighted by the brand's segment mix; market scaling applied).
direction_match: same sign; when |planted| < 0.03 log-odds, match means |model log-ratio| <= 0.10.
ratio = model lift / planted lift (null when the planted lift is ~0).

The answer key and generator are read locally only; the table is not granted to agent or MCP roles.
Usage: python scripts/model_effect_check.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import effect_recovery as er  # noqa: E402  (adds src paths, loads generator + answer key)
from common import BRANDS, FAMILIES  # noqa: E402

S = "MARKETING_COPILOT.CREATIVE"
gen = er.gen
NEAR_ZERO = 0.03

# (effect, brand or None for each brand, fixed context, family, A value, B value)
EFFECTS = [
    ("urgent vs conversational", "Nike", {"market": "UK"}, "headline_tone", "conversational", "urgent"),
    ("urgent vs conversational", "Nike", {"market": "US"}, "headline_tone", "conversational", "urgent"),
    ("person_on_camera vs promo_led", None, {}, "hook_type", "promo_led", "person_on_camera"),
    ("promo_led vs product_led", None, {"objective": "LINK_CLICKS"}, "hook_type", "product_led", "promo_led"),
    ("promo_led vs product_led", None, {"objective": "AWARENESS"}, "hook_type", "product_led", "promo_led"),
    ("logo Y vs N", None, {"objective": "AWARENESS"}, "has_logo_first_3s", "N", "Y"),
    ("logo Y vs N", None, {"objective": "LINK_CLICKS"}, "has_logo_first_3s", "N", "Y"),
    ("warm vs neutral", "Pepsi", {}, "color_temp", "neutral", "warm"),
    ("word_count 11+ vs 6-10", None, {}, "word_count_group", "6-10", "11+"),
    ("stories vs feed", None, {}, "placement", "feed", "stories"),
]


def planted_log_odds(brand, market, objective, placement, attrs):
    ad = type("Ad", (), {"brand": brand, "market": market, "objective": objective, "aspect_ratio": None})
    alpha = np.array(gen.SEGMENT_ALPHA[brand], float)
    w = alpha / alpha.sum()
    ages = [a for a in gen.AGE_GROUPS for _ in gen.GENDERS]
    attr = float(sum(wi * gen.ctr_attribute_effect(ad, attrs, age) for wi, age in zip(w, ages)))
    return (gen.CTR_BASE_PLACEMENT[placement] + gen.CTR_BASE_OBJECTIVE[objective]
            + gen.market_scale(ad) * attr)


def main():
    conn = er.connect()
    cur = conn.cursor()
    try:
        cur.execute("USE WAREHOUSE MARKETING_WH")
        ads = er.fetch(cur, er.AD_SQL)
        ads["spend_wk"] = ads.spend / ads.n_weeks

        def score(payload):
            cur.execute(f"CALL {S}.SCORE_AD(PARSE_JSON(%s))", (json.dumps(payload, sort_keys=True),))
            return json.loads(cur.fetchone()[0])["predicted_ctr"]

        rows = []
        for eff, brand_fixed, ctx, fam, a_val, b_val in EFFECTS:
            for brand in ([brand_fixed] if brand_fixed else BRANDS):
                sub = ads[ads.brand == brand]
                if "market" in ctx:
                    sub = sub[sub.market == ctx["market"]]
                if "objective" in ctx:
                    sub = sub[sub.objective == ctx["objective"]]
                market = ctx.get("market", sub.market.mode().iloc[0])
                objective = ctx.get("objective", "LINK_CLICKS")
                attrs = {f: sub[f].mode().iloc[0] for f in FAMILIES}
                base = {"brand": brand, "market": market, "objective": objective, "placement": "feed",
                        "budget": int(round(float(sub.spend_wk.median()), -1))}
                scen = {}
                for lab, val in (("A", a_val), ("B", b_val)):
                    p = {**base, "attributes": dict(attrs)}
                    if fam == "placement":
                        p["placement"] = val
                    else:
                        p["attributes"][fam] = val
                    scen[lab] = p
                pa, pb = score(scen["A"]), score(scen["B"])
                la = planted_log_odds(brand, market, objective, scen["A"]["placement"], scen["A"]["attributes"])
                lb = planted_log_odds(brand, market, objective, scen["B"]["placement"], scen["B"]["attributes"])
                d_pl, d_md = lb - la, float(np.log(pb / pa))
                planted, model = (np.exp(d_pl) - 1) * 100, (pb / pa - 1) * 100
                near_zero = abs(d_pl) < NEAR_ZERO
                match = abs(d_md) <= 0.10 if near_zero else np.sign(d_md) == np.sign(d_pl)
                ratio = None if near_zero else model / planted
                stratum = f"{brand} · {market} · {objective}"
                rows.append({"EFFECT": eff, "STRATUM": stratum, "BRAND": brand, "MARKET": market, "OBJECTIVE": objective,
                             "BUDGET": base["budget"], "PLANTED_LIFT_PCT": round(planted, 1),
                             "MODEL_LIFT_PCT": round(model, 1), "DIRECTION_MATCH": bool(match),
                             "RATIO_MODEL_TO_PLANTED": None if ratio is None else round(ratio, 2),
                             "SHRUNK_MORE_THAN_HALF": bool(ratio is not None and ratio < 0.5)})
        out = pd.DataFrame(rows)

        cur.execute(f"""CREATE OR REPLACE TABLE {S}.MODEL_EFFECT_CHECK (
            EFFECT VARCHAR, STRATUM VARCHAR, BRAND VARCHAR, MARKET VARCHAR, OBJECTIVE VARCHAR, BUDGET INT,
            PLANTED_LIFT_PCT FLOAT, MODEL_LIFT_PCT FLOAT, DIRECTION_MATCH BOOLEAN, RATIO_MODEL_TO_PLANTED FLOAT,
            SHRUNK_MORE_THAN_HALF BOOLEAN)
            COMMENT = 'Planted vs model-implied lifts via SCORE_AD (derived from the answer key). Owner only.'""")
        cur.executemany(f"INSERT INTO {S}.MODEL_EFFECT_CHECK VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        [tuple(None if (isinstance(v, float) and np.isnan(v)) else v for v in r)
                         for r in out.itertuples(index=False)])

        pd.set_option("display.width", 220, "display.max_rows", 100)
        print(out[["EFFECT", "STRATUM", "PLANTED_LIFT_PCT", "MODEL_LIFT_PCT", "DIRECTION_MATCH",
                   "RATIO_MODEL_TO_PLANTED", "SHRUNK_MORE_THAN_HALF"]].to_string(index=False))
        r = out.RATIO_MODEL_TO_PLANTED.dropna()
        print(f"\nDirection match: {out.DIRECTION_MATCH.sum()}/{len(out)} = {out.DIRECTION_MATCH.mean() * 100:.0f}%")
        print(f"Median ratio model/planted (non-zero planted, n={len(r)}): {r.median():.2f}")
        print("Shrunk by more than half:", out[out.SHRUNK_MORE_THAN_HALF][["EFFECT", "STRATUM"]].values.tolist())
        cur.execute(f"SHOW GRANTS ON TABLE {S}.MODEL_EFFECT_CHECK")
        print("Grants:", [(g[1], g[5]) for g in cur.fetchall()])
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
