-- ============================================
-- MCP Tool Stored Procedures
-- Wraps creative studio functions as Snowflake procedures
-- accessible via MCP GENERIC tool type
-- ============================================

USE ROLE ACCOUNTADMIN;
USE DATABASE MARKETING_COPILOT;
USE SCHEMA SEMANTIC;
USE WAREHOUSE MARKETING_WH;

-- 1. Video Storyboard Generator
CREATE OR REPLACE PROCEDURE GENERATE_STORYBOARD(
    CLIENT_NAME VARCHAR, PRODUCT_NAME VARCHAR, OBJECTIVE VARCHAR, CREATIVE_DIRECTION VARCHAR
)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
AS
$$
import json
def run(session, client_name, product_name, objective, creative_direction):
    scenes = [
        {"scene": 1, "duration": "0-1s", "description": f"Opening hero shot -- {product_name} reveal with cinematic lighting", "camera": "Slow zoom in", "mood": "Anticipation"},
        {"scene": 2, "duration": "1-3s", "description": f"Core benefit -- {objective} message through audience connection", "camera": "Medium shot, subtle pan", "mood": "Emotional resonance"},
        {"scene": 3, "duration": "3-4s", "description": f"{product_name} in use -- lifestyle context showing aspiration", "camera": "Close up detail", "mood": "Aspiration"},
        {"scene": 4, "duration": "4-5s", "description": f"{client_name} brand end card with tagline", "camera": "Static brand frame", "mood": "Trust"}
    ]
    prompt = (
        f"5-second cinematic brand video for {product_name} by {client_name}. "
        f"Goal: {objective}. Visual: {creative_direction}. "
        f"Style: Premium brand film, smooth camera, vibrant colours. No text. No logos."
    )
    return {"scenes": scenes, "video_prompt": prompt, "duration": "5 seconds", "client": client_name, "product": product_name}
$$;

-- 2. Design System Builder
CREATE OR REPLACE PROCEDURE BUILD_DESIGN_SYSTEM(
    CLIENT_NAME VARCHAR, BRAND_COLOURS VARCHAR, TONE_KEYWORDS VARCHAR
)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
AS
$$
def run(session, client_name, brand_colours, tone_keywords):
    colours = [c.strip() for c in brand_colours.split(",") if c.strip()]
    names = ["Primary", "Secondary", "Accent", "Background", "Text"]
    palette = [{"name": names[i] if i < len(names) else f"Colour {i+1}", "hex": c, "usage": f"{names[i]} elements"} for i, c in enumerate(colours[:5])]
    tones = [t.strip() for t in tone_keywords.split(",")]
    return {
        "client": client_name, "palette": palette, "tone": tones,
        "do": ["Use brand colours consistently", "Lead with benefits not features", "Show real people in real situations", "Use active voice"],
        "dont": ["Use competitor names", "Make unsubstantiated claims", "Crowd the composition", "Use generic stock imagery"]
    }
$$;

-- 3. Creative Intelligence (Cortex data layer that grounds the creative brief)
CREATE OR REPLACE PROCEDURE GET_CREATIVE_INTELLIGENCE(
    CLIENT_NAME VARCHAR, EVENT_NAME VARCHAR DEFAULT ''
)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
AS
$$
import json
from collections import Counter
from datetime import timedelta

def _rows(session, sql, params):
    return [r.as_dict() for r in session.sql(sql, params=params).collect()]

def _json_list(val):
    try:
        out = json.loads(val) if isinstance(val, str) else val
        return [str(x) for x in out] if isinstance(out, list) else []
    except Exception:
        return [s.strip() for s in str(val or "").split(",") if s.strip()]

def run(session, client_name, event_name):
    intel = {"client": client_name, "event": event_name or None}

    intel["top_channels"] = [
        {"channel": r["CHANNEL_NAME"], "avg_roas": float(r["AVG_ROAS"]), "avg_ctr": float(r["AVG_CTR"]),
         "total_revenue": float(r["TOTAL_REVENUE"])}
        for r in _rows(session, """
            SELECT channel_name, ROUND(AVG(roas), 2) AS avg_roas, ROUND(AVG(ctr), 4) AS avg_ctr,
                   ROUND(SUM(revenue_usd), 0) AS total_revenue
            FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS
            WHERE client_name = ? GROUP BY channel_name ORDER BY avg_roas DESC LIMIT 3""", [client_name])
    ]

    seg = _rows(session, """
        SELECT s.segment_name, s.age_band, s.gender_skew, s.income_level, TO_VARCHAR(s.interests) AS interests,
               ROUND(AVG(m.conversion_rate), 4) AS avg_conv_rate, ROUND(AVG(m.roas), 2) AS avg_roas
        FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS m
        JOIN MARKETING_COPILOT.RAW.RAW_BRIDGE_CAMPAIGN_SEGMENT b ON m.campaign_id = b.campaign_id
        JOIN MARKETING_COPILOT.ANALYTICS.DIM_AUDIENCE_SEGMENT s ON b.segment_id = s.segment_id
        WHERE m.client_name = ?
        GROUP BY 1, 2, 3, 4, 5 ORDER BY avg_conv_rate DESC LIMIT 1""", [client_name])
    if seg:
        s = seg[0]
        intel["primary_segment"] = {
            "name": s["SEGMENT_NAME"], "age_band": s["AGE_BAND"], "gender_skew": s["GENDER_SKEW"],
            "income_level": s["INCOME_LEVEL"], "interests": _json_list(s["INTERESTS"])[:5],
            "avg_conversion_rate": float(s["AVG_CONV_RATE"]), "avg_roas": float(s["AVG_ROAS"]),
        }

    guides = _rows(session, """
        SELECT industry, dos, donts, tone_keywords, color_palette
        FROM MARKETING_COPILOT.ANALYTICS.FACT_BRAND_GUIDELINES WHERE client_name = ?""", [client_name])
    if guides:
        dos, donts, tone = Counter(), Counter(), Counter()
        for g in guides:
            dos.update(_json_list(g["DOS"]))
            donts.update(_json_list(g["DONTS"]))
            tone.update(_json_list(g["TONE_KEYWORDS"]))
        intel["brand"] = {
            "industry": guides[0]["INDUSTRY"],
            "dos": [d for d, _ in dos.most_common(5)],
            "donts": [d for d, _ in donts.most_common(5)],
            "tone": [t for t, _ in tone.most_common(5)],
            "palette": guides[0]["COLOR_PALETTE"],
        }

    timing = {}
    if event_name:
        peak = _rows(session, """
            SELECT keyword, trend_date, interest_score
            FROM MARKETING_COPILOT.ANALYTICS.DIM_EVENT_TRENDS
            WHERE event_name ILIKE ? ORDER BY interest_score DESC, trend_date DESC LIMIT 1""", [event_name])
        if peak:
            p = peak[0]
            peak_date = p["TREND_DATE"]
            in_past = peak_date < session.sql("SELECT CURRENT_DATE()").collect()[0][0]
            timing.update({
                "trend_keyword": p["KEYWORD"], "trend_peak_date": str(peak_date),
                "peak_score": float(p["INTEREST_SCORE"]), "peak_in_past": in_past,
                "recommended_launch": None if in_past else str(peak_date - timedelta(weeks=6)),
                "source": "Google Trends, last 3 months (intelligence run)",
            })
    industry = intel.get("brand", {}).get("industry", "")
    upcoming = _rows(session, """
        SELECT event_name, start_date, end_date, impact_level
        FROM MARKETING_COPILOT.ANALYTICS.DIM_MARKET_EVENT
        WHERE start_date >= CURRENT_DATE()
          AND (affected_industries ILIKE '%' || ? || '%' OR affected_industries ILIKE '%All%')
        ORDER BY start_date LIMIT 1""", [industry])
    is_upcoming = bool(upcoming)
    if not upcoming:
        upcoming = _rows(session, """
            SELECT event_name, start_date, end_date, impact_level
            FROM MARKETING_COPILOT.ANALYTICS.DIM_MARKET_EVENT
            WHERE affected_industries ILIKE '%' || ? || '%' ORDER BY start_date DESC LIMIT 1""", [industry])
    if upcoming:
        u = upcoming[0]
        timing["market_event"] = {"name": u["EVENT_NAME"], "start": str(u["START_DATE"]),
                                  "end": str(u["END_DATE"]), "impact": u["IMPACT_LEVEL"],
                                  "upcoming": is_upcoming}
    intel["market_timing"] = timing
    return intel
$$;

-- 4. Poster Prompt Builder (optionally enriched with GET_CREATIVE_INTELLIGENCE output)
DROP PROCEDURE IF EXISTS BUILD_POSTER_PROMPT(VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR);
CREATE OR REPLACE PROCEDURE BUILD_POSTER_PROMPT(
    CLIENT_NAME VARCHAR, PRODUCT_NAME VARCHAR, OBJECTIVE VARCHAR,
    TARGET_AUDIENCE VARCHAR, BRAND_COLOURS VARCHAR, TONE_KEYWORDS VARCHAR,
    CREATIVE_DIRECTION VARCHAR, EVENT_NAME VARCHAR, INTEL_JSON VARCHAR DEFAULT ''
)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
AS
$$
import json

def intel_clauses(intel):
    parts = []
    seg = intel.get("primary_segment") or {}
    if seg:
        interests = ", ".join(seg.get("interests") or [])
        parts.append(
            f"Cast and styling for the highest-converting segment '{seg.get('name')}' "
            f"({seg.get('age_band')}, {seg.get('gender_skew')}, {seg.get('income_level')} income"
            + (f"; interests: {interests}" if interests else "") + ").")
    chans = intel.get("top_channels") or []
    if chans:
        top = chans[0]
        parts.append(
            f"Compose primarily for {top['channel']} (best channel, avg ROAS {top['avg_roas']}x): "
            "bold focal point, legible at small sizes, clear space for a call to action.")
    brand = intel.get("brand") or {}
    if brand.get("dos"):
        parts.append("Brand dos: " + "; ".join(brand["dos"]) + ".")
    if brand.get("donts"):
        parts.append("Avoid: " + "; ".join(brand["donts"]) + ".")
    timing = intel.get("market_timing") or {}
    if timing.get("trend_peak_date") and timing.get("peak_in_past"):
        parts.append(
            f"Ride proven '{timing['trend_keyword']}' search demand (peaked {timing['trend_peak_date']}); "
            "convey energy and seasonal relevance.")
    elif timing.get("trend_peak_date"):
        parts.append(
            f"Timed for the '{timing['trend_keyword']}' search peak on {timing['trend_peak_date']}; "
            "convey urgency and seasonal relevance.")
    elif (timing.get("market_event") or {}).get("upcoming"):
        parts.append(f"Seasonal context: {timing['market_event']['name']}.")
    return " ".join(parts)

def run(session, client_name, product_name, objective, target_audience, brand_colours, tone_keywords, creative_direction, event_name, intel_json):
    event_ctx = f"Event: {event_name}. " if event_name else ""
    intel_ctx = ""
    if intel_json:
        try:
            intel_ctx = intel_clauses(json.loads(intel_json)) + " "
        except Exception:
            intel_ctx = ""
    return (
        f"Professional marketing poster for {client_name} promoting {product_name}. "
        f"Objective: {objective}. Audience: {target_audience}. "
        f"Brand colours: {brand_colours}. Tone: {tone_keywords}. "
        f"Direction: {creative_direction}. {event_ctx}{intel_ctx}"
        f"Style: Clean modern commercial advertising. Portrait orientation. No watermarks. No logos."
    )
$$;

-- 5. Audio Script Builder
CREATE OR REPLACE PROCEDURE BUILD_AUDIO_SCRIPT(
    CLIENT_NAME VARCHAR, PRODUCT_NAME VARCHAR, OBJECTIVE VARCHAR, TONE_KEYWORDS VARCHAR
)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
AS
$$
def run(session, client_name, product_name, objective, tone_keywords):
    return {
        "prompt": f"30-second script for {product_name} by {client_name}. Tone: {tone_keywords}. Goal: {objective}. Include: hook (5s), benefit (15s), emotional close (7s), CTA (3s).",
        "duration": "30 seconds",
        "format": "Radio / Digital Audio"
    }
$$;
