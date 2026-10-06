"""
Web Intelligence Puller
Uses Snowflake Cortex Complete with web search to gather marketing intelligence.
"""

import json

import snowflake.connector


def _call_cortex_complete(session_or_conn, query: str) -> dict:
    system_prompt = (
        "You are a marketing intelligence researcher. "
        "Search the web and return structured findings. "
        "Always return valid JSON only, with no markdown fencing."
    )
    user_prompt = (
        f"Search for: {query}\n"
        "Return JSON with fields:\n"
        "summary: 2 sentence summary of findings\n"
        "key_findings: list of 5 bullet point strings\n"
        "competitor_activity: what competitors are doing (string)\n"
        "consumer_sentiment: positive or negative or neutral\n"
        "recommended_channels: list of top 3 channel name strings\n"
        "sources: list of source name strings found"
    )

    sql = f"""
    SELECT SNOWFLAKE.CORTEX.COMPLETE(
        'claude-sonnet-4-6',
        ARRAY_CONSTRUCT(
            OBJECT_CONSTRUCT('role', 'system', 'content', $${system_prompt}$$),
            OBJECT_CONSTRUCT('role', 'user', 'content', $${user_prompt}$$)
        ),
        OBJECT_CONSTRUCT('max_tokens', 2048)
    ) AS response
    """

    try:
        if hasattr(session_or_conn, "sql"):
            row = session_or_conn.sql(sql).collect()[0]
            raw = row["RESPONSE"]
        else:
            cur = session_or_conn.cursor()
            cur.execute(sql)
            raw = cur.fetchone()[0]
            cur.close()

        # Cortex Complete returns a JSON wrapper with "choices"
        try:
            wrapper = json.loads(raw)
            if "choices" in wrapper:
                choice = wrapper["choices"][0]
                text = choice.get("messages") or choice.get("message", {}).get("content", "")
            elif "messages" in wrapper:
                text = wrapper["messages"][0].get("content", raw)
            else:
                text = raw
        except (json.JSONDecodeError, KeyError, IndexError):
            text = raw

        # Strip markdown fences if present
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        parsed = json.loads(text)
        return parsed

    except json.JSONDecodeError:
        return {
            "summary": text[:500] if 'text' in dir() else "Unable to parse response",
            "key_findings": [],
            "competitor_activity": "",
            "consumer_sentiment": "neutral",
            "recommended_channels": [],
            "sources": [],
        }
    except Exception as e:
        return {
            "summary": f"Query failed: {str(e)}",
            "key_findings": [],
            "competitor_activity": "",
            "consumer_sentiment": "neutral",
            "recommended_channels": [],
            "sources": [],
            "error": str(e),
        }


def get_web_intelligence(
    client_brand: str,
    event: str,
    competitors: list,
    markets: list,
    snowflake_conn=None,
) -> dict:
    # Build connection if not provided
    conn = snowflake_conn
    owns_conn = False
    if conn is None:
        try:
            from config import SNOWFLAKE_CONNECTION
            conn = snowflake.connector.connect(connection_name=SNOWFLAKE_CONNECTION)
            cur = conn.cursor()
            cur.execute("USE ROLE ACCOUNTADMIN")
            cur.execute("USE WAREHOUSE MARKETING_WH")
            cur.close()
            owns_conn = True
        except Exception as e:
            return {
                "web_summary": {},
                "competitor_themes": {},
                "platform_presence": {},
                "consumer_sentiment": "unknown",
                "trending_channels": [],
                "raw_responses": [],
                "queries_run": 0,
                "error_message": f"Could not connect to Snowflake: {str(e)}",
            }

    queries = [
        f"{event} marketing campaign strategy 2026",
        f"{client_brand} {event} advertising",
    ]
    for comp in competitors[:3]:
        queries.append(f"{comp} {event} campaign social media ads")
    queries.append(f"{event} consumer sentiment social media")
    market_str = markets[0] if markets else "US"
    queries.append(f"best marketing channels {event} {market_str}")
    queries.append(f"competitor advertising {event} fashion apparel")

    raw_responses = []
    competitor_themes = {c: [] for c in competitors}
    platform_presence = {c: [] for c in competitors}
    all_channels = []
    all_findings = []
    sentiments = []

    for i, q in enumerate(queries):
        print(f"[Web Intel] Running query {i+1}/{len(queries)}: {q[:60]}...")
        try:
            resp = _call_cortex_complete(conn, q)
            raw_responses.append({"query": q, "response": resp})

            findings = resp.get("key_findings", [])
            all_findings.extend(findings)

            channels = resp.get("recommended_channels", [])
            all_channels.extend(channels)

            sent = resp.get("consumer_sentiment", "neutral")
            sentiments.append(sent)

            activity = resp.get("competitor_activity", "")
            for comp in competitors:
                if comp.lower() in q.lower():
                    competitor_themes[comp].append(activity)
                    competitor_themes[comp].extend(findings[:2])
                    platform_presence[comp].extend(channels)

        except Exception as e:
            print(f"[Web Intel] Query {i+1} failed: {e}")
            raw_responses.append({"query": q, "error": str(e)})

    # Aggregate trending channels
    channel_counts = {}
    for ch in all_channels:
        ch_clean = ch.strip().title()
        channel_counts[ch_clean] = channel_counts.get(ch_clean, 0) + 1
    trending_channels = sorted(channel_counts, key=channel_counts.get, reverse=True)

    # Overall sentiment
    if sentiments:
        from collections import Counter
        sent_counts = Counter(sentiments)
        overall_sentiment = sent_counts.most_common(1)[0][0]
    else:
        overall_sentiment = "unknown"

    # Deduplicate findings
    unique_findings = list(dict.fromkeys(all_findings))[:10]

    # Clean up competitor data
    for comp in competitors:
        competitor_themes[comp] = list(dict.fromkeys(competitor_themes[comp]))[:5]
        platform_presence[comp] = list(dict.fromkeys(platform_presence[comp]))[:5]

    if owns_conn:
        conn.close()

    result = {
        "web_summary": {
            "key_insights": unique_findings,
            "trending_channels": trending_channels[:5],
            "overall_sentiment": overall_sentiment,
        },
        "competitor_themes": competitor_themes,
        "platform_presence": platform_presence,
        "consumer_sentiment": overall_sentiment,
        "trending_channels": trending_channels[:5],
        "raw_responses": raw_responses,
        "queries_run": len(queries),
        "error_message": None,
    }

    print(f"\n[Web Intel] Completed {len(queries)} queries")
    print(f"[Web Intel] Unique insights: {len(unique_findings)}")
    print(f"[Web Intel] Trending channels: {trending_channels[:5]}")
    print(f"[Web Intel] Overall sentiment: {overall_sentiment}")
    return result


if __name__ == "__main__":
    print("=" * 60)
    print("Web Intelligence Puller - Test Run")
    print("=" * 60)
    result = get_web_intelligence(
        client_brand="Nike",
        event="FIFA World Cup 2026",
        competitors=["Adidas", "Puma"],
        markets=["US", "GB"],
    )
    print(f"\nQueries run: {result['queries_run']}")
    print(f"Web summary: {json.dumps(result['web_summary'], indent=2)}")
    print(f"Competitor themes: {json.dumps(result['competitor_themes'], indent=2)}")
    if result.get("error_message"):
        print(f"ERROR: {result['error_message']}")
