"""
Shared helpers for the creative intelligence layer (numpy/pandas only, so the same code runs
inside Snowflake Python procedures and locally).

Adjusted lift of an attribute value v (family F) inside a stratum:
  1. y = log-odds of ad-level CTR (sum clicks / sum impressions per ad).
  2. Ridge regression of y on one-hot dummies for ALL 8 attribute families (every level kept; the
     ridge penalty makes it identifiable) plus controls: log weekly spend, brand, placement.
  3. contrast(v) = beta_v - share-weighted mean of beta_u for the other levels u of F in the stratum.
     This is "with v vs without v" holding everything else fixed. lift% = (exp(contrast) - 1) * 100.
  4. 95% interval: percentile bootstrap over ads.
"""

import numpy as np
import pandas as pd

FAMILIES = ["hook_type", "headline_tone", "cta_tone", "background", "color_temp",
            "has_person", "word_count_group", "has_logo_first_3s"]
MARKETS = ["UAE", "KSA", "UK", "US", "IN"]
OBJECTIVES = ["AWARENESS", "LINK_CLICKS", "LEADS"]
BRANDS = ["Nike", "Pepsi", "Samsung"]
RIDGE_ALPHA = 1.0
LOW_N = 30
NEGLIGIBLE_PCT = 3.0

AD_LEVEL_SQL = """
SELECT ad_id, ANY_VALUE(brand) brand, ANY_VALUE(market) market, ANY_VALUE(objective) objective,
       ANY_VALUE(placement) placement, ANY_VALUE(ad_type) ad_type,
       ANY_VALUE(hook_type) hook_type, ANY_VALUE(headline_tone) headline_tone, ANY_VALUE(cta_tone) cta_tone,
       ANY_VALUE(background) background, ANY_VALUE(color_temp) color_temp, ANY_VALUE(has_person) has_person,
       ANY_VALUE(word_count_group) word_count_group, ANY_VALUE(has_logo_first_3s) has_logo_first_3s,
       SUM(impressions) impressions, SUM(clicks) clicks, SUM(spend) spend, COUNT(*) n_weeks
FROM MARKETING_COPILOT.CREATIVE.V_AD_FEATURES
GROUP BY ad_id
"""


def logit_rate(num, den):
    num, den = np.asarray(num, float), np.asarray(den, float)
    return np.log((num + 0.5) / (den - num + 0.5))


def prepare_ads(ads):
    ads = ads.copy()
    ads.columns = [c.lower() for c in ads.columns]
    for c in ["impressions", "clicks", "spend", "n_weeks"]:
        ads[c] = ads[c].astype(float)
    ads["y"] = logit_rate(ads["clicks"], ads["impressions"])
    ads["log_spend_wk"] = np.log(ads["spend"] / ads["n_weeks"])
    return ads


def _design(df, families, controls_cat, controls_num):
    blocks, names, groups = [], [], []
    for col in families + controls_cat:
        levels = sorted(df[col].astype(str).unique())
        if col in controls_cat and len(levels) < 2:
            continue
        for lv in levels:
            blocks.append((df[col].astype(str) == lv).to_numpy(float))
            names.append((col, lv))
            groups.append(col)
    for col in controls_num:
        x = df[col].to_numpy(float)
        sd = x.std()
        blocks.append((x - x.mean()) / sd if sd > 0 else np.zeros_like(x))
        names.append((col, None))
        groups.append(col)
    X = np.column_stack(blocks + [np.ones(len(df))])
    return X, names


def ridge_fit(X, y, alpha=RIDGE_ALPHA):
    p = X.shape[1]
    pen = np.full(p, alpha)
    pen[-1] = 0.0  # intercept unpenalised
    return np.linalg.solve(X.T @ X + np.diag(pen), X.T @ y)


def contrasts(df, beta, names, families):
    """{(family, value): contrast} using share-weighted mean of the other levels."""
    idx = {n: i for i, n in enumerate(names)}
    out = {}
    for fam in families:
        counts = df[fam].astype(str).value_counts()
        levels = [lv for lv in counts.index if (fam, lv) in idx]
        for v in levels:
            others = [u for u in levels if u != v]
            if not others:
                continue
            w = counts[others].to_numpy(float)
            other_mean = np.dot(w, [beta[idx[(fam, u)]] for u in others]) / w.sum()
            out[(fam, v)] = beta[idx[(fam, v)]] - other_mean
    return out


def adjusted_contrasts(df, y, families=FAMILIES, controls_cat=("brand", "placement"),
                       controls_num=("log_spend_wk",), alpha=RIDGE_ALPHA):
    X, names = _design(df, list(families), list(controls_cat), list(controls_num))
    beta = ridge_fit(X, np.asarray(y, float), alpha)
    return contrasts(df, beta, names, families)


def bootstrap_contrasts(df, y_col="y", n_boot=200, seed=7, **kw):
    """Point contrasts + percentile 95% intervals, resampling ads with replacement."""
    rng = np.random.default_rng(seed)
    point = adjusted_contrasts(df, df[y_col], **kw)
    draws = {k: [] for k in point}
    n = len(df)
    for _ in range(n_boot):
        sample = df.iloc[rng.integers(0, n, n)]
        est = adjusted_contrasts(sample, sample[y_col], **kw)
        for k in point:
            if k in est:
                draws[k].append(est[k])
    ci = {k: (np.percentile(v, 2.5), np.percentile(v, 97.5)) if len(v) >= 20 else (np.nan, np.nan)
          for k, v in draws.items()}
    return point, ci


def to_lift_pct(c):
    return (np.exp(c) - 1.0) * 100.0
