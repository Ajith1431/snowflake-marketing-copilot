"""
Intelligence Orchestrator
Runs all 3 intelligence pullers and aggregates into a single result.
"""

import sys
import os
from datetime import datetime, timezone

# Add parent directory for imports when running standalone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google_trends_puller import get_trend_data
from news_puller import get_news
from web_intelligence_puller import get_web_intelligence


def run_full_intelligence(
    client_name: str,
    event_name: str,
    event_keywords: list,
    competitors: list,
    markets: list,
    news_api_key: str,
) -> dict:
    run_id = f"RUN_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    pulled_at = datetime.now(timezone.utc).isoformat()

    print("=" * 60)
    print(f"Starting intelligence run for: {event_name}")
    print(f"Run ID: {run_id}")
    print(f"Client: {client_name}")
    print(f"Competitors: {', '.join(competitors)}")
    print(f"Markets: {', '.join(markets)}")
    print("=" * 60)

    # 1. Google Trends
    print("\n--- [1/3] Google Trends ---")
    trends = get_trend_data(
        keywords=event_keywords[:5],
        geo=markets[0] if markets else "US",
        timeframe="today 3-m",
    )
    trends_ok = bool(trends.get("trend_df")) and not trends.get("error_message")
    trends_count = len(trends.get("trend_df", []))

    # 2. NewsAPI
    print("\n--- [2/3] NewsAPI ---")
    news = get_news(
        client_brand=client_name,
        event=event_name,
        competitors=competitors,
        api_key=news_api_key,
        days_back=30,
    )
    news_ok = news.get("total_articles", 0) > 0 and not news.get("error_message")
    news_count = news.get("total_articles", 0)

    # 3. Web Intelligence
    print("\n--- [3/3] Web Intelligence (Cortex Complete) ---")
    web = get_web_intelligence(
        client_brand=client_name,
        event=event_name,
        competitors=competitors,
        markets=markets,
    )
    web_ok = web.get("queries_run", 0) > 0 and not web.get("error_message")
    web_count = web.get("queries_run", 0)

    # Confidence
    sources_succeeded = sum([trends_ok, news_ok, web_ok])
    confidence_map = {3: "HIGH", 2: "MEDIUM", 1: "LOW", 0: "INSUFFICIENT DATA"}
    confidence = confidence_map.get(sources_succeeded, "INSUFFICIENT DATA")

    # Build summary
    summary = {
        "peak_trend_keyword": trends.get("peak_keyword"),
        "peak_trend_date": trends.get("peak_date"),
        "top_news_headline": None,
        "overall_news_sentiment": None,
        "competitor_most_active": None,
        "top_trending_channel": None,
        "key_strategic_insight": None,
    }

    # Top news headline
    if news.get("event_news"):
        summary["top_news_headline"] = news["event_news"][0].get("title")

    # Overall news sentiment
    if news.get("sentiment_summary"):
        all_sent = {"positive": 0, "negative": 0, "neutral": 0}
        for label_counts in news["sentiment_summary"].values():
            for label, count in label_counts.items():
                all_sent[label] = all_sent.get(label, 0) + count
        summary["overall_news_sentiment"] = max(all_sent, key=all_sent.get)

    # Most active competitor
    if news.get("competitor_news"):
        comp_article_counts = {}
        for comp, arts in news["competitor_news"].items():
            comp_article_counts[comp] = len(arts)
        # Add web mentions
        for comp in competitors:
            web_themes = web.get("competitor_themes", {}).get(comp, [])
            comp_article_counts[comp] = comp_article_counts.get(comp, 0) + len(web_themes)
        if comp_article_counts:
            summary["competitor_most_active"] = max(comp_article_counts, key=comp_article_counts.get)

    # Top trending channel
    if web.get("trending_channels"):
        summary["top_trending_channel"] = web["trending_channels"][0]

    # Key strategic insight
    web_insights = web.get("web_summary", {}).get("key_insights", [])
    if web_insights:
        summary["key_strategic_insight"] = web_insights[0]

    result = {
        "run_id": run_id,
        "client_name": client_name,
        "event_name": event_name,
        "competitors": competitors,
        "markets": markets,
        "confidence": confidence,
        "sources_succeeded": sources_succeeded,
        "google_trends": trends,
        "news_intel": news,
        "web_intel": web,
        "pulled_at": pulled_at,
        "summary": summary,
    }

    # Print summary table
    print("\n" + "=" * 60)
    print("INTELLIGENCE RUN COMPLETE")
    print("=" * 60)
    print(f"{'Source':<25} {'Status':<10} {'Records'}")
    print("-" * 60)
    print(f"{'Google Trends':<25} {'OK' if trends_ok else 'FAIL':<10} {trends_count} data points")
    print(f"{'NewsAPI':<25} {'OK' if news_ok else 'FAIL':<10} {news_count} articles")
    print(f"{'Web Intelligence':<25} {'OK' if web_ok else 'FAIL':<10} {web_count} queries")
    print("-" * 60)
    print(f"Overall Confidence: {confidence}")
    print(f"Run ID: {run_id}")
    print("=" * 60)

    if summary["peak_trend_keyword"]:
        print(f"\nPeak Trend: '{summary['peak_trend_keyword']}' on {summary['peak_trend_date']}")
    if summary["top_news_headline"]:
        print(f"Top Headline: {summary['top_news_headline'][:80]}...")
    if summary["competitor_most_active"]:
        print(f"Most Active Competitor: {summary['competitor_most_active']}")
    if summary["top_trending_channel"]:
        print(f"Top Trending Channel: {summary['top_trending_channel']}")
    if summary["key_strategic_insight"]:
        print(f"Key Insight: {summary['key_strategic_insight'][:100]}...")

    return result


if __name__ == "__main__":
    from config import EVENT_REGISTRY_API_KEY

    result = run_full_intelligence(
        client_name="UrbanThread",
        event_name="FIFA World Cup 2026",
        event_keywords=["FIFA 2026", "World Cup 2026", "football shoes",
                        "Nike FIFA", "Adidas World Cup"],
        competitors=["Nike", "Adidas", "Puma"],
        markets=["US", "GB"],
        news_api_key=EVENT_REGISTRY_API_KEY,
    )

    print(f"\nResult dict keys: {list(result.keys())}")
    print(f"Summary: {result['summary']}")
