"""
Snowflake Loader for Event Intelligence
Loads intelligence run results into Snowflake RAW tables.
"""

import json
from datetime import datetime, timezone


def load_intelligence_run(session, intelligence_result: dict) -> dict:
    run_id = intelligence_result.get("run_id", "")
    client_name = intelligence_result.get("client_name", "")
    event_name = intelligence_result.get("event_name", "")
    competitors = intelligence_result.get("competitors", [])
    markets = intelligence_result.get("markets", [])
    confidence = intelligence_result.get("confidence", "LOW")
    sources_succeeded = intelligence_result.get("sources_succeeded", 0)

    errors = []
    trends_loaded = 0
    articles_loaded = 0
    web_loaded = 0

    def _exec(sql):
        try:
            session.sql(sql).collect()
            return True
        except Exception as e:
            errors.append(str(e))
            print(f"[Loader] SQL error: {e}")
            return False

    def _esc(s):
        if s is None:
            return ""
        return str(s).replace("'", "''")

    # 1. Insert run metadata
    print(f"[Loader] Inserting run {run_id}...")
    comp_array = ", ".join(f"'{_esc(c)}'" for c in competitors)
    mkt_array = ", ".join(f"'{_esc(m)}'" for m in markets)
    _exec(f"""
        INSERT INTO MARKETING_COPILOT.RAW.EVENT_INTELLIGENCE_RUNS
        (run_id, client_name, event_name, competitors, markets, confidence, sources_succeeded, status)
        SELECT '{_esc(run_id)}', '{_esc(client_name)}', '{_esc(event_name)}',
            ARRAY_CONSTRUCT({comp_array}), ARRAY_CONSTRUCT({mkt_array}),
            '{_esc(confidence)}', {sources_succeeded}, 'COMPLETED'
    """)

    # 2. Insert Google Trends data
    trends = intelligence_result.get("google_trends", {})
    trend_rows = trends.get("trend_df", [])
    peak_date = trends.get("peak_date")

    if trend_rows:
        print(f"[Loader] Inserting {len(trend_rows)} trend rows...")
        batch_size = 100
        for batch_start in range(0, len(trend_rows), batch_size):
            batch = trend_rows[batch_start:batch_start + batch_size]
            values = []
            for i, row in enumerate(batch):
                idx = batch_start + i
                tid = f"TR_{run_id}_{idx:04d}"
                is_peak = "TRUE" if row.get("date") == peak_date else "FALSE"
                values.append(
                    f"('{_esc(tid)}', '{_esc(run_id)}', '{_esc(row.get('keyword', ''))}', "
                    f"'{row.get('date', '2000-01-01')}', {row.get('score', 0)}, "
                    f"'{_esc(trends.get('geo', 'US')[:10])}', {is_peak})"
                )
            if values:
                sql = f"""INSERT INTO MARKETING_COPILOT.RAW.GOOGLE_TRENDS_DATA
                    (trend_id, run_id, keyword, trend_date, interest_score, geo, is_peak)
                    VALUES {', '.join(values)}"""
                if _exec(sql):
                    trends_loaded += len(batch)

    # 3. Insert news articles
    news = intelligence_result.get("news_intel", {})
    all_articles = []
    for a in news.get("event_news", []):
        all_articles.append(a)
    for a in news.get("brand_news", []):
        all_articles.append(a)
    for comp_articles in news.get("competitor_news", {}).values():
        all_articles.extend(comp_articles)

    if all_articles:
        print(f"[Loader] Inserting {len(all_articles)} news articles...")
        batch_size = 50
        for batch_start in range(0, len(all_articles), batch_size):
            batch = all_articles[batch_start:batch_start + batch_size]
            values = []
            for i, art in enumerate(batch):
                idx = batch_start + i
                aid = f"ART_{run_id}_{idx:04d}"
                pub = art.get("publishedAt", "")
                pub_ts = f"TRY_TO_TIMESTAMP('{_esc(pub)}')" if pub else "NULL"
                values.append(
                    f"('{_esc(aid)}', '{_esc(run_id)}', '{_esc(art.get('brand_tag', ''))}', "
                    f"'{_esc(art.get('article_type', ''))}', '{_esc(art.get('title', '')[:490])}', "
                    f"'{_esc(art.get('source', '')[:95])}', {pub_ts}, "
                    f"'{_esc(art.get('description', '')[:1990])}', '{_esc(art.get('url', '')[:990])}', "
                    f"'{_esc(art.get('sentiment_label', 'neutral'))}', {art.get('sentiment_score', 0)})"
                )
            if values:
                sql = f"""INSERT INTO MARKETING_COPILOT.RAW.NEWS_ARTICLES
                    (article_id, run_id, brand_name, article_type, title, source_name,
                     published_at, description, url, sentiment, sentiment_score)
                    VALUES {', '.join(values)}"""
                if _exec(sql):
                    articles_loaded += len(batch)

    # 4. Insert web intelligence
    web = intelligence_result.get("web_intel", {})
    raw_responses = web.get("raw_responses", [])

    if raw_responses:
        print(f"[Loader] Inserting {len(raw_responses)} web intelligence rows...")
        for i, wr in enumerate(raw_responses):
            wid = f"WEB_{run_id}_{i:04d}"
            query_text = wr.get("query", "")
            resp = wr.get("response", {})
            if isinstance(resp, str):
                resp = {}
            summary = _esc(str(resp.get("summary", ""))[:1990])
            findings = json.dumps(resp.get("key_findings", []))
            activity = _esc(str(resp.get("competitor_activity", ""))[:1990])
            sentiment = _esc(str(resp.get("consumer_sentiment", "neutral")))
            channels = json.dumps(resp.get("recommended_channels", []))
            sources = json.dumps(resp.get("sources", []))
            query_type = "competitor" if any(c.lower() in query_text.lower() for c in competitors) else "general"

            sql = f"""INSERT INTO MARKETING_COPILOT.RAW.WEB_INTELLIGENCE
                (intel_id, run_id, query_text, query_type, summary, key_findings,
                 competitor_activity, consumer_sentiment, recommended_channels, sources_found)
                SELECT '{_esc(wid)}', '{_esc(run_id)}', '{_esc(query_text[:490])}', '{query_type}',
                       '{summary}', PARSE_JSON($${findings}$$), '{activity}', '{sentiment}',
                       PARSE_JSON($${channels}$$), PARSE_JSON($${sources}$$)"""
            if _exec(sql):
                web_loaded += 1

    # Determine status
    total_expected = (1 if trend_rows else 0) + (1 if all_articles else 0) + (1 if raw_responses else 0)
    total_ok = (1 if trends_loaded > 0 else 0) + (1 if articles_loaded > 0 else 0) + (1 if web_loaded > 0 else 0)
    if total_ok == total_expected and not errors:
        load_status = "SUCCESS"
    elif total_ok > 0:
        load_status = "PARTIAL"
    else:
        load_status = "FAILED"

    result = {
        "run_id": run_id,
        "trends_loaded": trends_loaded,
        "articles_loaded": articles_loaded,
        "web_queries_loaded": web_loaded,
        "load_status": load_status,
        "errors": errors,
    }

    ok = "OK"
    fail = "FAIL"
    print(f"\n{'='*60}")
    print(f"SNOWFLAKE LOAD COMPLETE - {load_status}")
    print(f"{'='*60}")
    print(f"{'Table':<30} | {'Rows':>6} | Status")
    print(f"{'-'*60}")
    print(f"{'EVENT_INTELLIGENCE_RUNS':<30} | {'1':>6} | {ok}")
    print(f"{'GOOGLE_TRENDS_DATA':<30} | {trends_loaded:>6} | {ok if trends_loaded > 0 else fail}")
    print(f"{'NEWS_ARTICLES':<30} | {articles_loaded:>6} | {ok if articles_loaded > 0 else fail}")
    print(f"{'WEB_INTELLIGENCE':<30} | {web_loaded:>6} | {ok if web_loaded > 0 else fail}")
    print(f"{'='*60}")
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors[:5]:
            print(f"  - {e[:100]}")

    return result
