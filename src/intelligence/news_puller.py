"""
News Intelligence Puller
Primary: Event Registry API (with your API key)
Fallback: Google News RSS (free, no key needed)
"""

import re
import requests
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from html import unescape

from eventregistry import EventRegistry, QueryArticlesIter, QueryItems


POSITIVE_KEYWORDS = {"launch", "success", "growth", "record", "award", "win", "innovative", "leading", "best"}
NEGATIVE_KEYWORDS = {"fail", "controversy", "drop", "recall", "ban", "loss", "decline", "disappoint", "worst"}


def _sentiment_label(text: str) -> tuple:
    if not text:
        return 0, "neutral"
    words = set(text.lower().split())
    pos = len(words & POSITIVE_KEYWORDS)
    neg = len(words & NEGATIVE_KEYWORDS)
    score = pos - neg
    if score > 0:
        return score, "positive"
    elif score < 0:
        return score, "negative"
    return 0, "neutral"


def _strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", unescape(text or ""))
    return re.sub(r"\s+", " ", clean).strip()


def _fetch_event_registry(query: str, api_key: str, max_results: int = 10) -> list:
    try:
        er = EventRegistry(apiKey=api_key)
        q = QueryArticlesIter(
            keywords=QueryItems.AND(query.split()[:5]),
            lang="eng",
            dateStart=(datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d"),
        )
        articles = []
        for art in q.execQuery(er, sortBy="date", maxItems=max_results):
            articles.append({
                "title": art.get("title", ""),
                "source": {"name": art.get("source", {}).get("title", "Unknown")},
                "publishedAt": art.get("dateTime", ""),
                "description": (art.get("body", "") or "")[:500],
                "url": art.get("url", ""),
            })
        return articles
    except Exception as e:
        print(f"[EventRegistry] Error: {e}")
        return []


def _fetch_google_news_rss(query: str, max_results: int = 10) -> list:
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.content)
        articles = []
        for item in root.findall(".//item")[:max_results]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            desc = _strip_html(item.findtext("description", ""))
            source_match = re.search(r" - (.+)$", title)
            source_name = source_match.group(1).strip() if source_match else "Google News"
            clean_title = re.sub(r"\s*-\s*[^-]+$", "", title).strip() if source_match else title
            articles.append({
                "title": clean_title,
                "source": {"name": source_name},
                "publishedAt": pub_date,
                "description": desc[:500],
                "url": link,
            })
        return articles
    except Exception as e:
        print(f"[GoogleNewsRSS] Error: {e}")
        return []


def _normalize(raw: dict, query: str, brand_tag: str, article_type: str) -> dict:
    desc = raw.get("description") or ""
    sent_score, sent_label = _sentiment_label(desc)
    source = raw.get("source", {})
    source_name = source.get("name", "Unknown") if isinstance(source, dict) else str(source)
    return {
        "title": raw.get("title", ""),
        "source": source_name,
        "publishedAt": raw.get("publishedAt", ""),
        "description": desc[:500],
        "url": raw.get("url", ""),
        "query_used": query,
        "brand_tag": brand_tag,
        "article_type": article_type,
        "sentiment_score": sent_score,
        "sentiment_label": sent_label,
    }


def get_news(
    client_brand: str,
    event: str,
    competitors: list,
    api_key: str = "",
    days_back: int = 30,
) -> dict:
    seen_urls = set()
    event_news = []
    brand_news = []
    competitor_news = {c: [] for c in competitors}
    source_used = "none"

    def _fetch(query, brand_tag, article_type):
        nonlocal source_used
        # Try Event Registry first
        articles = []
        if api_key:
            articles = _fetch_event_registry(query, api_key, max_results=10)
            if articles:
                source_used = "Event Registry"
        # Fallback to Google News RSS
        if not articles:
            articles = _fetch_google_news_rss(query, max_results=10)
            if articles and source_used == "none":
                source_used = "Google News RSS"
        result = []
        for raw in articles:
            url = raw.get("url", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)
            result.append(_normalize(raw, query, brand_tag, article_type))
        return result

    try:
        print(f"[News] Searching for: {event} + {client_brand} + {len(competitors)} competitors")

        event_news = _fetch(f"{event} marketing campaign", event, "EVENT")
        brand_news = _fetch(f"{client_brand} {event}", client_brand, "OUR_BRAND")
        for comp in competitors:
            competitor_news[comp] = _fetch(f"{comp} {event} campaign", comp, "COMPETITOR")

        def _summarize(articles):
            counts = {"positive": 0, "negative": 0, "neutral": 0}
            for a in articles:
                counts[a["sentiment_label"]] += 1
            return counts

        sentiment_summary = {"brand": _summarize(brand_news)}
        for comp in competitors:
            sentiment_summary[comp] = _summarize(competitor_news[comp])

        all_articles = event_news + brand_news
        for arts in competitor_news.values():
            all_articles.extend(arts)
        total = len(all_articles)

        result = {
            "event_news": event_news,
            "brand_news": brand_news,
            "competitor_news": competitor_news,
            "sentiment_summary": sentiment_summary,
            "total_articles": total,
            "source_used": source_used,
            "error_message": None,
        }

        print(f"[News] Source: {source_used}")
        print(f"[News] Collected {total} unique articles")
        print(f"[News] Event: {len(event_news)}, Brand: {len(brand_news)}, "
              f"Competitors: {', '.join(f'{c}={len(v)}' for c, v in competitor_news.items())}")
        print(f"[News] Sentiment: {sentiment_summary}")
        return result

    except Exception as e:
        error_msg = f"News fetch error: {str(e)}"
        print(f"[News] {error_msg}")
        return {
            "event_news": [], "brand_news": [],
            "competitor_news": {c: [] for c in competitors},
            "sentiment_summary": {}, "total_articles": 0,
            "source_used": "none", "error_message": error_msg,
        }


if __name__ == "__main__":
    from config import EVENT_REGISTRY_API_KEY

    print("=" * 60)
    print("News Puller - Test Run")
    print("=" * 60)
    result = get_news(
        client_brand="UrbanThread",
        event="FIFA World Cup 2026",
        competitors=["Nike", "Adidas", "Puma"],
        api_key=EVENT_REGISTRY_API_KEY,
        days_back=30,
    )
    print(f"\nSource: {result.get('source_used')}")
    print(f"Total articles: {result['total_articles']}")
    print(f"Event news: {len(result['event_news'])}")
    print(f"Brand news: {len(result['brand_news'])}")
    for comp, arts in result["competitor_news"].items():
        print(f"  {comp}: {len(arts)} articles")
    print(f"Sentiment: {result['sentiment_summary']}")
    if result["event_news"]:
        print(f"\nSample headlines:")
        for a in result["event_news"][:3]:
            print(f"  [{a['sentiment_label'].upper()}] {a['title'][:80]} ({a['source']})")
    if result.get("error_message"):
        print(f"ERROR: {result['error_message']}")
