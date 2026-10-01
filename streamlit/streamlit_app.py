import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import re
import base64
import html as html_lib
import io
import zipfile
from datetime import datetime
from snowflake.snowpark.context import get_active_session
import streamlit.components.v1 as components

# -- Page config --
st.set_page_config(page_title="NovaSpark Marketing Co-Pilot", page_icon="📊", layout="wide")

# -- Color palette --
PRIMARY = "#0068FF"
SECONDARY = "#00D4AA"
ACCENT = "#FF6B35"
COLORS = [PRIMARY, SECONDARY, ACCENT, "#8B5CF6", "#F43F5E", "#FBBF24", "#34D399", "#60A5FA", "#A78BFA", "#FB923C"]
PLOTLY_TEMPLATE = "plotly_dark"
TODAY = datetime.now().strftime("%B %d, %Y")

# -- Session --
session = get_active_session()


def parse_agent_response(raw_response):
    """Extract clean readable text from any Cortex agent response format."""
    try:
        if isinstance(raw_response, str):
            try:
                parsed = json.loads(raw_response)
                return parse_agent_response(parsed)
            except Exception:
                return raw_response

        if isinstance(raw_response, dict):
            if "content" in raw_response:
                texts = []
                for block in raw_response["content"]:
                    if isinstance(block, dict):
                        if block.get("type") == "thinking":
                            continue
                        if block.get("type") == "tool_use":
                            continue
                        if block.get("type") == "text":
                            texts.append(block.get("text", ""))
                        elif "text" in block and isinstance(block["text"], str):
                            texts.append(block["text"])
                if texts:
                    return "\n\n".join([t for t in texts if t.strip()])

            if "text" in raw_response:
                return str(raw_response["text"])
            if "message" in raw_response:
                return str(raw_response["message"])
            if "response" in raw_response:
                return str(raw_response["response"])

        if isinstance(raw_response, list):
            texts = []
            for item in raw_response:
                parsed = parse_agent_response(item)
                if parsed and parsed.strip():
                    texts.append(parsed)
            return "\n\n".join(texts)

        return str(raw_response)
    except Exception as e:
        return f"Unable to parse response: {str(e)}"


def build_html_document(title, subtitle, metadata, content, confidence=None):
    conf_colours = {
        "HIGH": ("#00D4AA", "#003D30"),
        "MEDIUM": ("#FFD700", "#3D3000"),
        "LOW": ("#FF6B35", "#3D1500"),
    }
    conf_bg, conf_text = conf_colours.get(confidence, ("#6B7280", "#1F2937"))
    conf_badge = (
        f'<span style="background:{conf_bg};color:{conf_text};padding:4px 12px;'
        f'border-radius:20px;font-size:12px;font-weight:bold;letter-spacing:1px;">'
        f'{confidence}</span>'
    ) if confidence else ""

    meta_pills = "".join([
        f'<span style="background:#1E293B;color:#94A3B8;padding:4px 12px;'
        f'border-radius:20px;font-size:12px;margin-right:8px;">'
        f'<b style="color:#E2E8F0">{k}:</b> {v}</span>'
        for k, v in metadata.items()
    ])

    html_content = content
    html_content = re.sub(
        r'^### (.+)$',
        r'<h3 style="color:#00D4AA;margin-top:24px;margin-bottom:8px;font-size:16px;">\1</h3>',
        html_content, flags=re.MULTILINE)
    html_content = re.sub(
        r'^## (.+)$',
        r'<h2 style="color:#0068FF;margin-top:32px;margin-bottom:12px;font-size:20px;'
        r'border-bottom:2px solid #0068FF;padding-bottom:8px;">\1</h2>',
        html_content, flags=re.MULTILINE)
    html_content = re.sub(
        r'^# (.+)$',
        r'<h1 style="color:#FFFFFF;font-size:24px;">\1</h1>',
        html_content, flags=re.MULTILINE)
    html_content = re.sub(
        r'\*\*(.+?)\*\*',
        r'<strong style="color:#E2E8F0">\1</strong>',
        html_content)
    html_content = re.sub(
        r'^[-*] (.+)$',
        r'<li style="margin-bottom:6px;color:#CBD5E1;">\1</li>',
        html_content, flags=re.MULTILINE)
    html_content = re.sub(
        r'(<li[^>]*>.*?</li>\n?)+',
        lambda m: f'<ul style="padding-left:20px;margin:12px 0;">{m.group()}</ul>',
        html_content, flags=re.DOTALL)
    html_content = html_content.replace(
        '---', '<hr style="border:none;border-top:1px solid #1E293B;margin:24px 0;">')

    lines = html_content.split('\n')
    processed = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('<'):
            processed.append(
                f'<p style="color:#CBD5E1;line-height:1.7;margin-bottom:12px;">{stripped}</p>')
        else:
            processed.append(line)
    html_content = '\n'.join(processed)

    generated_date = datetime.now().strftime('%B %d, %Y at %H:%M')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0A0E27;color:#CBD5E1;min-height:100vh;padding:40px 20px;}}
.container{{max-width:900px;margin:0 auto;}}
.header{{background:linear-gradient(135deg,#0D1117 0%,#1a1f3a 100%);border:1px solid #1E293B;border-top:4px solid #0068FF;border-radius:12px;padding:40px;margin-bottom:32px;}}
.agency-tag{{color:#0068FF;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;}}
.doc-title{{font-size:32px;font-weight:800;color:#FFFFFF;line-height:1.2;margin-bottom:8px;}}
.doc-subtitle{{font-size:16px;color:#64748B;margin-bottom:24px;}}
.meta-row{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;}}
.content-card{{background:#0D1117;border:1px solid #1E293B;border-radius:12px;padding:40px;margin-bottom:24px;}}
table{{width:100%;border-collapse:collapse;margin:16px 0;}}
th{{background:#0068FF;color:white;padding:10px 14px;text-align:left;font-size:13px;font-weight:600;}}
td{{padding:10px 14px;border-bottom:1px solid #1E293B;color:#CBD5E1;font-size:14px;}}
tr:nth-child(even) td{{background:#0D1117;}}
tr:nth-child(odd) td{{background:#111827;}}
.footer{{text-align:center;padding:32px;color:#374151;font-size:12px;border-top:1px solid #1E293B;margin-top:40px;}}
.footer span{{color:#0068FF;font-weight:600;}}
@media print{{body{{background:white;color:black;}}.content-card{{border:1px solid #ddd;}}}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<div class="agency-tag">NovaSpark Agency</div>
<div class="doc-title">{title}</div>
<div class="doc-subtitle">{subtitle}</div>
<div class="meta-row">{meta_pills}{conf_badge}</div>
</div>
<div class="content-card">
{html_content}
</div>
<div class="footer">
Generated by <span>NovaSpark Co-Pilot</span> · Powered by <span>Snowflake Cortex</span> · {generated_date}
</div>
</div>
</body>
</html>"""


def js_download_button(content, filename, label="⬇️ Download", mime="text/html"):
    b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data_uri = f"data:{mime};base64,{b64}"
    button_html = f"""
    <button onclick="var a=document.createElement('a');a.href='{data_uri}';a.download='{filename}';document.body.appendChild(a);a.click();document.body.removeChild(a);"
        style="background:linear-gradient(135deg,#0068FF 0%,#0052CC 100%);color:white;border:none;padding:12px 24px;border-radius:8px;cursor:pointer;font-size:14px;font-weight:600;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;width:100%;transition:opacity 0.2s;letter-spacing:0.3px;"
        onmouseover="this.style.opacity='0.85'" onmouseout="this.style.opacity='1'">
        {label}
    </button>
    """
    components.html(button_html, height=60)


# -- Creative Studio functions (embedded for SiS compatibility) --
def _intel_clauses(intel):
    """Mirror of BUILD_POSTER_PROMPT's intelligence layer, used when the procedure is unavailable."""
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
        parts.append(
            f"Compose primarily for {chans[0]['channel']} (best channel, avg ROAS {chans[0]['avg_roas']}x): "
            "bold focal point, legible at small sizes, clear space for a call to action.")
    brand = intel.get("brand") or {}
    if brand.get("dos"):
        parts.append("Brand dos: " + "; ".join(brand["dos"]) + ".")
    if brand.get("donts"):
        parts.append("Avoid: " + "; ".join(brand["donts"]) + ".")
    timing = intel.get("market_timing") or {}
    if timing.get("trend_peak_date") and timing.get("peak_in_past"):
        parts.append(f"Ride proven '{timing['trend_keyword']}' search demand (peaked {timing['trend_peak_date']}); "
                     "convey energy and seasonal relevance.")
    elif timing.get("trend_peak_date"):
        parts.append(f"Timed for the '{timing['trend_keyword']}' search peak on {timing['trend_peak_date']}; "
                     "convey urgency and seasonal relevance.")
    elif (timing.get("market_event") or {}).get("upcoming"):
        parts.append(f"Seasonal context: {timing['market_event']['name']}.")
    return " ".join(parts)

def _build_poster_prompt(client_name, product_name, campaign_objective,
    target_audience, brand_colours, tone_keywords, creative_direction, event_name=None, intel=None):
    event_ctx = f"Event: {event_name}. " if event_name else ""
    intel_ctx = (_intel_clauses(intel) + " ") if intel else ""
    return (
        f"Professional marketing poster for {client_name} promoting {product_name}. "
        f"Objective: {campaign_objective}. Audience: {target_audience}. "
        f"Brand colours: {brand_colours}. Tone: {tone_keywords}. "
        f"Direction: {creative_direction}. {event_ctx}{intel_ctx}"
        f"Style: Clean modern commercial advertising. Portrait orientation. No watermarks. No logos."
    )

def _build_video_prompt(client_name, product_name, campaign_objective, creative_direction, event_name=None):
    event_ctx = f"Set during {event_name}. " if event_name else ""
    return (
        f"5-second cinematic brand video for {product_name} by {client_name}. {event_ctx}"
        f"Goal: {campaign_objective}. Visual: {creative_direction}. "
        f"Style: Premium brand film, smooth camera, vibrant colours. No text. No logos."
    )

def _generate_posters_gemini(prompt, api_key, count=3):
    if not api_key:
        return {"success": False, "demo_mode": True, "posters_b64": [], "error": "No API key provided"}
    try:
        return {"success": False, "demo_mode": True, "posters_b64": [],
                "error": "Poster generation requires Gemini API access. In Streamlit-in-Snowflake, outbound HTTP is not available on trial accounts. Use the poster prompt with Gemini AI Studio directly."}
    except Exception as exc:
        return {"success": False, "demo_mode": True, "posters_b64": [], "error": str(exc)}

def _build_storyboard_scenes():
    return [
        {"scene": 1, "duration": "0-1s", "description": "Opening hero shot -- product reveal", "camera": "Slow zoom in", "mood": "Anticipation"},
        {"scene": 2, "duration": "1-3s", "description": "Core benefit -- audience connection", "camera": "Medium shot, subtle pan", "mood": "Emotional resonance"},
        {"scene": 3, "duration": "3-4s", "description": "Product in use -- lifestyle context", "camera": "Close up detail", "mood": "Aspiration"},
        {"scene": 4, "duration": "4-5s", "description": "Brand end card -- tagline", "camera": "Static brand frame", "mood": "Trust"},
    ]

def _build_design_system(client_name, brand_colours, tone_keywords):
    colours = [c.strip() for c in brand_colours.split(",") if c.strip()]
    names = ["Primary", "Secondary", "Accent", "Background", "Text"]
    palette = [{"name": names[i] if i < len(names) else f"Colour {i+1}", "hex": c, "usage": f"{names[i]} elements"} for i, c in enumerate(colours[:5])]
    tones = [t.strip() for t in tone_keywords.split(",")]
    return {
        "client": client_name, "palette": palette, "tone": tones,
        "do": ["Use brand colours consistently", "Lead with benefits not features", "Show real people in real situations", "Use active voice"],
        "dont": ["Use competitor names", "Make unsubstantiated claims", "Crowd the composition", "Use generic stock imagery"]
    }

def generate_creative_assets(client_name, product_name, campaign_objective, target_audience,
    brand_colours, tone_keywords, creative_direction, gemini_api_key, event_name=None, intel=None):
    errors = {}
    results = {"intelligence": intel or {}}
    intel_json = json.dumps(intel) if intel else ""

    # Call Snowflake stored procedures instead of embedded functions
    try:
        ds_result = session.sql(f"""
            CALL MARKETING_COPILOT.SEMANTIC.BUILD_DESIGN_SYSTEM(
                $${client_name.replace('$$','$ $')}$$,
                $${brand_colours.replace('$$','$ $')}$$,
                $${tone_keywords.replace('$$','$ $')}$$
            )
        """).collect()
        results["design_system"] = json.loads(ds_result[0][0]) if ds_result else _build_design_system(client_name, brand_colours, tone_keywords)
    except Exception:
        results["design_system"] = _build_design_system(client_name, brand_colours, tone_keywords)

    # Poster prompt via stored procedure
    try:
        pp_result = session.sql(f"""
            CALL MARKETING_COPILOT.SEMANTIC.BUILD_POSTER_PROMPT(
                $${client_name.replace('$$','$ $')}$$,
                $${product_name.replace('$$','$ $')}$$,
                $${campaign_objective.replace('$$','$ $')}$$,
                $${target_audience.replace('$$','$ $')}$$,
                $${brand_colours.replace('$$','$ $')}$$,
                $${tone_keywords.replace('$$','$ $')}$$,
                $${creative_direction.replace('$$','$ $')}$$,
                $${(event_name or '').replace('$$','$ $')}$$,
                $${intel_json.replace('$$','$ $')}$$
            )
        """).collect()
        poster_prompt = pp_result[0][0] if pp_result else _build_poster_prompt(client_name, product_name, campaign_objective, target_audience, brand_colours, tone_keywords, creative_direction, event_name, intel)
    except Exception:
        poster_prompt = _build_poster_prompt(client_name, product_name, campaign_objective, target_audience, brand_colours, tone_keywords, creative_direction, event_name, intel)

    # Gemini poster generation (still direct HTTP since EAI not available on trial)
    poster_result = _generate_posters_gemini(poster_prompt, gemini_api_key, count=3)
    results["posters_b64"] = poster_result.get("posters_b64", [])
    results["poster_prompt"] = poster_prompt
    results["poster_demo_mode"] = poster_result.get("demo_mode", False)
    if poster_result.get("error"):
        errors["posters"] = poster_result["error"]

    # Storyboard via stored procedure
    try:
        sb_result = session.sql(f"""
            CALL MARKETING_COPILOT.SEMANTIC.GENERATE_STORYBOARD(
                $${client_name.replace('$$','$ $')}$$,
                $${product_name.replace('$$','$ $')}$$,
                $${campaign_objective.replace('$$','$ $')}$$,
                $${creative_direction.replace('$$','$ $')}$$
            )
        """).collect()
        sb_data = json.loads(sb_result[0][0]) if sb_result else {}
        results["hero_scenes"] = sb_data.get("scenes", _build_storyboard_scenes())
        results["video_prompt"] = sb_data.get("video_prompt", _build_video_prompt(client_name, product_name, campaign_objective, creative_direction, event_name))
    except Exception:
        results["hero_scenes"] = _build_storyboard_scenes()
        results["video_prompt"] = _build_video_prompt(client_name, product_name, campaign_objective, creative_direction, event_name)

    results["video_message"] = "Video storyboard generated via Snowflake MCP procedure. Veo 2 access requires allowlist -- showing scene breakdown instead."

    # Audio script via stored procedure
    try:
        as_result = session.sql(f"""
            CALL MARKETING_COPILOT.SEMANTIC.BUILD_AUDIO_SCRIPT(
                $${client_name.replace('$$','$ $')}$$,
                $${product_name.replace('$$','$ $')}$$,
                $${campaign_objective.replace('$$','$ $')}$$,
                $${tone_keywords.replace('$$','$ $')}$$
            )
        """).collect()
        results["audio_script"] = json.loads(as_result[0][0]) if as_result else {"prompt": "", "duration": "30 seconds", "format": "Radio / Digital Audio"}
    except Exception:
        results["audio_script"] = {
            "prompt": f"30-second script for {product_name} by {client_name}. Tone: {tone_keywords}. Goal: {campaign_objective}. Include: hook (5s), benefit (15s), emotional close (7s), CTA (3s).",
            "duration": "30 seconds", "format": "Radio / Digital Audio"
        }

    results["campaign_meta"] = {"client": client_name, "product": product_name, "objective": campaign_objective, "audience": target_audience, "event": event_name or "N/A"}
    results["errors"] = errors
    return results

def build_assets_zip(assets):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i, p in enumerate(assets.get("posters_b64", [])[:3]):
            if p:
                zf.writestr(f"poster_{i+1}.png", base64.b64decode(p))
        ds = assets.get("design_system", {})
        if ds:
            zf.writestr("design_system.json", json.dumps(ds, indent=2))
        zf.writestr("creative_prompts.json", json.dumps({
            "poster_prompt": assets.get("poster_prompt", ""),
            "video_prompt": assets.get("video_prompt", ""),
            "audio_script": assets.get("audio_script", {}).get("prompt", "")
        }, indent=2))
        scenes = assets.get("hero_scenes", [])
        if scenes:
            zf.writestr("video_storyboard.json", json.dumps(scenes, indent=2))
    return buf.getvalue() or b"no-assets"


def run_query(sql):
    return session.sql(sql).to_pandas()


# -- Cached data loaders --
@st.cache_data(ttl=300)
def load_clients():
    return run_query("SELECT client_id, client_name, industry, region FROM MARKETING_COPILOT.ANALYTICS.DIM_CLIENT ORDER BY client_name")


@st.cache_data(ttl=300)
def load_products(client_id):
    return run_query(f"SELECT product_id, product_name, category, price_tier FROM MARKETING_COPILOT.ANALYTICS.DIM_PRODUCT WHERE client_id = '{client_id}' ORDER BY product_name")


@st.cache_data(ttl=300)
def load_client_kpis(client_id):
    return run_query(f"""
        SELECT
            (SELECT COUNT(DISTINCT campaign_id) FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN WHERE client_id = '{client_id}') AS total_campaigns,
            ROUND(AVG(roas), 2) AS avg_roas,
            SUM(spend_usd) AS total_spend,
            SUM(revenue_usd) AS total_revenue,
            SUM(impressions) AS total_impressions,
            SUM(conversions) AS total_conversions
        FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS
        WHERE client_id = '{client_id}'
    """)


@st.cache_data(ttl=300)
def load_sentiment(client_id):
    return run_query(f"""
        SELECT ROUND(AVG(sentiment_score), 3) AS avg_sentiment,
               ROUND(AVG(rating), 1) AS avg_rating,
               COUNT(*) AS feedback_count
        FROM MARKETING_COPILOT.ANALYTICS.FACT_CUSTOMER_FEEDBACK
        WHERE client_id = '{client_id}'
    """)


@st.cache_data(ttl=300)
def load_channel_roas(client_id):
    return run_query(f"""
        SELECT channel_name, ROUND(AVG(roas), 2) AS avg_roas,
               SUM(spend_usd) AS total_spend, SUM(revenue_usd) AS total_revenue
        FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS
        WHERE client_id = '{client_id}'
        GROUP BY channel_name ORDER BY avg_roas DESC
    """)


@st.cache_data(ttl=300)
def load_monthly_revenue(client_id):
    return run_query(f"""
        SELECT DATE_TRUNC('MONTH', date) AS month,
               SUM(revenue_usd) AS monthly_revenue,
               SUM(spend_usd) AS monthly_spend
        FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS
        WHERE client_id = '{client_id}'
        GROUP BY month ORDER BY month
    """)


@st.cache_data(ttl=300)
def load_top_campaigns(client_id, limit=5):
    return run_query(f"""
        SELECT campaign_name, campaign_type,
               SUM(revenue_usd) AS revenue, SUM(spend_usd) AS spend,
               ROUND((SUM(revenue_usd) - SUM(spend_usd)) / NULLIF(SUM(spend_usd), 0) * 100, 1) AS roi_pct
        FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS
        WHERE client_id = '{client_id}'
        GROUP BY campaign_name, campaign_type
        ORDER BY roi_pct DESC LIMIT {limit}
    """)


@st.cache_data(ttl=300)
def load_budget_by_type(client_id):
    return run_query(f"""
        SELECT campaign_type, SUM(total_budget_usd) AS budget
        FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN
        WHERE client_id = '{client_id}'
        GROUP BY campaign_type ORDER BY budget DESC
    """)


@st.cache_data(ttl=300)
def load_channel_history(client_id):
    return run_query(f"""
        SELECT channel_name, ROUND(AVG(roas), 3) AS avg_roas,
               ROUND(AVG(ctr), 6) AS avg_ctr,
               ROUND(AVG(conversion_rate), 6) AS avg_conv_rate,
               ROUND(AVG(cpc), 2) AS avg_cpc,
               COUNT(DISTINCT date) AS data_points
        FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS
        WHERE client_id = '{client_id}'
        GROUP BY channel_name
    """)


@st.cache_data(ttl=300)
def load_creative_intelligence(client_name, event_name=""):
    """Top channels, primary segment, brand guardrails and market timing from GET_CREATIVE_INTELLIGENCE."""
    try:
        res = session.sql(f"""
            CALL MARKETING_COPILOT.SEMANTIC.GET_CREATIVE_INTELLIGENCE(
                $${client_name.replace('$$','$ $')}$$,
                $${(event_name or '').replace('$$','$ $')}$$
            )
        """).collect()
        return json.loads(res[0][0]) if res else {}
    except Exception:
        return {}


# -- Agent helpers --
INCOMPLETE_MARKERS = [
    "time limit", "reached the time limit", "may be incomplete",
    "continue working", "Would you like me to continue",
    "I've reached the", "token limit",
]


def response_is_incomplete(text):
    return any(m.lower() in text.lower() for m in INCOMPLETE_MARKERS)


def call_named_agent(agent_fqn, prompt):
    request_body = json.dumps(
        {"messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]}
    )
    request_body = request_body.replace("$$", "$ $")
    sql = f"""
        SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN(
            '{agent_fqn}',
            $${request_body}$$
        ) AS response
    """
    try:
        result = session.sql(sql).collect()
    except Exception as e:
        return f"Error calling agent: {str(e)}"
    raw = result[0]["RESPONSE"]
    try:
        resp = json.loads(raw)
        if "message" in resp and resp.get("code"):
            return f"Agent error ({resp.get('code')}): {resp['message']}"
        messages = resp.get("messages", [])
        texts = []
        for m in messages:
            if m.get("role") == "assistant":
                parsed = parse_agent_response(m)
                if parsed and parsed.strip():
                    texts.append(parsed)
        return "\n\n".join(texts) if texts else parse_agent_response(raw)
    except Exception:
        return parse_agent_response(raw)


def call_agent(prompt):
    return call_named_agent('MARKETING_COPILOT.SEMANTIC.MARKETING_COPILOT', prompt)


MAX_CONTINUATIONS = 3


def call_agent_with_auto_continue(agent_fqn, initial_prompt, continue_prompt_fn):
    result = call_named_agent(agent_fqn, initial_prompt)
    for i in range(MAX_CONTINUATIONS):
        if not response_is_incomplete(result):
            break
        continuation = call_named_agent(agent_fqn, continue_prompt_fn(i + 1))
        result = result.rstrip() + "\n\n" + continuation
    return result


def format_usd(val):
    if val >= 1_000_000:
        return f"${val/1_000_000:,.1f}M"
    if val >= 1_000:
        return f"${val/1_000:,.1f}K"
    return f"${val:,.0f}"


def format_number(val):
    if val >= 1_000_000:
        return f"{val/1_000_000:,.1f}M"
    if val >= 1_000:
        return f"{val/1_000:,.1f}K"
    return f"{val:,.0f}"


def render_agent_markdown(raw):
    """Render agent response as formatted markdown with expandable sections."""
    text = parse_agent_response(raw) if not isinstance(raw, str) else raw
    if not text or text.startswith("Error") or text.startswith("Agent error") or text.startswith("Unable to parse"):
        st.error("Something went wrong. Please try again.")
        with st.expander("Technical details"):
            st.code(str(raw))
        return

    sections = text.split("\n## ")
    if len(sections) > 1:
        st.markdown(sections[0])
        for sec in sections[1:]:
            lines = sec.split("\n")
            title = lines[0].strip().lstrip("#").strip()
            body = "\n".join(lines[1:])
            with st.expander(f"📌 {title}", expanded=True):
                st.markdown(body)
    else:
        st.markdown(text)


# ============================
# SIDEBAR
# ============================
with st.sidebar:
    st.markdown("## 🚀 NovaSpark Agency")
    st.markdown("##### Marketing Co-Pilot & Pitch Engine")
    st.divider()

    clients_df = load_clients()
    client_names = clients_df["CLIENT_NAME"].tolist()
    selected_client = st.selectbox("Select Client", client_names, index=0)
    client_row = clients_df[clients_df["CLIENT_NAME"] == selected_client].iloc[0]
    client_id = client_row["CLIENT_ID"]

    st.caption(f"**Industry:** {client_row['INDUSTRY']}  \n**Region:** {client_row['REGION']}")
    st.divider()

    products_df = load_products(client_id)
    product_names = products_df["PRODUCT_NAME"].tolist()
    selected_product = st.selectbox("Select Product", product_names, index=0) if product_names else "N/A"

    objective = st.selectbox("Campaign Objective", [
        "Brand Awareness", "Lead Generation", "Sales Conversion", "Customer Retention"
    ])

    budget = st.number_input("Campaign Budget (USD)", min_value=10000, max_value=10000000, value=200000, step=10000, format="%d")
    st.divider()

    analyze_btn = st.button("🎯 Analyze & Recommend", type="primary", use_container_width=True)

# ============================
# MAIN AREA
# ============================
st.title(f"📊 {selected_client} Marketing Dashboard")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Client Intelligence",
    "🎯 Campaign Recommendation",
    "🔀 What-If Analysis",
    "📋 Generate Pitch",
    "🌍 Event Intelligence",
    "🎨 Creative Studio"
])

# ============================
# TAB 1: Client Intelligence
# ============================
with tab1:
    st.subheader("Client Overview")
    ov1, ov2, ov3 = st.columns(3)
    ov1.metric("Industry", client_row["INDUSTRY"])
    ov2.metric("Region", client_row["REGION"])
    ov3.metric("Products", len(product_names))

    st.subheader("Performance Snapshot")
    kpis = load_client_kpis(client_id)
    sentiment = load_sentiment(client_id)
    k = kpis.iloc[0]
    s = sentiment.iloc[0]

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Campaigns", int(k["TOTAL_CAMPAIGNS"]))
    c2.metric("Avg ROAS", f"{k['AVG_ROAS']}x")
    c3.metric("Total Spend", format_usd(k["TOTAL_SPEND"]))
    c4.metric("Total Revenue", format_usd(k["TOTAL_REVENUE"]))
    c5.metric("Total Conversions", format_number(k["TOTAL_CONVERSIONS"]))
    c6.metric("Avg Sentiment", f"{s['AVG_SENTIMENT']:.2f}")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("ROAS by Channel")
        channel_df = load_channel_roas(client_id)
        fig = px.bar(channel_df, x="CHANNEL_NAME", y="AVG_ROAS",
                     color_discrete_sequence=[PRIMARY],
                     template=PLOTLY_TEMPLATE)
        fig.update_layout(xaxis_title="Channel", yaxis_title="Avg ROAS", height=380, margin=dict(t=20, b=40))
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Monthly Revenue Trend")
        monthly_df = load_monthly_revenue(client_id)
        fig2 = px.line(monthly_df, x="MONTH", y="MONTHLY_REVENUE",
                       color_discrete_sequence=[SECONDARY],
                       template=PLOTLY_TEMPLATE)
        fig2.update_layout(xaxis_title="Month", yaxis_title="Revenue (USD)", height=380, margin=dict(t=20, b=40))
        st.plotly_chart(fig2, use_container_width=True)

    col_left2, col_right2 = st.columns(2)

    with col_left2:
        st.subheader("Top 5 Campaigns by ROI %")
        top_camp = load_top_campaigns(client_id, 5)
        fig3 = px.bar(top_camp, x="ROI_PCT", y="CAMPAIGN_NAME", orientation="h",
                      color_discrete_sequence=[ACCENT],
                      template=PLOTLY_TEMPLATE)
        fig3.update_layout(xaxis_title="ROI %", yaxis_title="", height=380, margin=dict(t=20, b=40, l=200))
        st.plotly_chart(fig3, use_container_width=True)

    with col_right2:
        st.subheader("Budget by Campaign Type")
        budget_type = load_budget_by_type(client_id)
        fig4 = px.pie(budget_type, values="BUDGET", names="CAMPAIGN_TYPE",
                      color_discrete_sequence=COLORS,
                      template=PLOTLY_TEMPLATE)
        fig4.update_layout(height=380, margin=dict(t=20, b=40))
        st.plotly_chart(fig4, use_container_width=True)


# ============================
# TAB 2: Campaign Recommendation
# ============================
with tab2:
    if analyze_btn:
        with st.spinner("Analyzing campaign data and generating recommendation..."):
            prompt = (
                f"Create a detailed campaign recommendation for {selected_client} "
                f"for their product '{selected_product}'. "
                f"Campaign objective: {objective}. "
                f"Budget: ${budget:,}. "
                f"Include: recommended channels with budget allocation percentages, "
                f"target audience segments, expected KPIs (ROAS, impressions, conversions), "
                f"and strategy rationale. Ground everything in historical performance data. "
                f"Use markdown headers (## Section Title) to structure each section."
            )
            response = call_agent_with_auto_continue(
                'MARKETING_COPILOT.SEMANTIC.MARKETING_COPILOT',
                prompt,
                lambda n: (
                    f"Continue the campaign recommendation you were writing for {selected_client}. "
                    f"Pick up exactly where you left off. Do not repeat sections already written. "
                    f"This is continuation #{n}."
                )
            )
            st.session_state["recommendation"] = response
            st.session_state["recommendation_approved"] = False

    if "recommendation" in st.session_state:
        rec = st.session_state["recommendation"]

        st.markdown(f"## 📋 Campaign Recommendation")
        st.markdown(f"**Client:** {selected_client} | **Product:** {selected_product} | **Objective:** {objective} | **Budget:** ${budget:,}")
        st.divider()

        render_agent_markdown(rec)

        if response_is_incomplete(rec):
            st.warning("The recommendation may still be incomplete after auto-continuation.")

        st.divider()

        # Download recommendation
        rec_html = build_html_document(
            title="Campaign Recommendation",
            subtitle=f"{selected_client} — {selected_product}",
            metadata={"Client": selected_client, "Product": selected_product,
                      "Objective": objective, "Budget": f"${budget:,}", "Date": TODAY},
            content=parse_agent_response(rec)
        )

        dl_col, approve_col, regen_col = st.columns([1, 1, 1])
        with dl_col:
            js_download_button(
                content=rec_html,
                filename=f"{selected_client}_{selected_product}_recommendation.html",
                label="⬇️ Download Recommendation"
            )
        with approve_col:
            if st.button("✅ Approve Recommendation", type="primary", use_container_width=True):
                st.session_state["recommendation_approved"] = True
                st.success("Recommendation approved! Go to **Generate Pitch** tab.")
        with regen_col:
            if st.button("🔄 Regenerate", use_container_width=True):
                st.session_state.pop("recommendation", None)
                st.experimental_rerun()
    else:
        st.info("Select a client, product, and objective in the sidebar, then click **Analyze & Recommend** to generate a campaign recommendation.")


# ============================
# TAB 3: What-If Analysis
# ============================
with tab3:
    st.subheader("Budget Allocation Scenario Comparison")
    st.caption("Adjust the proposed allocation sliders to see projected impact vs. current baseline.")

    ch_history = load_channel_history(client_id)
    if ch_history.empty:
        st.warning("No channel history available for this client.")
    else:
        top_channels = ch_history.sort_values("AVG_ROAS", ascending=False).head(5)
        channel_list = top_channels["CHANNEL_NAME"].tolist()

        n_channels = len(channel_list)
        default_pct = 100 // n_channels

        col_current, col_proposed = st.columns(2)

        current_alloc = {}
        proposed_alloc = {}

        with col_current:
            st.markdown("### 📌 Current Allocation (equal split)")
            for ch in channel_list:
                current_alloc[ch] = budget * default_pct / 100
                st.markdown(f"- **{ch}**: {format_usd(current_alloc[ch])} ({default_pct}%)")

        with col_proposed:
            st.markdown("### 🔄 Proposed Allocation")
            remaining = 100
            for i, ch in enumerate(channel_list):
                default_val = min(default_pct, remaining)
                pct = st.slider(f"{ch}", 0, 100, default_val, 5, key=f"slider_{ch}")
                proposed_alloc[ch] = budget * pct / 100
                remaining -= pct

            if remaining != 0:
                st.warning(f"Allocation {'over' if remaining < 0 else 'under'} by {abs(remaining)}%")

        st.divider()

        ch_map = dict(zip(ch_history["CHANNEL_NAME"], ch_history.itertuples(index=False)))
        results = []
        for ch in channel_list:
            if ch in ch_map:
                row = ch_map[ch]
                cur_budget = current_alloc.get(ch, 0)
                prop_budget = proposed_alloc.get(ch, 0)
                roas = float(row.AVG_ROAS) if row.AVG_ROAS else 1.0
                cpc = float(row.AVG_CPC) if row.AVG_CPC and row.AVG_CPC > 0 else 1.0
                conv_rate = float(row.AVG_CONV_RATE) if row.AVG_CONV_RATE else 0.02

                cur_rev = cur_budget * roas
                prop_rev = prop_budget * roas
                cur_clicks = cur_budget / cpc
                prop_clicks = prop_budget / cpc
                cur_conv = cur_clicks * conv_rate
                prop_conv = prop_clicks * conv_rate

                results.append({
                    "Channel": ch,
                    "Current Budget": cur_budget,
                    "Proposed Budget": prop_budget,
                    "Current Revenue": cur_rev,
                    "Proposed Revenue": prop_rev,
                    "Hist ROAS": roas,
                    "Current Conv": cur_conv,
                    "Proposed Conv": prop_conv,
                    "Delta Revenue": prop_rev - cur_rev,
                })

        if results:
            res_df = pd.DataFrame(results)
            total_cur_rev = res_df["Current Revenue"].sum()
            total_prop_rev = res_df["Proposed Revenue"].sum()
            total_cur_conv = res_df["Current Conv"].sum()
            total_prop_conv = res_df["Proposed Conv"].sum()
            delta_rev = total_prop_rev - total_cur_rev
            delta_conv = total_prop_conv - total_cur_conv

            m1, m2, m3 = st.columns(3)
            m1.metric("Projected Revenue (Current)", format_usd(total_cur_rev))
            m2.metric("Projected Revenue (Proposed)", format_usd(total_prop_rev),
                       delta=format_usd(delta_rev))
            m3.metric("Projected Conversions (Proposed)", format_number(total_prop_conv),
                       delta=format_number(delta_conv))

            # Recommendation box
            if total_prop_rev > total_cur_rev:
                st.success(f"✅ **Proposed scenario recommended.** Expected revenue increase: {format_usd(delta_rev)}")
            elif total_prop_rev < total_cur_rev:
                st.warning(f"⚠️ **Current scenario performs better.** Proposed change reduces revenue by {format_usd(abs(delta_rev))}")
            else:
                st.info("Both scenarios project equal revenue.")

            st.divider()

            comp_df = pd.melt(
                res_df[["Channel", "Current Revenue", "Proposed Revenue"]],
                id_vars="Channel", var_name="Scenario", value_name="Revenue"
            )
            fig5 = px.bar(comp_df, x="Channel", y="Revenue", color="Scenario", barmode="group",
                          color_discrete_sequence=[PRIMARY, ACCENT],
                          template=PLOTLY_TEMPLATE)
            fig5.update_layout(height=400, margin=dict(t=20, b=40))
            st.plotly_chart(fig5, use_container_width=True)

            # Download What-If report
            st.divider()
            cur_alloc_lines = "\n".join([f"- {ch}: {format_usd(current_alloc[ch])} ({default_pct}%)" for ch in channel_list])
            prop_alloc_lines = "\n".join([f"- {ch}: {format_usd(proposed_alloc.get(ch, 0))}" for ch in channel_list])
            whatif_content = (
                f"## Current Scenario (Equal Split)\n{cur_alloc_lines}\n"
                f"- **Projected Revenue:** {format_usd(total_cur_rev)}\n"
                f"- **Projected Conversions:** {format_number(total_cur_conv)}\n\n"
                f"## Proposed Scenario\n{prop_alloc_lines}\n"
                f"- **Projected Revenue:** {format_usd(total_prop_rev)}\n"
                f"- **Projected Conversions:** {format_number(total_prop_conv)}\n\n"
                f"## Impact Analysis\n"
                f"- Revenue Change: {format_usd(delta_rev)}\n"
                f"- Conversion Change: {format_number(delta_conv)}\n"
                f"- Recommendation: {'Proposed' if total_prop_rev > total_cur_rev else 'Current'} scenario recommended"
            )
            whatif_html = build_html_document(
                title="What-If Scenario Analysis",
                subtitle=f"{selected_client} — Budget Reallocation",
                metadata={"Client": selected_client, "Budget": f"${budget:,}", "Date": TODAY},
                content=whatif_content
            )
            js_download_button(
                content=whatif_html,
                filename=f"{selected_client}_whatif_analysis.html",
                label="⬇️ Download Analysis"
            )


# ============================
# TAB 4: Generate Pitch
# ============================
with tab4:
    if st.session_state.get("recommendation_approved"):
        st.markdown(f"## 📋 Campaign Pitch")
        st.markdown(f"**Client:** {selected_client} | **Product:** {selected_product} | **Budget:** ${budget:,} | **Date:** {TODAY}")
        st.divider()

        if "pitch_content" not in st.session_state:
            if st.button("📝 Generate Full Pitch", type="primary"):
                with st.spinner("Generating pitch document (auto-continues if needed)..."):
                    prompt = (
                        f"Generate a complete client-ready campaign pitch document for {selected_client}, "
                        f"product: {selected_product}, objective: {objective}, budget: ${budget:,}. "
                        f"Include these sections with ## markdown headers: "
                        f"1. Executive Summary, "
                        f"2. Client & Product Overview, "
                        f"3. Campaign Objective & KPIs, "
                        f"4. Target Audience Analysis, "
                        f"5. Channel Strategy with budget allocation, "
                        f"6. Creative Direction (based on brand guidelines), "
                        f"7. Expected Impact and projected metrics. "
                        f"End with a Confidence Level (HIGH/MEDIUM/LOW) with explanation. "
                        f"Make it professional, data-backed, and aligned with the brand voice."
                    )
                    pitch = call_agent_with_auto_continue(
                        'MARKETING_COPILOT.SEMANTIC.MARKETING_COPILOT',
                        prompt,
                        lambda n: (
                            f"Continue the campaign pitch document you were writing for {selected_client}, "
                            f"product: {selected_product}. Pick up exactly where you left off. "
                            f"Do not repeat sections already written. Complete the remaining sections. "
                            f"This is continuation #{n}."
                        )
                    )
                    st.session_state["pitch_content"] = pitch
                    st.experimental_rerun()
        else:
            pitch = st.session_state["pitch_content"]

            if response_is_incomplete(pitch):
                st.warning("The pitch may still be incomplete after auto-continuation attempts.")

            render_agent_markdown(pitch)

            st.divider()

            pitch_html = build_html_document(
                title="Campaign Pitch",
                subtitle=f"{selected_client} — {selected_product}",
                metadata={"Client": selected_client, "Product": selected_product,
                          "Objective": objective, "Budget": f"${budget:,}", "Date": TODAY},
                content=parse_agent_response(pitch)
            )

            dl_col, reset_col = st.columns([1, 4])
            with dl_col:
                safe_product = selected_product.replace(" ", "_").replace("/", "_")
                js_download_button(
                    content=pitch_html,
                    filename=f"{selected_client}_{safe_product}_pitch.html",
                    label="⬇️ Download Pitch"
                )
            with reset_col:
                if st.button("🔄 Start Over"):
                    for key in ["recommendation", "recommendation_approved", "pitch_content"]:
                        st.session_state.pop(key, None)
                    st.experimental_rerun()
    else:
        st.info("Approve a campaign recommendation in the **Campaign Recommendation** tab first to generate a pitch document.")


# ============================
# TAB 6: Creative Studio
# ============================
with tab6:
    st.subheader("Creative Studio")
    st.caption("Generate campaign posters, video storyboards, and design systems powered by Gemini.")

    # -- Cortex intelligence layer: grounds the creative brief in this client's data --
    cs_client = selected_client
    cs_event_default = st.session_state.get("cs_event", st.session_state.get("ei_event", "")) or ""
    cs_intel = load_creative_intelligence(cs_client, cs_event_default)
    cs_brand = cs_intel.get("brand") or {}

    # -- Section 1: Creative Brief Form --
    cs_col1, cs_col2 = st.columns([3, 2])

    with cs_col1:
        cs_product = selected_product
        cs_objective = objective

        cs_audience = st.text_area(
            "Target Audience",
            value=st.session_state.get("recommendation_audience", "Adults 25-45, digitally savvy, brand-conscious"),
            height=68, key="cs_audience"
        )
        cs_colours = st.text_input(
            "Brand Colours (comma-separated hex)",
            value=cs_brand.get("palette") or "#0068FF, #00D4AA, #FF6B35",
            key=f"cs_colours_{cs_client}"
        )
        cs_tone = st.text_input(
            "Tone Keywords",
            value=st.session_state.get("recommendation_tone") or ", ".join(cs_brand.get("tone") or []) or "bold, modern, confident, approachable",
            key=f"cs_tone_{cs_client}"
        )
        cs_direction = st.text_area(
            "Creative Direction",
            value=st.session_state.get("recommendation_creative", "Clean modern visuals with lifestyle imagery showing product in everyday premium context"),
            height=68, key="cs_direction"
        )
        cs_event = st.text_input(
            "Event Name (optional)",
            value=cs_event_default,
            key="cs_event"
        )
        cs_gemini_key = st.text_input(
            "Gemini API Key",
            type="password",
            help="Get free at aistudio.google.com",
            key="cs_gemini_key"
        )

    with cs_col2:
        st.info(
            "**How Creative Studio Works**\n\n"
            "1. **Cortex Strategy -> Creative Brief**\n"
            "   Auto-filled from your campaign recommendation\n\n"
            "2. **Cortex Intelligence + Gemini 2.5 Flash Image -> 3 Marketing Posters**\n"
            "   Portrait format, commercial quality\n\n"
            "3. **Veo 2 -> Video Storyboard**\n"
            "   5-second brand film concept\n\n"
            "4. **Download all as ZIP**"
        )
        components.html("""
        <div style="background:#0D1117;border-left:4px solid #0068FF;border-radius:8px;padding:16px;margin-top:12px;">
            <div style="color:#E2E8F0;font-size:13px;line-height:1.6;">
                <strong style="color:#0068FF;">🚀 Our Recommendation to Snowflake:</strong><br>
                Build <strong>Cortex Image</strong> + <strong>Cortex Video</strong> to make this 100% native.
                The brand data is already in Snowflake — we just need the canvas.
            </div>
        </div>
        """, height=100)

    # -- Section 1b: Cortex Intelligence Panel --
    st.markdown("#### 🧠 Cortex Intelligence Feeding This Brief")
    if not cs_intel:
        st.warning("Could not load creative intelligence (procedure GET_CREATIVE_INTELLIGENCE). Posters will use the brief fields only.")
    else:
        esc = html_lib.escape
        chans = cs_intel.get("top_channels") or []
        seg = cs_intel.get("primary_segment") or {}
        timing = cs_intel.get("market_timing") or {}

        def _card(color, title, body):
            return (f'<div style="flex:1;min-width:220px;background:#0D1117;border:1px solid #1E293B;'
                    f'border-top:3px solid {color};border-radius:10px;padding:14px;">'
                    f'<div style="color:{color};font-size:11px;font-weight:700;letter-spacing:1px;margin-bottom:8px;">{title}</div>'
                    f'<div style="color:#CBD5E1;font-size:12.5px;line-height:1.55;">{body}</div></div>')

        chan_body = "<br>".join(
            f"<b style='color:#E2E8F0'>{esc(c['channel'])}</b> &middot; ROAS {c['avg_roas']:.2f}x &middot; CTR {c['avg_ctr']*100:.2f}%"
            for c in chans) or "No channel history"
        seg_body = (f"<b style='color:#E2E8F0'>{esc(seg.get('name', ''))}</b><br>"
                    f"{esc(str(seg.get('age_band', '')))} &middot; {esc(str(seg.get('gender_skew', '')))} &middot; {esc(str(seg.get('income_level', '')))} income<br>"
                    f"Conv. rate {seg.get('avg_conversion_rate', 0)*100:.2f}% &middot; ROAS {seg.get('avg_roas', 0):.2f}x<br>"
                    f"Interests: {esc(', '.join(seg.get('interests') or []))}") if seg else "No segment data"
        guard_body = ("<b style='color:#00D4AA'>Do</b><br>" + "<br>".join("&#10003; " + esc(d) for d in cs_brand.get("dos", [])[:4])
                      + "<br><b style='color:#FF6B35'>Avoid</b><br>" + "<br>".join("&#10007; " + esc(d) for d in cs_brand.get("donts", [])[:4])) if cs_brand else "No brand guidelines"
        if timing.get("trend_peak_date"):
            time_body = (f"<b style='color:#E2E8F0'>{esc(timing['trend_keyword'])}</b> "
                         f"{'peaked' if timing.get('peak_in_past') else 'peaks'} <b>{esc(timing['trend_peak_date'])}</b> "
                         f"(score {timing.get('peak_score', 0):.0f})<br>")
            if timing.get("recommended_launch"):
                time_body += (f"Recommended launch: <b style='color:#E2E8F0'>{esc(timing['recommended_launch'])}</b> "
                              "(6 weeks before peak)<br>")
            else:
                time_body += "Peak already passed in the 3-month trend window &mdash; re-run Event Intelligence closer to the event for launch timing.<br>"
            time_body += f"<span style='color:#64748B'>{esc(timing.get('source', ''))}</span>"
        else:
            time_body = "No intelligence run for this event yet &mdash; run Event Intelligence (Tab 5) to add trend timing."
        mev = timing.get("market_event") or {}
        if mev:
            label = "Next market event" if mev.get("upcoming") else "Latest relevant market event"
            time_body += f"<br>{label}: {esc(mev.get('name', ''))} ({esc(mev.get('start', ''))}, {esc(str(mev.get('impact', '')))} impact)"

        components.html(
            '<div style="display:flex;gap:12px;flex-wrap:wrap;font-family:sans-serif;">'
            + _card("#0068FF", "TOP CHANNELS BY ROAS", chan_body)
            + _card("#00D4AA", "PRIMARY SEGMENT", seg_body)
            + _card("#FF6B35", "BRAND GUARDRAILS", guard_body)
            + _card("#8B5CF6", "MARKET TIMING", time_body)
            + "</div>", height=250)

    # -- Section 2: Generate --
    generate_creative = st.button("✨ Generate Creative Assets", type="primary", use_container_width=True, key="cs_generate")

    if generate_creative:
        with st.spinner("Generating your campaign creative with Gemini..."):
            assets = generate_creative_assets(
                client_name=cs_client,
                product_name=cs_product,
                campaign_objective=cs_objective,
                target_audience=cs_audience,
                brand_colours=cs_colours,
                tone_keywords=cs_tone,
                creative_direction=cs_direction,
                gemini_api_key=cs_gemini_key,
                event_name=cs_event if cs_event else None,
                intel=load_creative_intelligence(cs_client, cs_event or "")
            )
            st.session_state["creative_assets"] = assets

        gen_errors = assets.get("errors", {})
        if gen_errors:
            st.warning(f"Some assets had issues: {gen_errors}")

    # -- Section 3: Creative Workspace Display --
    if "creative_assets" in st.session_state:
        assets = st.session_state["creative_assets"]
        ds = assets.get("design_system") or {}
        palette = ds.get("palette") or []
        posters = assets.get("posters_b64") or []
        hero_scenes = assets.get("hero_scenes") or []
        audio_script = assets.get("audio_script") or {}

        st.divider()

        # ROW 1: Video Storyboard (rendered as visual scene cards)
        st.markdown("#### 🎬 Video Storyboard (5-Second Brand Film)")
        if hero_scenes:
            scene_cards_html = '<div style="display:flex;gap:12px;flex-wrap:wrap;">'
            scene_icons = ["🎬", "💡", "🌟", "🏷️"]
            scene_colors = ["#0068FF", "#00D4AA", "#FF6B35", "#8B5CF6"]
            for idx, scene in enumerate(hero_scenes):
                icon = scene_icons[idx] if idx < len(scene_icons) else "🎬"
                color = scene_colors[idx] if idx < len(scene_colors) else "#0068FF"
                scene_cards_html += f"""
                <div style="flex:1;min-width:200px;background:#0D1117;border:1px solid #1E293B;
                    border-top:3px solid {color};border-radius:10px;padding:16px;">
                    <div style="font-size:24px;margin-bottom:8px;">{icon}</div>
                    <div style="color:#E2E8F0;font-weight:700;font-size:14px;margin-bottom:4px;">
                        Scene {scene.get('scene',idx+1)} &middot; {scene.get('duration','')}</div>
                    <div style="color:#CBD5E1;font-size:13px;line-height:1.5;margin-bottom:10px;">
                        {scene.get('description','')}</div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;">
                        <span style="background:#1E293B;color:#94A3B8;padding:3px 8px;border-radius:12px;font-size:11px;">
                            📷 {scene.get('camera','')}</span>
                        <span style="background:#1E293B;color:#94A3B8;padding:3px 8px;border-radius:12px;font-size:11px;">
                            🎭 {scene.get('mood','')}</span>
                    </div>
                </div>"""
            scene_cards_html += '</div>'
            components.html(scene_cards_html, height=220)

        if assets.get("video_message"):
            st.info(assets["video_message"])

        with st.expander("📋 Video Prompt (copy to RunwayML / Veo / Sora)"):
            st.code(assets.get("video_prompt", ""), language=None)

        st.divider()

        # ROW 2: Design System (colour palette + tone + guidelines)
        st.markdown("#### 🎨 Brand Design System")

        ds_left, ds_right = st.columns([1, 1])

        with ds_left:
            if palette:
                palette_html = '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px;">'
                for colour in palette:
                    palette_html += f"""
                    <div style="text-align:center;">
                        <div style="width:60px;height:60px;background:{colour.get('hex','#333')};
                            border-radius:10px;border:2px solid #1E293B;margin-bottom:4px;"></div>
                        <div style="color:#E2E8F0;font-size:11px;font-weight:600;">{colour.get('name','')}</div>
                        <div style="color:#64748B;font-size:10px;">{colour.get('hex','')}</div>
                    </div>"""
                palette_html += '</div>'
                components.html(palette_html, height=110)

            tones = ds.get("tone", [])
            if tones:
                tone_html = "".join([
                    f"<span style='background:#1E293B;color:#00D4AA;padding:4px 10px;border-radius:20px;margin:3px;font-size:12px;font-weight:600;display:inline-block;'>{t}</span>"
                    for t in tones
                ])
                components.html(f"<div style='margin-top:8px;'>{tone_html}</div>", height=40)

        with ds_right:
            d1, d2 = st.columns(2)
            with d1:
                st.markdown("**Do**")
                for d in ds.get("do", []):
                    st.markdown(f"- {d}")
            with d2:
                st.markdown("**Don't**")
                for d in ds.get("dont", []):
                    st.markdown(f"- {d}")

        st.divider()

        # ROW 3: Key Visuals / Posters
        st.markdown("#### 🖼️ Key Visuals / Campaign Posters")

        if posters and any(p for p in posters):
            img_cols = st.columns(3)
            labels = ["Hero Shot", "Lifestyle", "Product Close-Up"]
            for i in range(min(3, len(posters))):
                with img_cols[i]:
                    if posters[i]:
                        img_bytes = base64.b64decode(posters[i])
                        st.image(img_bytes, caption=labels[i], use_column_width=True)
        else:
            poster_prompt_text = assets.get("poster_prompt", "No prompt generated")
            components.html(f"""
            <div style="background:#0D1117;border:1px solid #1E293B;border-radius:12px;padding:24px;margin-bottom:12px;">
                <div style="display:flex;gap:16px;margin-bottom:16px;">
                    <div style="flex:1;background:#1E293B;height:180px;border-radius:8px;display:flex;flex-direction:column;align-items:center;justify-content:center;">
                        <div style="font-size:40px;margin-bottom:8px;">🖼️</div>
                        <div style="color:#64748B;font-size:12px;">Hero Shot</div>
                    </div>
                    <div style="flex:1;background:#1E293B;height:180px;border-radius:8px;display:flex;flex-direction:column;align-items:center;justify-content:center;">
                        <div style="font-size:40px;margin-bottom:8px;">🖼️</div>
                        <div style="color:#64748B;font-size:12px;">Lifestyle</div>
                    </div>
                    <div style="flex:1;background:#1E293B;height:180px;border-radius:8px;display:flex;flex-direction:column;align-items:center;justify-content:center;">
                        <div style="font-size:40px;margin-bottom:8px;">🖼️</div>
                        <div style="color:#64748B;font-size:12px;">Product Close-Up</div>
                    </div>
                </div>
                <div style="background:#111827;border-radius:8px;padding:12px;">
                    <div style="color:#0068FF;font-size:11px;font-weight:700;letter-spacing:1px;margin-bottom:6px;">INTELLIGENCE-ENRICHED POSTER PROMPT (copy to aistudio.google.com)</div>
                    <div style="color:#94A3B8;font-size:12px;line-height:1.6;">{poster_prompt_text}</div>
                </div>
            </div>
            """, height=310)

            st.caption("Poster generation requires Gemini API access via External Access Integration (not available on trial accounts). Copy the prompt above into [Google AI Studio](https://aistudio.google.com) to generate images.")

        st.divider()

        # ROW 4: Audio Script
        st.markdown("#### 🎵 Audio / Voiceover Script")
        script_prompt = audio_script.get("prompt", "")
        if script_prompt:
            components.html(f"""
            <div style="background:#0D1117;border:1px solid #1E293B;border-radius:12px;padding:20px;">
                <div style="display:flex;gap:16px;margin-bottom:12px;">
                    <span style="background:#1E293B;color:#00D4AA;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">
                        Duration: {audio_script.get('duration','30s')}</span>
                    <span style="background:#1E293B;color:#0068FF;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">
                        Format: {audio_script.get('format','Digital Audio')}</span>
                </div>
                <div style="color:#CBD5E1;font-size:13px;line-height:1.7;">{script_prompt}</div>
                <div style="margin-top:12px;color:#64748B;font-size:11px;">
                    Use with ElevenLabs, Murf.ai, or your studio team to produce the final voiceover.
                </div>
            </div>
            """, height=160)

        st.divider()

        # Download all assets as ZIP
        zip_bytes = build_assets_zip(assets)
        zip_b64 = base64.b64encode(zip_bytes).decode()
        safe_prod = cs_product.replace(" ", "_").replace("/", "_")
        components.html(f"""
        <button onclick="var a=document.createElement('a');a.href='data:application/zip;base64,{zip_b64}';a.download='{cs_client}_{safe_prod}_creative_assets.zip';document.body.appendChild(a);a.click();document.body.removeChild(a);"
            style="background:linear-gradient(135deg,#0068FF,#0052CC);color:white;border:none;padding:12px 24px;border-radius:8px;cursor:pointer;font-size:14px;font-weight:600;width:100%;letter-spacing:0.3px;"
            onmouseover="this.style.opacity='0.85'" onmouseout="this.style.opacity='1'">
            ⬇️ Download All Creative Assets (.zip)
        </button>
        """, height=60)

        # Snowflake vision note
        components.html("""
        <div style="background:#0D1117;border:1px solid #1E293B;border-left:4px solid #0068FF;border-radius:12px;padding:24px;margin-top:20px;">
            <div style="color:#E2E8F0;font-size:15px;font-weight:700;margin-bottom:8px;">🔮 Our Recommendation to Snowflake</div>
            <div style="color:#94A3B8;font-size:13px;line-height:1.7;">
                This feature required external Gemini APIs for image and video generation. Every other part of NovaSpark Co-Pilot runs natively on Snowflake Cortex.
                We recommend Snowflake build <strong style="color:#0068FF;">Cortex Image</strong> (powered by Imagen) and <strong style="color:#0068FF;">Cortex Video</strong> (powered by Veo)
                to make the complete creative workflow 100% Snowflake-native — from raw campaign data to client-ready visual assets, without leaving the platform.
            </div>
        </div>
        """, height=140)


# ============================
# TAB 5: Event Intelligence
# ============================
with tab5:
    st.subheader("Live Event Intelligence & Strategy")
    st.caption("Pull real-time market intelligence for major events and generate data-driven campaign strategies.")

    # -- Stage 1: Input Panel --
    ei_col1, ei_col2 = st.columns([2, 1])

    with ei_col1:
        event_options = [
            "Super Bowl 2025", "Black Friday 2025", "Holiday Season 2025",
            "Back to School 2025", "Valentine's Day 2026", "Summer Olympics 2028",
            "New Year Campaign 2026", "Spring Launch 2025"
        ]
        selected_event = st.selectbox("Select Market Event", event_options, key="ei_event")

        ei_keywords = st.text_input(
            "Event Keywords (comma-separated)",
            value=f"{selected_event}, marketing, advertising, campaign",
            key="ei_keywords"
        )

        competitors_input = st.text_input(
            "Competitors (comma-separated)",
            value="Nike, Adidas, Apple, Samsung",
            key="ei_comp_input"
        )

        markets_input = st.text_input(
            "Target Markets (comma-separated)",
            value="US, UK, India",
            key="ei_markets_input"
        )

        ei_budget = st.number_input(
            "Event Budget (USD)", min_value=50000, max_value=50000000,
            value=500000, step=50000, format="%d", key="ei_budget"
        )

        ei_objective = st.selectbox("Event Objective", [
            "Maximize Brand Visibility", "Drive Event-Day Sales",
            "Capture Market Share", "Build Community Engagement"
        ], key="ei_objective")

    with ei_col2:
        st.info(
            "**How It Works**\n\n"
            "1. **Research Phase** -- The Internet Intelligence Agent pulls Google Trends, "
            "news articles, and web intelligence for your event and competitors.\n\n"
            "2. **Analysis Phase** -- Data is loaded into Snowflake dynamic tables for "
            "real-time analytics: trend patterns, news sentiment, competitor presence.\n\n"
            "3. **Strategy Phase** -- The Strategy Synthesis Agent combines internal campaign "
            "data with live market intelligence to produce a complete event strategy."
        )

    run_intel = st.button("🚀 Run Event Intelligence", type="primary", use_container_width=True, key="ei_run_btn")

    # -- Stage 2: Research & Intelligence Display --
    if run_intel:
        competitors_list = [c.strip() for c in competitors_input.split(",") if c.strip()]
        markets_list = [m.strip() for m in markets_input.split(",") if m.strip()]
        keywords_list = [k.strip() for k in ei_keywords.split(",") if k.strip()]

        st.divider()
        st.markdown("### 🔍 Research Phase")

        progress = st.progress(0, text="Starting intelligence research...")

        # Step 1: Call Internet Intelligence Agent with auto-continue
        progress.progress(10, text="Calling Internet Intelligence Agent...")
        try:
            intel_prompt = (
                f"Research the market event '{selected_event}' for client {selected_client}. "
                f"Keywords: {', '.join(keywords_list)}. "
                f"Competitors: {', '.join(competitors_list)}. "
                f"Target markets: {', '.join(markets_list)}. "
                f"Gather Google Trends data, recent news articles, and web intelligence about "
                f"competitive positioning and market opportunities for this event."
            )
            intel_response = call_agent_with_auto_continue(
                'MARKETING_COPILOT.SEMANTIC.INTERNET_INTELLIGENCE_AGENT',
                intel_prompt,
                lambda n: (
                    f"Continue your research on '{selected_event}' for {selected_client}. "
                    f"Pick up where you left off. Do not repeat sections. Continuation #{n}."
                )
            )
        except Exception as e:
            intel_response = f"Error calling agent: {str(e)}"

        st.session_state["ei_intel_response"] = intel_response
        progress.progress(40, text="Intelligence research complete. Loading analytics...")

        # Step 2: Query existing event intelligence data from Snowflake
        progress.progress(50, text="Fetching trend data...")

        try:
            trends_df = run_query(f"""
                SELECT keyword, trend_date, interest_score, is_peak_date, data_source
                FROM MARKETING_COPILOT.ANALYTICS.DIM_EVENT_TRENDS
                WHERE UPPER(event_name) LIKE '%{selected_event.upper().replace("'", "''")}%'
                ORDER BY trend_date DESC
                LIMIT 200
            """)
        except Exception:
            trends_df = pd.DataFrame()

        progress.progress(60, text="Fetching news sentiment...")

        try:
            news_df = run_query(f"""
                SELECT title, source, sentiment_label, sentiment_score,
                       published_date, relevance_score
                FROM MARKETING_COPILOT.ANALYTICS.DIM_NEWS_SENTIMENT
                WHERE UPPER(event_name) LIKE '%{selected_event.upper().replace("'", "''")}%'
                ORDER BY published_date DESC
                LIMIT 50
            """)
        except Exception:
            news_df = pd.DataFrame()

        progress.progress(70, text="Fetching competitor presence...")

        try:
            competitor_df = run_query(f"""
                SELECT competitor_name, mention_count, sentiment_avg,
                       market_share_indicator, threat_level
                FROM MARKETING_COPILOT.ANALYTICS.DIM_COMPETITOR_PRESENCE
                WHERE UPPER(event_name) LIKE '%{selected_event.upper().replace("'", "''")}%'
                ORDER BY mention_count DESC
                LIMIT 20
            """)
        except Exception:
            competitor_df = pd.DataFrame()

        progress.progress(80, text="Building intelligence dashboard...")

        st.session_state["ei_trends_data"] = trends_df
        st.session_state["ei_news_data"] = news_df
        st.session_state["ei_comp_data"] = competitor_df

        progress.progress(100, text="Research complete!")

    # -- Display cached intelligence results --
    if "ei_intel_response" in st.session_state:
        st.divider()

        # Agent response — use st.markdown directly to avoid nested expanders
        with st.expander("🤖 Intelligence Agent Findings", expanded=True):
            clean = parse_agent_response(st.session_state["ei_intel_response"])
            st.markdown(clean)

        # Trends visualization
        trends_df = st.session_state.get("ei_trends_data", pd.DataFrame())
        if not trends_df.empty:
            with st.expander("📈 Google Trends Analysis", expanded=True):
                fig_trends = px.line(
                    trends_df, x="TREND_DATE", y="INTEREST_SCORE",
                    color="KEYWORD" if "KEYWORD" in trends_df.columns else None,
                    color_discrete_sequence=COLORS,
                    template=PLOTLY_TEMPLATE
                )
                fig_trends.update_layout(
                    xaxis_title="Date", yaxis_title="Interest Score",
                    height=350, margin=dict(t=20, b=40)
                )
                st.plotly_chart(fig_trends, use_container_width=True)

                if "IS_PEAK_DATE" in trends_df.columns:
                    peak_rows = trends_df[trends_df["IS_PEAK_DATE"] == True]
                    if not peak_rows.empty:
                        st.success(f"📈 **Peak interest detected on:** {', '.join(peak_rows['TREND_DATE'].astype(str).unique()[:3])}")

        # News sentiment
        news_df = st.session_state.get("ei_news_data", pd.DataFrame())
        if not news_df.empty:
            with st.expander("📰 News Sentiment Overview", expanded=True):
                sent_cols = st.columns(3)
                if "SENTIMENT_LABEL" in news_df.columns:
                    pos_count = len(news_df[news_df["SENTIMENT_LABEL"] == "positive"])
                    neg_count = len(news_df[news_df["SENTIMENT_LABEL"] == "negative"])
                    neu_count = len(news_df) - pos_count - neg_count
                else:
                    pos_count = neg_count = neu_count = 0
                sent_cols[0].metric("🟢 Positive", pos_count)
                sent_cols[1].metric("⚪ Neutral", neu_count)
                sent_cols[2].metric("🔴 Negative", neg_count)

                if "SENTIMENT_LABEL" in news_df.columns:
                    sent_fig = px.pie(
                        news_df["SENTIMENT_LABEL"].value_counts().reset_index(),
                        values="count", names="SENTIMENT_LABEL",
                        color_discrete_sequence=[SECONDARY, "#94A3B8", ACCENT],
                        template=PLOTLY_TEMPLATE
                    )
                    sent_fig.update_layout(height=300, margin=dict(t=20, b=20))
                    st.plotly_chart(sent_fig, use_container_width=True)

                display_cols = [c for c in ["TITLE", "SOURCE", "SENTIMENT_LABEL", "PUBLISHED_DATE"] if c in news_df.columns]
                if display_cols:
                    st.dataframe(news_df[display_cols].head(15), use_container_width=True, hide_index=True)

        # Competitor presence
        competitor_df = st.session_state.get("ei_comp_data", pd.DataFrame())
        if not competitor_df.empty:
            with st.expander("🏢 Competitor Landscape", expanded=True):
                fig_comp = px.bar(
                    competitor_df, x="COMPETITOR_NAME", y="MENTION_COUNT",
                    color="THREAT_LEVEL" if "THREAT_LEVEL" in competitor_df.columns else None,
                    color_discrete_sequence=COLORS,
                    template=PLOTLY_TEMPLATE
                )
                fig_comp.update_layout(
                    xaxis_title="Competitor", yaxis_title="Mentions",
                    height=350, margin=dict(t=20, b=40)
                )
                st.plotly_chart(fig_comp, use_container_width=True)

        # -- Stage 3: Strategy Output --
        st.divider()
        st.markdown("### 🧠 Strategy Synthesis")

        if "ei_strategy" not in st.session_state:
            if st.button("🧠 Generate Event Strategy", type="primary", key="ei_strategy_btn"):
                with st.spinner("Strategy Synthesis Agent is building your event strategy (auto-continues if needed)..."):
                    try:
                        strategy_prompt = (
                            f"Create a comprehensive event marketing strategy for {selected_client} "
                            f"targeting the '{selected_event}' event. "
                            f"Budget: ${ei_budget:,}. Objective: {ei_objective}. "
                            f"Competitors: {competitors_input}. Markets: {markets_input}. "
                            f"Include: 1) Channel allocation with percentages, "
                            f"2) Creative direction and messaging themes, "
                            f"3) Timeline with key milestones, "
                            f"4) Expected impact metrics (reach, engagement, conversions), "
                            f"5) Competitive positioning strategy. "
                            f"Use ## markdown headers for each section. "
                            f"Base recommendations on both historical campaign performance data "
                            f"and current market intelligence."
                        )
                        strategy = call_agent_with_auto_continue(
                            'MARKETING_COPILOT.SEMANTIC.STRATEGY_SYNTHESIS_AGENT',
                            strategy_prompt,
                            lambda n: (
                                f"Continue the event strategy you were writing for {selected_client} "
                                f"and '{selected_event}'. Pick up where you left off. "
                                f"Do not repeat. Continuation #{n}."
                            )
                        )
                    except Exception as e:
                        strategy = f"Error calling agent: {str(e)}"
                    st.session_state["ei_strategy"] = strategy
                    st.experimental_rerun()
        else:
            strategy = st.session_state["ei_strategy"]

            st.markdown(f"**Event:** {selected_event} | **Client:** {selected_client} | **Budget:** ${ei_budget:,} | **Date:** {TODAY}")
            st.divider()

            if response_is_incomplete(strategy):
                st.warning("The strategy may still be incomplete after auto-continuation attempts.")

            render_agent_markdown(strategy)

            st.divider()

            # Download strategy
            safe_client = selected_client.replace(" ", "_")
            safe_event = selected_event.replace(" ", "_").replace("/", "_")
            strategy_html = build_html_document(
                title="Event Campaign Strategy",
                subtitle=f"{selected_event} — {selected_client}",
                metadata={"Client": selected_client, "Event": selected_event,
                          "Budget": f"${ei_budget:,}", "Markets": markets_input, "Date": TODAY},
                content=parse_agent_response(strategy)
            )

            dl_col, reset_col = st.columns([1, 4])
            with dl_col:
                js_download_button(
                    content=strategy_html,
                    filename=f"{safe_client}_{safe_event}_strategy.html",
                    label="⬇️ Download Event Strategy"
                )
            with reset_col:
                if st.button("🔄 New Research", key="ei_reset"):
                    for key in ["ei_intel_response", "ei_trends_data", "ei_news_data",
                                "ei_comp_data", "ei_strategy"]:
                        st.session_state.pop(key, None)
                    st.experimental_rerun()
