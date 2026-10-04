"""
Snowflake procedure handler: CREATIVE.TRAIN_CTR_MODEL()

Trains on CREATIVE.V_AD_FEATURES (ad-week grain), last 10 weeks held out:
  baseline   historical CTR by brand x placement (training weeks)
  ridge      one-hot attributes + controls, Ridge on log-odds CTR
  hgb        HistGradientBoostingRegressor on log-odds CTR
  hgb_q10/90 HistGradientBoosting quantile models -> p10 / p90 interval
Writes MODEL_METRICS, MODEL_PREDICTIONS, FEATURE_EFFECTS; saves the bundle to @MODEL_STAGE/ctr_model.joblib.
"""

import json
import os
import tempfile

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from common import FAMILIES, logit_rate

DIMS = ["brand", "market", "objective", "placement", "ad_type", "aspect_ratio", "platform"]
CATS = DIMS + FAMILIES
NUMS = ["log_spend", "frequency", "freq_over6", "weeks_since_start"]
FEATURES = CATS + NUMS
HOLDOUT_WEEKS = 10
CALIBRATION_WEEKS = 8   # last training weeks used to conformalise the p10-p90 interval
TARGET_COVERAGE = 0.80
STAGE = "@MARKETING_COPILOT.CREATIVE.MODEL_STAGE"
SEED = 42


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def load(session):
    df = session.sql("SELECT * FROM MARKETING_COPILOT.CREATIVE.V_AD_FEATURES").to_pandas()
    df.columns = [c.lower() for c in df.columns]
    for c in ["impressions", "clicks", "spend", "frequency", "log_spend", "weeks_since_start"]:
        df[c] = df[c].astype(float)
    df["week"] = pd.to_datetime(df["week"])
    df["freq_over6"] = np.maximum(0.0, df["frequency"] - 6.0)
    df["y"] = logit_rate(df["clicks"], df["impressions"])
    df["ctr"] = df["clicks"] / df["impressions"]
    cut = df["week"].max() - pd.Timedelta(weeks=HOLDOUT_WEEKS - 1)
    df["split"] = np.where(df["week"] >= cut, "holdout", "train")
    return df, cut


def make_ridge():
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), CATS),
                             ("num", StandardScaler(), NUMS)])
    return Pipeline([("pre", pre), ("model", Ridge(alpha=1.0))])


def make_hgb(loss="squared_error", quantile=None):
    pre = ColumnTransformer([("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), CATS),
                             ("num", "passthrough", NUMS)])
    kw = dict(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=40,
              l2_regularization=1.0, random_state=SEED,
              categorical_features=list(range(len(CATS))))
    if quantile is not None:
        kw.update(loss="quantile", quantile=quantile)
    return Pipeline([("pre", pre), ("model", HistGradientBoostingRegressor(**kw))])


def scores(actual, pred):
    actual, pred = np.asarray(actual, float), np.asarray(pred, float)
    mae = float(np.mean(np.abs(actual - pred)))
    pos = actual > 0
    mape = float(np.mean(np.abs(actual[pos] - pred[pos]) / actual[pos]) * 100)
    ss_res = float(np.sum((actual - pred) ** 2))
    ss_tot = float(np.sum((actual - actual.mean()) ** 2))
    return mae, mape, 1 - ss_res / ss_tot, ss_res / len(actual)


def ad_level(h, col):
    g = h.assign(_num=h[col] * h["impressions"]).groupby("ad_id")
    return g["_num"].sum() / g["impressions"].sum()


def ridge_contributions(ridge, train):
    """Per attribute value: coef - share-weighted mean coef of its family (log-odds vs an average ad)."""
    enc = ridge.named_steps["pre"].named_transformers_["cat"]
    coef = ridge.named_steps["model"].coef_
    out = {}
    for j, col in enumerate(CATS):
        levels = list(enc.categories_[j])
        offset = sum(len(c) for c in enc.categories_[:j])
        b = np.array([coef[offset + k] for k in range(len(levels))])
        shares = train[col].astype(str).value_counts(normalize=True).reindex(levels).fillna(0).to_numpy()
        mean_b = float(np.dot(shares, b))
        out[col] = {str(lv): float(b[k] - mean_b) for k, lv in enumerate(levels)}
    return out


def run(session):
    df, cut = load(session)
    tr, ho = df[df.split == "train"], df[df.split == "holdout"]
    Xtr, Xho, Xall = tr[FEATURES], ho[FEATURES], df[FEATURES]

    base_tbl = (tr.groupby(["brand", "placement"])[["clicks", "impressions"]].sum()
                .pipe(lambda t: t["clicks"] / t["impressions"]))
    global_ctr = tr["clicks"].sum() / tr["impressions"].sum()

    def base_pred(d):
        return np.array([base_tbl.get((b, p), global_ctr) for b, p in zip(d["brand"], d["placement"])])

    models = {"ridge": make_ridge(), "hgb": make_hgb(),
              "hgb_q10": make_hgb("quantile", 0.10), "hgb_q90": make_hgb("quantile", 0.90)}
    for name in ["ridge", "hgb"]:
        models[name].fit(Xtr, tr["y"])

    # Conformalised quantile regression: fit quantile models on the earlier training weeks, then widen
    # both bounds by the 80% quantile of the miss on the last CALIBRATION_WEEKS training weeks.
    cal_cut = cut - pd.Timedelta(weeks=CALIBRATION_WEEKS)
    fit, cal = tr[tr.week < cal_cut], tr[tr.week >= cal_cut]
    for name in ["hgb_q10", "hgb_q90"]:
        models[name].fit(fit[FEATURES], fit["y"])
    lo_cal = np.minimum(models["hgb_q10"].predict(cal[FEATURES]), models["hgb_q90"].predict(cal[FEATURES]))
    hi_cal = np.maximum(models["hgb_q10"].predict(cal[FEATURES]), models["hgb_q90"].predict(cal[FEATURES]))
    miss = np.maximum(lo_cal - cal["y"].to_numpy(), cal["y"].to_numpy() - hi_cal)
    level = min(1.0, np.ceil((len(miss) + 1) * TARGET_COVERAGE) / len(miss))
    qhat = float(np.quantile(miss, level))

    preds = {"baseline": base_pred(df)}
    for name in ["ridge", "hgb"]:
        preds[name] = sigmoid(models[name].predict(Xall))
    for k, v in preds.items():
        df[f"pred_{k}"] = v
    q_lo = np.minimum(models["hgb_q10"].predict(Xall), models["hgb_q90"].predict(Xall))
    q_hi = np.maximum(models["hgb_q10"].predict(Xall), models["hgb_q90"].predict(Xall))
    df["p10_raw"], df["p90_raw"] = sigmoid(q_lo), sigmoid(q_hi)
    df["p10"], df["p90"] = sigmoid(q_lo - qhat), sigmoid(q_hi + qhat)
    ho = df[df.split == "holdout"]

    rows = []
    base_mse = {}
    for level in ["ad_week", "ad"]:
        for name in ["baseline", "ridge", "hgb"]:
            if level == "ad_week":
                act, pr, n = ho["ctr"], ho[f"pred_{name}"], len(ho)
            else:
                act, pr = ad_level(ho, "ctr"), ad_level(ho, f"pred_{name}")
                n = len(act)
            mae, mape, r2, mse = scores(act, pr)
            if name == "baseline":
                base_mse[level] = mse
            rows.append({"MODEL": name, "LEVEL": level, "N_HOLDOUT": n, "MAE_CTR_PP": round(mae * 100, 4),
                         "MAPE_PCT": round(mape, 2), "R2": round(r2, 4),
                         "MSE_SKILL_VS_BASELINE": round(1 - mse / base_mse[level], 4), "P10_P90_COVERAGE": None})
        for label, lo_col, hi_col in [("hgb_quantile_p10_p90_raw", "p10_raw", "p90_raw"),
                                      ("hgb_quantile_p10_p90_conformal", "p10", "p90")]:
            if level == "ad_week":
                cov = float(((ho["ctr"] >= ho[lo_col]) & (ho["ctr"] <= ho[hi_col])).mean())
            else:
                a, lo, hi = ad_level(ho, "ctr"), ad_level(ho, lo_col), ad_level(ho, hi_col)
                cov = float(((a >= lo) & (a <= hi)).mean())
            rows.append({"MODEL": label, "LEVEL": level,
                         "N_HOLDOUT": len(ho) if level == "ad_week" else ho.ad_id.nunique(),
                         "MAE_CTR_PP": None, "MAPE_PCT": None, "R2": None, "MSE_SKILL_VS_BASELINE": None,
                         "P10_P90_COVERAGE": round(cov, 4)})
    metrics = pd.DataFrame(rows)
    meta = {"TRAIN_START": str(tr.week.min().date()), "TRAIN_END": str(tr.week.max().date()),
            "HOLDOUT_START": str(ho.week.min().date()), "HOLDOUT_END": str(ho.week.max().date()),
            "N_TRAIN_ROWS": len(tr), "N_HOLDOUT_ROWS": len(ho),
            "CALIBRATION_START": str(cal.week.min().date()), "CONFORMAL_QHAT_LOGODDS": round(qhat, 4)}
    for k, v in meta.items():
        metrics[k] = v

    aw = metrics[(metrics.LEVEL == "ad_week") & metrics.MODEL.isin(["ridge", "hgb"])].set_index("MODEL")["R2"]
    chosen = "hgb" if aw["hgb"] > aw["ridge"] + 0.01 else "ridge"
    metrics["CHOSEN_POINT_MODEL"] = chosen

    pred_df = pd.DataFrame({
        "AD_ID": df["ad_id"], "WEEK": df["week"].dt.date, "SPLIT": df["split"].str.upper(),
        "ACTUAL_CTR": df["ctr"].round(6), "PREDICTED_CTR": df[f"pred_{chosen}"].round(6),
        "P10_CTR": df["p10"].round(6), "P90_CTR": df["p90"].round(6),
        "BASELINE_CTR": df["pred_baseline"].round(6), "RIDGE_CTR": df["pred_ridge"].round(6),
        "HGB_CTR": df["pred_hgb"].round(6), "POINT_MODEL": chosen})

    fe_rows = []
    for name in ["ridge", "hgb"]:
        pi = permutation_importance(models[name], Xho, ho["y"], n_repeats=10, random_state=SEED, scoring="r2")
        for f, mu, sd in zip(FEATURES, pi.importances_mean, pi.importances_std):
            fe_rows.append({"MODEL": name, "FEATURE": f, "IMPORTANCE_R2_DROP": round(float(mu), 5),
                            "IMPORTANCE_STD": round(float(sd), 5)})
    fe = pd.DataFrame(fe_rows)
    fe["RANK"] = fe.groupby("MODEL")["IMPORTANCE_R2_DROP"].rank(ascending=False, method="first").astype(int)

    A = np.column_stack([np.ones(len(tr)), tr["log_spend"], tr["weeks_since_start"]])
    freq_coef = np.linalg.lstsq(A, tr["frequency"].to_numpy(), rcond=None)[0].tolist()
    defaults = {c: str(tr[c].mode().iloc[0]) for c in CATS}
    bundle = {"models": models, "chosen": chosen, "features": FEATURES, "cats": CATS, "nums": NUMS,
              "families": FAMILIES, "freq_coef": freq_coef, "defaults": defaults, "qhat": qhat,
              "levels": {c: sorted(df[c].astype(str).unique().tolist()) for c in CATS},
              "contrib": ridge_contributions(models["ridge"], tr), "meta": meta}
    path = os.path.join(tempfile.gettempdir(), "ctr_model.joblib")
    joblib.dump(bundle, path)
    session.file.put(path, STAGE, auto_compress=False, overwrite=True)

    for name, d in [("MODEL_METRICS", metrics), ("MODEL_PREDICTIONS", pred_df), ("FEATURE_EFFECTS", fe)]:
        session.write_pandas(d, name, database="MARKETING_COPILOT", schema="CREATIVE",
                             auto_create_table=True, overwrite=True, quote_identifiers=False)
    return json.loads(json.dumps({"chosen": chosen, "meta": meta,
                                  "metrics": metrics.drop(columns=list(meta)).to_dict("records")}, default=str))
