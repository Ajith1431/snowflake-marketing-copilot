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


def show_df(df):
    # SiS warehouse runtime ships an older Streamlit without st.dataframe(hide_index=)
    try:
        st.dataframe(df, use_container_width=True, hide_index=True)
    except TypeError:
        st.dataframe(df.reset_index(drop=True), use_container_width=True)


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


# -- Creative intelligence + predictor (MARKETING_COPILOT.CREATIVE, synthetic data) --
CI_BANNER = "Illustrative synthetic data. Brand names are labels only. Outputs are scenario estimates, not real forecasts."
CI_BRANDS = ["Nike", "Pepsi", "Samsung"]
CI_MARKETS = ["UAE", "KSA", "UK", "US", "IN"]
CI_OBJECTIVES = ["AWARENESS", "LINK_CLICKS", "LEADS"]
CI_PLACEMENTS = ["feed", "reels", "stories"]
CI_FAMILIES = {
    "hook_type": ["product_led", "promo_led", "person_on_camera", "ugc_style"],
    "headline_tone": ["informational", "conversational", "urgent", "playful"],
    "cta_tone": ["transactional", "informational"],
    "background": ["studio", "home", "outdoor", "retail"],
    "color_temp": ["warm", "cool", "neutral"],
    "has_person": ["Y", "N"],
    "word_count_group": ["0-5", "6-10", "11+"],
    "has_logo_first_3s": ["N", "Y"],
}
CI_CLASS_COLORS = {"NET_HELPED": "#22C55E", "NET_HURT": "#EF4444", "NEGLIGIBLE": "#94A3B8",
                   "MIXED": "#F59E0B", "INCONCLUSIVE": "#475569"}


@st.cache_data(ttl=300)
def load_net_lean(stratum_type, market, objective, brand_label):
    return run_query(f"""
        SELECT * FROM MARKETING_COPILOT.CREATIVE.NET_LEAN
        WHERE stratum_type = '{stratum_type}' AND market = '{market}'
          AND objective = '{objective}' AND brand = '{brand_label}'
    """)


@st.cache_data(ttl=300)
def load_net_lean_takeaway(stratum_type, market, objective, brand_label):
    return run_query(f"""
        SELECT * FROM MARKETING_COPILOT.CREATIVE.NET_LEAN_TAKEAWAY
        WHERE stratum_type = '{stratum_type}' AND market = '{market}'
          AND objective = '{objective}' AND brand = '{brand_label}'
    """)


@st.cache_data(ttl=300)
def load_best_attributes(brand_label, market):
    """NET_HELPED values (vs their reference) for brand x market; falls back to the brand across all markets."""
    for scope in (market, "ALL"):
        df = run_query(f"""
            SELECT attribute_family, attribute_value, reference_value, adj_lift_pct FROM MARKETING_COPILOT.CREATIVE.NET_LEAN
            WHERE stratum_type = 'MARKET_X_BRAND' AND market = '{scope}' AND brand = '{brand_label}'
              AND net_lean_class = 'NET_HELPED'
            ORDER BY adj_lift_pct DESC LIMIT 3
        """)
        if not df.empty:
            return [f"{r.ATTRIBUTE_FAMILY.replace('_', ' ')} = {r.ATTRIBUTE_VALUE} (vs {r.REFERENCE_VALUE}, "
                    f"{float(r.ADJ_LIFT_PCT):+.0f}% CTR)" for r in df.itertuples()], scope
    return [], None


@st.cache_data(ttl=300)
def load_model_metrics():
    return run_query("SELECT * FROM MARKETING_COPILOT.CREATIVE.MODEL_METRICS ORDER BY level DESC, model")


@st.cache_data(ttl=300)
def load_null_effect_rate():
    try:
        df = run_query("SELECT n_strata_tested, n_false_positive, false_positive_share "
                       "FROM MARKETING_COPILOT.CREATIVE.NULL_EFFECT_CHECK WHERE attribute_family = 'ALL'")
    except Exception:
        return None
    return None if df.empty else df.iloc[0]


@st.cache_data(ttl=300)
def load_model_effect_check():
    try:
        return run_query("SELECT * FROM MARKETING_COPILOT.CREATIVE.MODEL_EFFECT_CHECK")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_feature_effects():
    return run_query("SELECT * FROM MARKETING_COPILOT.CREATIVE.FEATURE_EFFECTS ORDER BY model, rank")


@st.cache_data(ttl=300)
def score_ad(payload_json):
    res = session.sql(
        f"CALL MARKETING_COPILOT.CREATIVE.SCORE_AD(PARSE_JSON($${payload_json.replace('$$', '$ $')}$$))"
    ).collect()
    return json.loads(res[0][0])


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
st.title("📊 Marketing Co-Pilot")
st.caption(f"Sidebar client: {selected_client} (used by Client Intelligence, Campaign Recommendation, Generate Pitch, "
           f"Event Intelligence and Creative Studio). Predictor and Performance Drivers use the synthetic creative "
           f"dataset and their own brand pickers.")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Client Intelligence",
    "🎯 Campaign Recommendation",
    "🔮 Predictor",
    "📋 Generate Pitch",
    "🌍 Event Intelligence",
    "🎨 Creative Studio",
    "🧠 Performance Drivers"
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
# TAB 3: Predictor (scenario estimates from CREATIVE.SCORE_AD)
# ============================
with tab3:
    st.subheader("Creative Predictor: compare two creative scenarios")
    st.warning(f"⚠️ {CI_BANNER}")
    st.caption("Pick brand label, market, objective, placement, creative attributes and weekly budget for scenario A, "
               "then change any of them for scenario B. Each scenario is scored by CREATIVE.SCORE_AD "
               "(gradient boosting point estimate, conformal p10-p90 range).")

    def _scenario_inputs(prefix, base=None):
        base = base or {}
        out = {}

        def pick(label, key, options):
            default = base.get(key, options[0])
            return st.selectbox(label, options, index=options.index(default) if default in options else 0,
                                key=f"{prefix}_{key}_{base.get(key, '')}")

        c1, c2 = st.columns(2)
        with c1:
            out["brand"] = pick("Brand (label)", "brand", CI_BRANDS)
            out["objective"] = pick("Objective", "objective", CI_OBJECTIVES)
        with c2:
            out["market"] = pick("Market", "market", CI_MARKETS)
            out["placement"] = pick("Placement", "placement", CI_PLACEMENTS)
        attrs = {}
        a1, a2 = st.columns(2)
        for i, (fam, values) in enumerate(CI_FAMILIES.items()):
            with (a1 if i % 2 == 0 else a2):
                default = base.get("attributes", {}).get(fam, values[0])
                attrs[fam] = st.selectbox(fam.replace("_", " "), values,
                                          index=values.index(default) if default in values else 0,
                                          key=f"{prefix}_{fam}_{default}")
        out["attributes"] = attrs
        out["budget"] = st.number_input("Weekly budget (USD)", min_value=100, max_value=50000,
                                        value=int(base.get("budget", 2000)), step=100,
                                        key=f"{prefix}_budget_{base.get('budget', '')}")
        return out

    PRED_PRESETS = {
        "(a) Nike · UK · LINK_CLICKS: urgent headline vs conversational": (
            {"brand": "Nike", "market": "UK", "objective": "LINK_CLICKS", "placement": "feed", "budget": 2000,
             "attributes": {"headline_tone": "urgent"}},
            {"attributes": {"headline_tone": "conversational"}}),
        "(b) Creative-only bundle (placement held constant): Nike · UK · LINK_CLICKS · feed, "
        "urgent + product-led vs conversational + person on camera": (
            {"brand": "Nike", "market": "UK", "objective": "LINK_CLICKS", "placement": "feed", "budget": 2000,
             "attributes": {"headline_tone": "urgent", "hook_type": "product_led"}},
            {"attributes": {"headline_tone": "conversational", "hook_type": "person_on_camera"}}),
        "(c) Pepsi · UAE · AWARENESS: no logo in first 3s vs logo in first 3s": (
            {"brand": "Pepsi", "market": "UAE", "objective": "AWARENESS", "placement": "feed", "budget": 2000,
             "attributes": {"has_logo_first_3s": "N"}},
            {"attributes": {"has_logo_first_3s": "Y"}}),
        "(d) Placement + creative bundle: Nike · UK · LINK_CLICKS, stories + urgent + product-led "
        "vs feed + conversational + person on camera": (
            {"brand": "Nike", "market": "UK", "objective": "LINK_CLICKS", "placement": "stories", "budget": 2000,
             "attributes": {"headline_tone": "urgent", "hook_type": "product_led"}},
            {"placement": "feed", "attributes": {"headline_tone": "conversational", "hook_type": "person_on_camera"}}),
    }
    preset_names = list(PRED_PRESETS)
    preset = st.selectbox("Preset scenario pair (edit any field afterwards)", preset_names, index=1, key="pred_preset")
    preset_a, preset_b_changes = PRED_PRESETS[preset]
    if preset.startswith("(d)"):
        st.caption("Most of this lift comes from placement (stories → feed), not from the creative changes.")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### Scenario A")
        scen_a = _scenario_inputs("pa", preset_a)
    with col_b:
        st.markdown("### Scenario B")
        b_base = {**scen_a, **{k: v for k, v in preset_b_changes.items() if k != "attributes"},
                  "attributes": {**scen_a["attributes"], **preset_b_changes.get("attributes", {})}}
        st.caption("Starts as A with the preset's changes; change any field.")
        scen_b = _scenario_inputs("pb", b_base)

    if scen_a == scen_b:
        st.warning("Scenario B is identical to A. Change at least one field to compare.")

    if st.button("🔮 Score both scenarios", type="primary", key="pred_score_btn"):
        try:
            st.session_state["pred_results"] = (
                scen_a, scen_b,
                score_ad(json.dumps(scen_a, sort_keys=True)), score_ad(json.dumps(scen_b, sort_keys=True)))
        except Exception as exc:
            st.error(f"Scoring failed: {exc}")

    if "pred_results" in st.session_state:
        sa, sb, ra, rb = st.session_state["pred_results"]
        st.divider()
        lift = (rb["predicted_ctr"] / ra["predicted_ctr"] - 1) * 100 if ra["predicted_ctr"] else 0.0
        overlap = not (rb["p10"] > ra["p90"] or rb["p90"] < ra["p10"])
        lift_lo = (rb["p10"] / ra["p90"] - 1) * 100 if ra["p90"] else 0.0
        lift_hi = (rb["p90"] / ra["p10"] - 1) * 100 if ra["p10"] else 0.0
        changed = [k for k in ("brand", "market", "objective", "placement", "budget") if sa[k] != sb[k]] + \
                  [f for f in CI_FAMILIES if sa["attributes"][f] != sb["attributes"][f]]
        st.caption("Changed in B: " + (", ".join(changed) if changed else "nothing (B = A)"))
        m1, m2, m3 = st.columns(3)
        m1.metric("Scenario A: predicted CTR", f"{ra['predicted_ctr'] * 100:.2f}%",
                  help=f"p10-p90: {ra['p10'] * 100:.2f}% to {ra['p90'] * 100:.2f}%")
        m1.caption(f"p10-p90 range: {ra['p10'] * 100:.2f}% to {ra['p90'] * 100:.2f}%")
        m2.metric("Scenario B: predicted CTR", f"{rb['predicted_ctr'] * 100:.2f}%", delta=f"{lift:+.1f}% vs A")
        m2.caption(f"p10-p90 range: {rb['p10'] * 100:.2f}% to {rb['p90'] * 100:.2f}%")
        m3.metric("Lift of B vs A (point estimate)", f"{lift:+.1f}%")
        if abs(lift) < 5:
            st.warning(f"⚠️ Expected difference is only {lift:+.1f}% (A vs B): too small to distinguish from noise.")
        else:
            st.success(f"Expected difference: {lift:+.1f}% (A vs B).")

        # Swap decomposition: revert one changed field of B to A's value and re-score
        swaps = []
        for field in changed:
            reverted = {**sb, "attributes": dict(sb["attributes"])}
            if field in CI_FAMILIES:
                reverted["attributes"][field] = sa["attributes"][field]
                a_val, b_val = sa["attributes"][field], sb["attributes"][field]
            else:
                reverted[field] = sa[field]
                a_val, b_val = sa[field], sb[field]
            try:
                r_rev = score_ad(json.dumps(reverted, sort_keys=True))
            except Exception as exc:
                st.error(f"Scoring failed for swap {field}: {exc}")
                continue
            delta_pp = (rb["predicted_ctr"] - r_rev["predicted_ctr"]) * 100
            swaps.append({"Changed field": field.replace("_", " "), "A → B": f"{a_val} → {b_val}",
                          "B with only this reverted": f"{r_rev['predicted_ctr'] * 100:.2f}%",
                          "CTR change attributable (pp)": f"{delta_pp:+.2f}",
                          "As % of A's CTR": f"{delta_pp / (ra['predicted_ctr'] * 100) * 100:+.1f}%" if ra["predicted_ctr"] else ""})
        if swaps:
            st.markdown("**What each change contributes** (swap test: B scored with only that field set back to A)")
            show_df(pd.DataFrame(swaps))
            st.caption(f"Total change B vs A: {(rb['predicted_ctr'] - ra['predicted_ctr']) * 100:+.2f} pp. The swap "
                       "contributions need not add up to the total, because the gradient boosting model has "
                       "interactions between fields.")
        for name, r in [("A", ra), ("B", rb)]:
            if r.get("warnings"):
                st.caption(f"Notes for scenario {name}: " + "; ".join(r["warnings"]))

        with st.expander("Show range for individual ad-weeks", expanded=False):
            st.caption(f"Lift range: {lift_lo:+.1f}% to {lift_hi:+.1f}% (B's p10-p90 against A's p90-p10). It covers "
                       "individual ad-weeks, so it is intentionally wide; use the expected difference as the headline.")
            if overlap:
                st.caption("The individual ad-week ranges overlap, so any single ad can go either way.")
            else:
                st.caption("The individual ad-week ranges do not overlap.")
            fig_pred = go.Figure()
            for name, r, color in [("A", ra, PRIMARY), ("B", rb, ACCENT)]:
                fig_pred.add_trace(go.Scatter(
                    x=[r["predicted_ctr"] * 100], y=[f"Scenario {name}"], mode="markers", marker=dict(size=14, color=color),
                    error_x=dict(type="data", symmetric=False, array=[(r["p90"] - r["predicted_ctr"]) * 100],
                                 arrayminus=[(r["predicted_ctr"] - r["p10"]) * 100], color=color),
                    name=f"Scenario {name}"))
            fig_pred.update_layout(template=PLOTLY_TEMPLATE, height=220, margin=dict(t=20, b=40), showlegend=False,
                                   xaxis_title="Predicted CTR % (dot) with p10-p90 range")
            st.plotly_chart(fig_pred, use_container_width=True)
        st.caption(f"Scenario estimate. {ra['disclaimer']}")

        pred_report = (
            f"## Scenario A\n- Inputs: {json.dumps(sa)}\n- Predicted CTR: {ra['predicted_ctr'] * 100:.2f}% "
            f"(p10 {ra['p10'] * 100:.2f}%, p90 {ra['p90'] * 100:.2f}%)\n\n"
            f"## Scenario B\n- Inputs: {json.dumps(sb)}\n- Predicted CTR: {rb['predicted_ctr'] * 100:.2f}% "
            f"(p10 {rb['p10'] * 100:.2f}%, p90 {rb['p90'] * 100:.2f}%)\n\n"
            f"## Comparison\n- Lift of B vs A: {lift:+.1f}% (point estimate)\n"
            f"- {'Individual ad-week ranges overlap, so any single ad can go either way.' if overlap else 'Individual ad-week ranges do not overlap.'}\n\n"
            f"## Caveat\n{CI_BANNER}"
        )
        js_download_button(
            content=build_html_document(title="Creative Predictor: Scenario Estimate", subtitle="Scenario A vs B",
                                        metadata={"Data": "Synthetic", "Date": TODAY}, content=pred_report),
            filename="creative_predictor_scenarios.html", label="⬇️ Download Scenario Estimate")


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
        ci_c1, ci_c2 = st.columns(2)
        ci_brand = ci_c1.selectbox("Performance Drivers brand (label)", CI_BRANDS, key="cs_ci_brand")
        ci_market = ci_c2.selectbox("Performance Drivers market", CI_MARKETS, key="cs_ci_market")
        ci_best, ci_scope = load_best_attributes(ci_brand, ci_market)
        ci_where = ci_market if ci_scope == ci_market else "all markets (too few ads in " + ci_market + ")"
        st.caption(f"Net helpers for {ci_brand} in {ci_where} (synthetic creative data): {', '.join(ci_best)}"
                   if ci_best else f"No net-helped attributes for {ci_brand} (not enough evidence).")
        cs_direction = st.text_area(
            "Creative Direction",
            value=st.session_state.get("recommendation_creative", "Clean modern visuals with lifestyle imagery showing product in everyday premium context")
                  + (f" Lean into (adjusted CTR lift vs the stated reference value, synthetic data): {'; '.join(ci_best)}." if ci_best else ""),
            height=68, key=f"cs_direction_{ci_brand}_{ci_market}"
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
            "FIFA World Cup 2026", "Black Friday 2026",
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
                SELECT keyword, trend_date, interest_score, is_peak AS is_peak_date, confidence AS data_source
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
                SELECT title, source_name AS source, sentiment AS sentiment_label, sentiment_score,
                       published_at AS published_date, brand_name
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
                SELECT brand_name AS competitor_name, total_articles AS mention_count,
                       avg_sentiment_score AS sentiment_avg, media_presence
                FROM MARKETING_COPILOT.ANALYTICS.DIM_COMPETITOR_PRESENCE
                WHERE UPPER(event_name) LIKE '%{selected_event.upper().replace("'", "''")}%'
                  AND brand_name <> event_name
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

                display_cols = [c for c in ["TITLE", "BRAND_NAME", "SOURCE", "SENTIMENT_LABEL", "PUBLISHED_DATE"] if c in news_df.columns]
                if display_cols:
                    show_df(news_df[display_cols].head(15))

        # Competitor presence
        competitor_df = st.session_state.get("ei_comp_data", pd.DataFrame())
        if not competitor_df.empty:
            with st.expander("🏢 Competitor Landscape", expanded=True):
                fig_comp = px.bar(
                    competitor_df, x="COMPETITOR_NAME", y="MENTION_COUNT",
                    color="MEDIA_PRESENCE" if "MEDIA_PRESENCE" in competitor_df.columns else None,
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


# ============================
# TAB 7: Performance Drivers (CREATIVE.NET_LEAN + model card)
# ============================
with tab7:
    st.subheader("Performance Drivers: which creative attributes move CTR (synthetic creative dataset)")
    st.warning(f"⚠️ {CI_BANNER}")

    CI_CLASS_INFO = {
        "NET_HELPED": ("#22C55E", "net helped: lift > +3% and the 95% interval excludes 0"),
        "NET_HURT": ("#EF4444", "net hurt: lift < -3% and the 95% interval excludes 0"),
        "NEGLIGIBLE": ("#94A3B8", "negligible: the whole 95% interval is within ±3%"),
        "MIXED": ("#F59E0B", "mixed: the sign differs across brands"),
        "INCONCLUSIVE": ("#64748B", "inconclusive: interval too wide to call (includes 0, wider than ±3%)"),
        "INSUFFICIENT_DATA": ("#1E293B", "not enough data: fewer than 30 ads have this value"),
    }

    f1, f2, f3 = st.columns(3)
    pd_brand = f1.selectbox("Brand (label)", CI_BRANDS + ["ALL brands"], index=0, key="pdv_brand2")
    pd_market = f2.selectbox("Drill down: market", ["ALL"] + CI_MARKETS, key="pdv_market2")
    pd_objective = f3.selectbox("Drill down: objective", ["ALL"] + CI_OBJECTIVES, key="pdv_objective2")

    if pd_brand != "ALL brands" and pd_objective == "ALL":
        stype, s_mkt, s_obj, s_brand = "MARKET_X_BRAND", pd_market, "ALL", pd_brand
    else:
        stype, s_mkt, s_obj, s_brand = "MARKET_X_OBJECTIVE", pd_market, pd_objective, "ALL"
        if pd_brand != "ALL brands":
            st.info(f"Brand × objective cells are not computed (too few ads), so this view shows all brands for "
                    f"objective = {pd_objective}. Set objective to ALL to see {pd_brand} on its own.")

    nl = load_net_lean(stype, s_mkt, s_obj, s_brand)
    tk = load_net_lean_takeaway(stype, s_mkt, s_obj, s_brand)
    if nl.empty:
        st.info("No NET_LEAN results for this selection. Run scripts/deploy_creative_ml.py to compute them.")
    else:
        n_ads = int(nl["N_ADS"].iloc[0])
        st.caption(f"Stratum: {nl['STRATUM'].iloc[0]}  ·  {n_ads} ads  ·  adjusted CTR lift controls for log spend, "
                   f"brand, placement, market, objective (when not fixed by the filter) and the other attribute families; 95% bootstrap interval over ads.")
        if n_ads < 60:
            st.info(f"Only {n_ads} ads in this cell, so most values will show 'not enough data'. "
                    f"Widen the drill-down (set market or objective to ALL) for more evidence.")
        if not tk.empty:
            st.markdown(f"**Takeaway:** {tk['TAKEAWAY'].iloc[0]}")

        nl = nl.copy()
        nl["LABEL"] = (nl["ATTRIBUTE_FAMILY"].str.replace("_", " ") + ": " + nl["ATTRIBUTE_VALUE"]
                       + " vs " + nl["REFERENCE_VALUE"])
        enough = nl[nl["NET_LEAN_CLASS"] != "INSUFFICIENT_DATA"].copy()
        thin = nl[nl["NET_LEAN_CLASS"] == "INSUFFICIENT_DATA"]

        helped = enough[enough["NET_LEAN_CLASS"] == "NET_HELPED"].sort_values("ADJ_LIFT_PCT", ascending=False)
        hurt = enough[enough["NET_LEAN_CLASS"] == "NET_HURT"].sort_values("ADJ_LIFT_PCT")
        b1, b2 = st.columns(2)
        with b1:
            if helped.empty:
                st.info("**Best attribute:** none clears the evidence bar here.")
            else:
                h = helped.iloc[0]
                st.success(f"**Best attribute:** {h['LABEL']}\n\n{h['ADJ_LIFT_PCT']:+.1f}% adjusted CTR "
                           f"(95% CI {h['CI_LOW_PCT']:+.1f}% to {h['CI_HIGH_PCT']:+.1f}%, {int(h['N_ADS_WITH'])} ads)")
        with b2:
            if hurt.empty:
                st.info("**Worst attribute:** none clears the evidence bar here.")
            else:
                h = hurt.iloc[0]
                st.error(f"**Worst attribute:** {h['LABEL']}\n\n{h['ADJ_LIFT_PCT']:+.1f}% adjusted CTR "
                         f"(95% CI {h['CI_LOW_PCT']:+.1f}% to {h['CI_HIGH_PCT']:+.1f}%, {int(h['N_ADS_WITH'])} ads)")

        st.markdown("#### Net lean by attribute family")
        st.markdown(" ".join(
            f"<span style='display:inline-block;margin:2px 10px 2px 0;font-size:12px;'>"
            f"<span style='display:inline-block;width:11px;height:11px;background:{c};border:1px solid #475569;"
            f"margin-right:5px;vertical-align:middle;'></span>{d}</span>"
            for c, d in CI_CLASS_INFO.values()), unsafe_allow_html=True)
        st.caption("Lifts are versus the stated reference value. With about 1,000 cells, roughly 1 in 20 cells with "
                   "no real effect will still be flagged; treat single borderline cells as hypotheses.")

        if enough.empty:
            st.info("Every attribute value in this stratum has fewer than 30 ads: not enough data.")
        else:
            for c in ("ADJ_LIFT_PCT", "CI_LOW_PCT", "CI_HIGH_PCT"):
                enough[c] = pd.to_numeric(enough[c], errors="coerce").astype(float)
            fam_order = {f: i for i, f in enumerate(CI_FAMILIES)}
            enough["FAM_ORDER"] = enough["ATTRIBUTE_FAMILY"].map(fam_order)
            # plotly draws horizontal bars bottom-up: reverse so the first family is on top, highest lift first
            enough = enough.sort_values(["FAM_ORDER", "ADJ_LIFT_PCT"], ascending=[False, True])
            enough["YLABEL"] = [f"{r.LABEL} (n={int(r.N_ADS_WITH)})" for r in enough.itertuples()]
            x_max = float(max(enough["CI_HIGH_PCT"].abs().max(), enough["CI_LOW_PCT"].abs().max(),
                              enough["ADJ_LIFT_PCT"].abs().max(), 5.0)) * 1.15
            fig_nl = go.Figure(go.Bar(
                x=enough["ADJ_LIFT_PCT"].tolist(), y=enough["YLABEL"].tolist(), orientation="h", base=0,
                marker_color=[CI_CLASS_INFO.get(c, ("#64748B", ""))[0] for c in enough["NET_LEAN_CLASS"]],
                error_x=dict(type="data", symmetric=False,
                             array=(enough["CI_HIGH_PCT"] - enough["ADJ_LIFT_PCT"]).fillna(0).tolist(),
                             arrayminus=(enough["ADJ_LIFT_PCT"] - enough["CI_LOW_PCT"]).fillna(0).tolist(),
                             color="#CBD5E1", thickness=1.5, width=4),
                text=[f"{v:+.1f}%" for v in enough["ADJ_LIFT_PCT"]], textposition="none",
                customdata=[[r.LABEL, CI_CLASS_INFO.get(r.NET_LEAN_CLASS, ("", r.NET_LEAN_CLASS))[1],
                             int(r.N_ADS_WITH), r.CI_LOW_PCT, r.CI_HIGH_PCT] for r in enough.itertuples()],
                hovertemplate="%{customdata[0]}<br>adjusted lift %{x:+.1f}%<br>95% CI %{customdata[3]:+.1f}% to "
                              "%{customdata[4]:+.1f}%<br>%{customdata[2]} ads<br>%{customdata[1]}<extra></extra>"))
            fig_nl.add_vline(x=0, line_color="#64748B")
            fig_nl.update_layout(template=PLOTLY_TEMPLATE, height=max(320, 28 * len(enough) + 80),
                                 margin=dict(t=20, b=40, l=10, r=40),
                                 xaxis=dict(type="linear", range=[-x_max, x_max], zeroline=True, ticksuffix="%",
                                            title="Adjusted CTR lift % (bar) with 95% interval (whisker); left = hurts, right = helps"),
                                 yaxis=dict(type="category", categoryorder="array", categoryarray=enough["YLABEL"].tolist()))
            st.plotly_chart(fig_nl, use_container_width=True)

            fam_rows = []
            for fam_name in CI_FAMILIES:
                g = enough[enough["ATTRIBUTE_FAMILY"] == fam_name]
                if g.empty:
                    fam_rows.append({"Family": fam_name, "Reference": "", "Strongest helper": "not enough data", "Strongest hurter": ""})
                    continue
                top, low = g.loc[g["ADJ_LIFT_PCT"].idxmax()], g.loc[g["ADJ_LIFT_PCT"].idxmin()]
                fam_rows.append({
                    "Family": fam_name, "Reference": top["REFERENCE_VALUE"],
                    "Strongest helper": f"{top['ATTRIBUTE_VALUE']} ({top['ADJ_LIFT_PCT']:+.1f}%, {top['NET_LEAN_CLASS']}, n={int(top['N_ADS_WITH'])})",
                    "Strongest hurter": f"{low['ATTRIBUTE_VALUE']} ({low['ADJ_LIFT_PCT']:+.1f}%, {low['NET_LEAN_CLASS']}, n={int(low['N_ADS_WITH'])})"})
            show_df(pd.DataFrame(fam_rows))
        if not thin.empty:
            st.caption("Not enough data (< 30 ads with the value): "
                       + ", ".join(f"{l} (n={int(n)})" for l, n in zip(thin["LABEL"], thin["N_ADS_WITH"])))

        st.markdown("#### Sub-attribute breakdown by family")
        fam = st.selectbox("Attribute family", list(CI_FAMILIES), key="pdv_family")
        fam_df = nl[nl["ATTRIBUTE_FAMILY"] == fam].sort_values("ADJ_LIFT_PCT", ascending=False, na_position="last")
        sub_rows = [{
            "Value": r.ATTRIBUTE_VALUE, "Reference": r.REFERENCE_VALUE,
            "Adjusted lift": "not enough data" if r.NET_LEAN_CLASS == "INSUFFICIENT_DATA" else f"{r.ADJ_LIFT_PCT:+.1f}%",
            "95% interval": "" if r.NET_LEAN_CLASS == "INSUFFICIENT_DATA" else f"{r.CI_LOW_PCT:+.1f}% to {r.CI_HIGH_PCT:+.1f}%",
            "Ads with": int(r.N_ADS_WITH), "Ads with reference": int(r.N_ADS_REFERENCE),
            "Class": "not enough data" if r.NET_LEAN_CLASS == "INSUFFICIENT_DATA" else r.NET_LEAN_CLASS,
            "Brand-level lifts": "" if r.BRAND_LIFTS_JSON in (None, "{}") else r.BRAND_LIFTS_JSON,
        } for r in fam_df.itertuples()]
        sub_df = pd.DataFrame(sub_rows)
        if pd_brand != "ALL brands" and "Brand-level lifts" in sub_df:
            sub_df = sub_df.drop(columns=["Brand-level lifts"])
        show_df(sub_df)

    with st.expander("📇 Model card: CTR predictor", expanded=False):
        mm = load_model_metrics()
        fe = load_feature_effects()
        if mm.empty:
            st.info("Model not trained yet. Run scripts/deploy_creative_ml.py.")
        else:
            m0 = mm.iloc[0]
            st.markdown(
                f"- **Point model:** {m0['CHOSEN_POINT_MODEL']} (HistGradientBoostingRegressor on log-odds CTR); "
                f"Ridge and a brand × placement historical-mean baseline are kept for comparison.\n"
                f"- **Interval model:** HistGradientBoosting quantile regressors (p10, p90), conformally widened using "
                f"the last 8 training weeks (from {m0['CALIBRATION_START']}).\n"
                f"- **Features:** brand, market, objective, placement, ad type, aspect ratio, platform, the 8 creative "
                f"attribute families, log weekly spend, frequency (and excess over 6), weeks since start.\n"
                f"- **Training period:** {m0['TRAIN_START']} to {m0['TRAIN_END']} ({int(m0['N_TRAIN_ROWS'])} ad-weeks).\n"
                f"- **Holdout period:** {m0['HOLDOUT_START']} to {m0['HOLDOUT_END']} ({int(m0['N_HOLDOUT_ROWS'])} ad-weeks, "
                f"last 10 weeks, never used for training or calibration).")
            show = mm[["MODEL", "LEVEL", "N_HOLDOUT", "MAE_CTR_PP", "MAPE_PCT", "R2", "MSE_SKILL_VS_BASELINE",
                       "P10_P90_COVERAGE"]].rename(columns={
                "MAE_CTR_PP": "MAE (CTR pp)", "MAPE_PCT": "MAPE %", "MSE_SKILL_VS_BASELINE": "Skill vs baseline",
                "P10_P90_COVERAGE": "p10-p90 coverage"})
            show_df(show)
            st.caption("Ad level = holdout weeks aggregated per ad before scoring. Coverage target is ~80%. "
                       "Gradient boosting beats Ridge only modestly (ad-week R² gap ~0.04); most of the signal is "
                       "captured by a linear model, and the remaining edge plausibly comes from brand-specific interactions.")
            if not fe.empty:
                top = fe[fe["RANK"] <= 8].copy()
                fig_fe = px.bar(top, x="IMPORTANCE_R2_DROP", y="FEATURE", color="MODEL", barmode="group",
                                orientation="h", template=PLOTLY_TEMPLATE, color_discrete_sequence=[PRIMARY, ACCENT])
                fig_fe.update_layout(height=420, margin=dict(t=20, b=40), yaxis=dict(categoryorder="total ascending"),
                                     xaxis_title="Permutation importance (drop in holdout R² on log-odds CTR)")
                st.plotly_chart(fig_fe, use_container_width=True)
            st.markdown(
                "**Known limitations**\n"
                "- Synthetic data with planted effects; brand names are labels only. Not a forecast of real campaigns.\n"
                "- Small samples: ~40 ads per market × objective cell; many attribute values have < 30 ads and are "
                "reported as not enough data.\n"
                "- Wide intervals on small cells; the Predictor's p10-p90 is calibrated overall, not per cell.\n"
                "- The Predictor's per-change contributions are swap tests on the gradient boosting model (re-score B "
                "with one field reverted), so they include interactions and need not sum to the total.\n"
                "- Frequency is estimated from budget when not supplied, so budget changes also move frequency.\n"
                "- No multiple-comparison correction was applied across the ~1,000 net-lean cells; borderline results "
                "are hypotheses (for example IN shows one borderline NET_HURT where no effect was planted).")
            ne = load_null_effect_rate()
            if ne is not None:
                st.markdown(
                    f"- **False-positive check:** of {int(ne['N_STRATA_TESTED'])} attribute values with no planted CTR "
                    f"effect (stratum by stratum, enough data), {int(ne['N_FALSE_POSITIVE'])} "
                    f"({float(ne['FALSE_POSITIVE_SHARE']) * 100:.1f}%) were classified NET_HELPED or NET_HURT. "
                    f"No multiple-comparison correction is applied.")
            mec = load_model_effect_check()
            if not mec.empty:
                ratios = pd.to_numeric(mec["RATIO_MODEL_TO_PLANTED"], errors="coerce").dropna()
                shrunk = mec[mec["SHRUNK_MORE_THAN_HALF"].astype(bool)]
                st.markdown(
                    f"- **Planted-effect check (model):** scoring a typical ad with one field changed, the predictor's "
                    f"lift has the planted direction in {int(mec['DIRECTION_MATCH'].astype(bool).sum())}/{len(mec)} "
                    f"effects, median model/planted ratio {ratios.median():.2f} (planted effects are partly shrunk).\n"
                    f"- **Known limitation: shrunk or missed interactions.** Effects the model reproduces at less than "
                    f"half the planted size (or with the wrong sign): "
                    + "; ".join(f"{r.EFFECT} ({r.STRATUM})" for r in shrunk.itertuples())
                    + ". Treat Predictor lifts for these as conservative.")
