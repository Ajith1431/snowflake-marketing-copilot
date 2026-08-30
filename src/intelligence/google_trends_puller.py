"""
Google Trends Intelligence Puller
Fetches trend data, rising queries, and regional interest for marketing keywords.
"""

import time
from datetime import datetime

from pytrends.request import TrendReq


def get_trend_data(keywords: list, geo: str = "US", timeframe: str = "today 3-m") -> dict:
    if not keywords:
        return {"error_message": "No keywords provided"}

    # pytrends allows max 5 keywords per request
    keywords = keywords[:5]

    for attempt in range(2):
        try:
            pytrends = TrendReq(hl="en-US", tz=360)
            pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo=geo)

            # 1. Interest over time
            interest_df = pytrends.interest_over_time()
            trend_rows = []
            if not interest_df.empty:
                for date_idx, row in interest_df.iterrows():
                    for kw in keywords:
                        if kw in row:
                            trend_rows.append({
                                "date": date_idx.strftime("%Y-%m-%d"),
                                "keyword": kw,
                                "score": int(row[kw]),
                            })

            # Find peak
            peak_date, peak_score, peak_keyword = None, 0, None
            if not interest_df.empty:
                for kw in keywords:
                    if kw in interest_df.columns:
                        max_idx = interest_df[kw].idxmax()
                        max_val = int(interest_df[kw].max())
                        if max_val > peak_score:
                            peak_score = max_val
                            peak_date = max_idx.strftime("%Y-%m-%d")
                            peak_keyword = kw

            # 2. Related queries
            related = pytrends.related_queries()
            rising_queries = []
            for kw in keywords:
                if kw in related and related[kw].get("rising") is not None:
                    rising_df = related[kw]["rising"]
                    for _, r in rising_df.head(5).iterrows():
                        q = r.get("query", "")
                        if q and q not in rising_queries:
                            rising_queries.append(q)
            rising_queries = rising_queries[:5]

            # 3. Interest by region
            regional_df = pytrends.interest_by_region(resolution="COUNTRY", inc_low_vol=True, inc_geo_code=False)
            regional_interest = []
            if not regional_df.empty:
                regional_df["total"] = regional_df.sum(axis=1)
                top_regions = regional_df.sort_values("total", ascending=False).head(5)
                for region_name, row in top_regions.iterrows():
                    regional_interest.append({
                        "region": region_name,
                        "score": int(row["total"]),
                    })

            result = {
                "trend_df": trend_rows,
                "peak_date": peak_date,
                "peak_score": peak_score,
                "peak_keyword": peak_keyword,
                "rising_queries": rising_queries,
                "regional_interest": regional_interest,
                "error_message": None,
            }

            print(f"[Google Trends] {len(trend_rows)} data points collected")
            print(f"[Google Trends] Peak: '{peak_keyword}' scored {peak_score} on {peak_date}")
            print(f"[Google Trends] Rising queries: {rising_queries}")
            print(f"[Google Trends] Top regions: {[r['region'] for r in regional_interest]}")
            return result

        except Exception as e:
            if attempt == 0:
                print(f"[Google Trends] Attempt 1 failed: {e}. Retrying in 10s...")
                time.sleep(10)
            else:
                error_msg = f"Google Trends failed after 2 attempts: {str(e)}"
                print(f"[Google Trends] {error_msg}")
                return {
                    "trend_df": [],
                    "peak_date": None,
                    "peak_score": 0,
                    "peak_keyword": None,
                    "rising_queries": [],
                    "regional_interest": [],
                    "error_message": error_msg,
                }


if __name__ == "__main__":
    print("=" * 60)
    print("Google Trends Puller - Test Run")
    print("=" * 60)
    result = get_trend_data(
        keywords=["FIFA 2026", "football shoes", "Nike", "Adidas", "Puma"],
        geo="US",
        timeframe="today 3-m",
    )
    print(f"\nResult keys: {list(result.keys())}")
    print(f"Trend rows: {len(result.get('trend_df', []))}")
    print(f"Peak: {result.get('peak_keyword')} = {result.get('peak_score')} on {result.get('peak_date')}")
    print(f"Rising: {result.get('rising_queries')}")
    print(f"Regions: {result.get('regional_interest')}")
    if result.get("error_message"):
        print(f"ERROR: {result['error_message']}")
