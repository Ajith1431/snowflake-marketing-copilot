"""
Snowflake procedure handler: CREATIVE.SCORE_AD(PAYLOAD VARIANT) -> VARIANT

Payload: {"brand","market","objective","placement", optional "ad_type","aspect_ratio","platform",
          "attributes": {family: value}, "budget": weekly spend USD, optional "weeks_since_start", "frequency"}
Returns a scenario estimate (synthetic data): predicted CTR, p10, p90 and the top contributing attributes.
"""

import io

import joblib
import numpy as np
import pandas as pd

STAGE_FILE = "@MARKETING_COPILOT.CREATIVE.MODEL_STAGE/ctr_model.joblib"
_BUNDLE = None


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def bundle(session):
    global _BUNDLE
    if _BUNDLE is None:
        with session.file.get_stream(STAGE_FILE) as f:
            _BUNDLE = joblib.load(io.BytesIO(f.read()))
    return _BUNDLE


def build_row(b, payload):
    p = {str(k).lower(): v for k, v in (payload or {}).items()}
    attrs = {str(k).lower(): str(v) for k, v in (p.get("attributes") or {}).items()}
    row, warnings = {}, []
    placement = str(p.get("placement") or b["defaults"]["placement"])
    implied = {"ad_type": "video" if placement in ("reels", "stories") else b["defaults"]["ad_type"],
               "aspect_ratio": "9:16" if placement in ("reels", "stories") else b["defaults"]["aspect_ratio"]}
    for c in b["cats"]:
        val = attrs.get(c, p.get(c))
        if val is None:
            val = implied.get(c, b["defaults"][c])
        val = str(val)
        if val not in b["levels"][c]:
            warnings.append(f"unknown {c}='{val}', using '{b['defaults'][c]}'")
            val = b["defaults"][c]
        row[c] = val
    budget = float(p.get("budget") or 1500.0)
    if budget <= 0:
        raise ValueError("budget must be positive (weekly spend in USD)")
    weeks = float(p.get("weeks_since_start", 2))
    c0, c1, c2 = b["freq_coef"]
    freq = float(p["frequency"]) if p.get("frequency") is not None else max(1.0, c0 + c1 * np.log(budget) + c2 * weeks)
    row.update({"log_spend": np.log(budget), "frequency": freq, "freq_over6": max(0.0, freq - 6.0),
                "weeks_since_start": weeks})
    return row, budget, warnings


def run(session, payload):
    b = bundle(session)
    row, budget, warnings = build_row(b, payload)
    X = pd.DataFrame([row])[b["features"]]
    m = b["models"]
    pred = float(sigmoid(m[b["chosen"]].predict(X)[0]))
    lo_q, hi_q = sorted([float(m["hgb_q10"].predict(X)[0]), float(m["hgb_q90"].predict(X)[0])])
    qhat = float(b.get("qhat", 0.0))  # conformal widening (log-odds) learned on calibration weeks
    q10, q90 = float(sigmoid(lo_q - qhat)), float(sigmoid(hi_q + qhat))
    widened = pred < q10 or pred > q90
    p10, p90 = min(q10, pred), max(q90, pred)

    drivers = []
    for fam in b["families"]:
        c = b["contrib"][fam].get(row[fam])
        if c is not None:
            drivers.append({"attribute": fam, "value": row[fam], "log_odds_vs_average_ad": round(c, 4),
                            "approx_ctr_effect_pct": round((np.exp(c) - 1) * 100, 1)})
    drivers.sort(key=lambda d: abs(d["log_odds_vs_average_ad"]), reverse=True)

    return {
        "predicted_ctr": round(pred, 6), "p10": round(p10, 6), "p90": round(p90, 6),
        "interval_widened_to_include_prediction": widened,
        "point_model": b["chosen"], "interval_model": "HistGradientBoosting quantile (p10/p90), conformally calibrated",
        "top_drivers": drivers[:3], "all_attribute_effects": drivers,
        "inputs_used": {**{k: row[k] for k in b["cats"]}, "weekly_budget": budget,
                        "frequency": round(row["frequency"], 2), "weeks_since_start": row["weeks_since_start"]},
        "warnings": warnings,
        "disclaimer": "Scenario estimate from a model trained on illustrative synthetic data; brand names are labels only. Not a forecast.",
    }
