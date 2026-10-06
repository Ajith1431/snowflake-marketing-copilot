"""
Pure helpers shared by streamlit_app.py and scripts/make_example_exports.py (no Streamlit, no Snowflake session):
markdown cleanup and HTML export, the channel-plan / KPI calculator, agent prompt builders and event dates.
"""

import html as html_lib
import re
from datetime import date, datetime

# ---------------------------------------------------------------------------- export cleanup
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+\S")
_OFFER = re.compile(r"^\s*(\*\*)?\s*(would you like|do you want|shall i|should i|let me know if|"
                    r"i can also|if you(?:'d| would) like|want me to)", re.I)
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
CHART_NOTE = ("Charts shown in the app are not included in this download; the figures behind them are in the "
              "tables above.")


def clean_agent_markdown(text):
    """Drop preamble before the first heading, closing 'Would you like me to...' offers and dangling lead-ins."""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    first = next((i for i, l in enumerate(lines) if _HEADING.match(l)), None)
    if first:
        lines = lines[first:]

    # closing offer: the last offer line near the end, plus anything after it that is only bullets or blank
    tail_start = max(0, len(lines) - 15)
    for i in range(len(lines) - 1, tail_start - 1, -1):
        if _OFFER.match(lines[i]):
            rest = lines[i + 1:]
            if all(not r.strip() or re.match(r"^\s*([-*]|\d+\.)\s", r) for r in rest):
                lines = lines[:i]
            break
    while lines and (not lines[-1].strip() or lines[-1].strip() in ("---", "***", "___")):
        lines.pop()

    # dangling lead-in: a line ending with ':' whose next non-empty line is a heading, a rule or nothing
    out = []
    for i, line in enumerate(lines):
        s = line.strip()
        if s.endswith(":") and not s.startswith(("|", "#")):
            nxt = next((l.strip() for l in lines[i + 1:] if l.strip()), "")
            if not nxt or _HEADING.match(nxt) or nxt in ("---", "***", "___"):
                continue
        out.append(line)
    return "\n".join(out).strip()


def _split_row(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def markdown_tables_to_html(text):
    """Convert GitHub-style markdown tables (header row + --- separator) into <table> markup, one row per line."""
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        if (lines[i].strip().startswith("|") and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1])):
            header = _split_row(lines[i])
            out.append("<table>")
            out.append("<tr>" + "".join(f"<th>{c}</th>" for c in header) + "</tr>")
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = _split_row(lines[i])
                cells += [""] * (len(header) - len(cells))
                out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells[:len(header)]) + "</tr>")
                i += 1
            out.append("</table>")
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def build_html_document(title, subtitle, metadata, content, confidence=None, chart_note=True):
    conf_colours = {"HIGH": ("#00D4AA", "#003D30"), "MEDIUM": ("#FFD700", "#3D3000"), "LOW": ("#FF6B35", "#3D1500")}
    conf_bg, conf_text = conf_colours.get(confidence, ("#6B7280", "#1F2937"))
    conf_badge = (f'<span style="background:{conf_bg};color:{conf_text};padding:4px 12px;border-radius:20px;'
                  f'font-size:12px;font-weight:bold;letter-spacing:1px;">{confidence}</span>') if confidence else ""
    esc = html_lib.escape
    meta_pills = "".join(
        f'<span style="background:#1E293B;color:#94A3B8;padding:4px 12px;border-radius:20px;font-size:12px;'
        f'margin-right:8px;"><b style="color:#E2E8F0">{esc(str(k))}:</b> {esc(str(v))}</span>'
        for k, v in metadata.items())

    # agent text is untrusted: escape first, then apply the small markdown subset below
    html_content = esc(clean_agent_markdown(content), quote=False)
    html_content = markdown_tables_to_html(html_content)
    html_content = re.sub(r'^### (.+)$', r'<h3 style="color:#00D4AA;margin-top:24px;margin-bottom:8px;font-size:16px;">\1</h3>',
                          html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^## (.+)$', r'<h2 style="color:#0068FF;margin-top:32px;margin-bottom:12px;font-size:20px;'
                          r'border-bottom:2px solid #0068FF;padding-bottom:8px;">\1</h2>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^# (.+)$', r'<h1 style="color:#FFFFFF;font-size:24px;">\1</h1>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#E2E8F0">\1</strong>', html_content)
    html_content = re.sub(r'^\s*[-*] (.+)$', r'<li style="margin-bottom:6px;color:#CBD5E1;">\1</li>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'(<li[^>]*>.*?</li>\n?)+', lambda m: f'<ul style="padding-left:20px;margin:12px 0;">{m.group()}</ul>',
                          html_content, flags=re.DOTALL)
    html_content = re.sub(r'^\s*(---|\*\*\*|___)\s*$', '<hr style="border:none;border-top:1px solid #1E293B;margin:24px 0;">',
                          html_content, flags=re.MULTILINE)
    processed = []
    for line in html_content.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("<"):
            processed.append(f'<p style="color:#CBD5E1;line-height:1.7;margin-bottom:12px;">{stripped}</p>')
        else:
            processed.append(line)
    html_content = "\n".join(processed)
    if chart_note:
        html_content += f'\n<p style="color:#64748B;font-size:12px;margin-top:24px;"><em>{CHART_NOTE}</em></p>'

    generated_date = datetime.now().strftime('%B %d, %Y at %H:%M')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
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
<div class="doc-title">{esc(title)}</div>
<div class="doc-subtitle">{esc(subtitle)}</div>
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


# ---------------------------------------------------------------------------- channel plan and KPIs
# Pooled per-dollar rates per channel: SUM(metric) / SUM(spend). Pooling (not averaging daily ratios) keeps
# clicks x CPC equal to spend.
CHANNEL_RATES_SQL = """
SELECT channel_name, COUNT(DISTINCT campaign_id) AS campaigns, SUM(spend_usd) AS spend,
       SUM(impressions) / SUM(spend_usd) AS impr_per_usd, SUM(clicks) / SUM(spend_usd) AS clicks_per_usd,
       SUM(conversions) / SUM(spend_usd) AS conv_per_usd, SUM(revenue_usd) / SUM(spend_usd) AS rev_per_usd
FROM MARKETING_COPILOT.ANALYTICS.FACT_CAMPAIGN_METRICS
WHERE client_id = '{client_id}' AND spend_usd > 0
GROUP BY channel_name
"""
OBJECTIVE_METRIC = {  # which historical per-dollar rate ranks channels for each objective
    "Brand Awareness": ("impr_per_usd", "impressions per $"),
    "Lead Generation": ("conv_per_usd", "conversions per $"),
    "Sales Conversion": ("rev_per_usd", "revenue per $ (ROAS)"),
    "Customer Retention": ("conv_per_usd", "conversions per $"),
}


def compute_channel_plan(rates, budget, objective, n_channels=4):
    """rates: list of dicts (CHANNEL_RATES_SQL columns, lower-case). Returns {'channels': [...], 'totals': {...}, ...}.

    Same method for every objective: rank channels by the objective's historical per-dollar rate, keep the top
    n_channels, split the budget in proportion to that rate (whole percent, summing to 100), then project each KPI
    as allocated dollars x the channel's pooled historical per-dollar rate.
    """
    metric, metric_label = OBJECTIVE_METRIC.get(objective, OBJECTIVE_METRIC["Sales Conversion"])
    rows = sorted((dict(r) for r in rates if float(r.get(metric) or 0) > 0),
                  key=lambda r: float(r[metric]), reverse=True)[:n_channels]
    if not rows:
        return {"channels": [], "totals": {}, "objective": objective, "metric": metric_label, "budget": budget}
    total_score = sum(float(r[metric]) for r in rows)
    pcts = [round(100 * float(r[metric]) / total_score) for r in rows]
    pcts[0] += 100 - sum(pcts)
    channels = []
    for r, pct in zip(rows, pcts):
        spend = budget * pct / 100.0
        impr = spend * float(r["impr_per_usd"])
        clicks = spend * float(r["clicks_per_usd"])
        conv = spend * float(r["conv_per_usd"])
        rev = spend * float(r["rev_per_usd"])
        channels.append({"channel": r["channel_name"], "pct": pct, "budget": spend, "campaigns": int(r["campaigns"]),
                         "impressions": impr, "clicks": clicks, "cpc": spend / clicks if clicks else 0.0,
                         "ctr": clicks / impr if impr else 0.0, "conversions": conv, "revenue": rev,
                         "roas": rev / spend if spend else 0.0})
    t = {k: sum(c[k] for c in channels) for k in ("budget", "impressions", "clicks", "conversions", "revenue")}
    t.update(cpc=t["budget"] / t["clicks"] if t["clicks"] else 0.0, ctr=t["clicks"] / t["impressions"] if t["impressions"] else 0.0,
             roas=t["revenue"] / t["budget"] if t["budget"] else 0.0, campaigns=None)
    return {"channels": channels, "totals": t, "objective": objective, "metric": metric_label, "budget": budget}


def plan_rows(plan):
    """Display rows (channel lines + total) for st.dataframe or a markdown table."""
    def fmt(c, name, pct):
        return {"Channel": name, "Allocation": pct, "Budget": f"${c['budget']:,.0f}",
                "Campaigns behind rates": "" if c["campaigns"] is None else f"{c['campaigns']}", "Impressions": f"{c['impressions']:,.0f}",
                "Clicks": f"{c['clicks']:,.0f}", "CPC": f"${c['cpc']:.2f}", "Conversions": f"{c['conversions']:,.0f}",
                "Revenue": f"${c['revenue']:,.0f}", "ROAS": f"{c['roas']:.2f}x"}
    rows = [fmt(c, c["channel"], f"{c['pct']}%") for c in plan["channels"]]
    if plan.get("totals"):
        rows.append(fmt(plan["totals"], "Total", "100%"))
    return rows


def plan_markdown(plan):
    rows = plan_rows(plan)
    if not rows:
        return "(no channel history for this client)"
    cols = list(rows[0])
    return "\n".join(["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
                     + ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in rows])


# ---------------------------------------------------------------------------- dates and events
def today_iso():
    return date.today().isoformat()


# Tab 5 events: (start, end, note). Dates are calendar facts; notes say how each example should be read.
EVENT_CATALOG = {
    "Black Friday 2026": ("2026-11-27", "2026-11-27", "Live example: upcoming event with a full intelligence run."),
    "FIFA World Cup 2026": ("2026-06-11", "2026-07-19", "Retrospective example: the tournament ended July 19, 2026."),
    "Cyber Monday 2026": ("2026-11-30", "2026-11-30", ""),
    "Holiday Season 2026": ("2026-11-27", "2026-12-31", ""),
    "Valentine's Day 2027": ("2027-02-14", "2027-02-14", ""),
    "Summer Olympics 2028": ("2028-07-14", "2028-07-30", ""),
    "Black Friday 2025": ("2025-11-28", "2025-11-28", "Past event."),
    "Super Bowl 2025": ("2025-02-09", "2025-02-09", "Past event."),
}


def event_status(start, end, today=None):
    today = today or today_iso()
    if end < today:
        return "past"
    if start > today:
        return "upcoming"
    return "in progress"


DATE_RULES = ("Today is {today}. Treat any event whose end date is before today as past: describe it in the past "
              "tense as a retrospective and never as planned or upcoming. Only events with a start date after today "
              "are upcoming.")
CONFIDENCE_RULES = ("Channel rankings and KPIs are historical averages from synthetic campaign data with no "
                    "significance testing, so confidence in the relative ranking of channels is at most MEDIUM. "
                    "For each channel figure, state the number of campaigns behind it.")
FIXED_PLAN_RULES = ("Use these channels, allocation and KPIs exactly; do not recompute them. "
                    "They were computed from pooled historical per-dollar rates, so clicks x CPC equals the budget.")


def _plan_block(plan):
    return (f"Channel plan and projected KPIs for objective '{plan['objective']}' (channels ranked by historical "
            f"{plan['metric']}; KPIs = allocated budget x pooled historical per-dollar rate):\n{plan_markdown(plan)}")


UPCOMING_EVENTS_SQL = """
SELECT event_name, start_date::VARCHAR AS start_date, end_date::VARCHAR AS end_date
FROM MARKETING_COPILOT.ANALYTICS.DIM_MARKET_EVENT WHERE start_date > CURRENT_DATE() ORDER BY start_date LIMIT 12
"""


def _upcoming_block(upcoming):
    if upcoming is None:
        return ""
    if not upcoming:
        return "\n\nThere are no upcoming market events in the data; do not describe any market event as upcoming."
    items = "; ".join(f"{e['event_name']} ({e['start_date']})" for e in upcoming)
    return (f"\n\nUpcoming market events (start date after today): {items}. These are the only events you may call "
            f"upcoming; any other event found by search is past and may only be cited as history.")


def recommendation_prompt(client, product, objective, budget, plan, today=None, upcoming=None):
    return (f"{DATE_RULES.format(today=today or today_iso())}{_upcoming_block(upcoming)}\n\n"
            f"Create a detailed campaign recommendation for {client} for their product '{product}'. "
            f"Campaign objective: {objective}. Budget: ${budget:,}.\n\n{_plan_block(plan)}\n\n{FIXED_PLAN_RULES}\n\n"
            f"Include: the channel plan table above, target audience segments, the expected KPIs from the table, "
            f"and strategy rationale grounded in historical performance data. {CONFIDENCE_RULES} "
            f"Start directly with a ## heading and use ## markdown headers for every section. "
            f"Do not end with offers of further help.")


def pitch_prompt(client, product, objective, budget, plan, today=None, upcoming=None):
    return (f"{DATE_RULES.format(today=today or today_iso())}{_upcoming_block(upcoming)}\n\n"
            f"Generate a complete client-ready campaign pitch document for {client}, product: {product}, "
            f"objective: {objective}, budget: ${budget:,}. This pitch follows the approved recommendation.\n\n"
            f"{_plan_block(plan)}\n\n{FIXED_PLAN_RULES}\n\n"
            f"Include these sections with ## markdown headers: 1. Executive Summary, 2. Client & Product Overview, "
            f"3. Campaign Objective & KPIs, 4. Target Audience Analysis, 5. Channel Strategy with budget allocation "
            f"(the table above), 6. Creative Direction (based on brand guidelines), 7. Expected Impact and projected "
            f"metrics (the table above). End with a Confidence Level (HIGH/MEDIUM/LOW) with explanation. "
            f"{CONFIDENCE_RULES} Start directly with a ## heading. Do not end with offers of further help.")


def _event_line(event, today):
    start, end, _ = EVENT_CATALOG.get(event, ("", "", ""))
    if not start:
        return f"Event: {event} (date not in the catalogue; check it before describing the event as upcoming)."
    span = start if start == end else f"{start} to {end}"
    return f"Event: {event}, dates {span}, status as of today: {event_status(start, end, today)}."


def intel_prompt(client, event, keywords, competitors, markets, today=None):
    today = today or today_iso()
    return (f"{DATE_RULES.format(today=today)} {_event_line(event, today)}\n\n"
            f"Research the market event '{event}' for client {client}. Keywords: {', '.join(keywords)}. "
            f"Competitors: {', '.join(competitors)}. Target markets: {', '.join(markets)}. Gather Google Trends data, "
            f"recent news articles, and web intelligence about competitive positioning and market opportunities "
            f"for this event. Start directly with a ## heading.")


def strategy_prompt(client, event, budget, objective, competitors, markets, today=None):
    today = today or today_iso()
    return (f"{DATE_RULES.format(today=today)} {_event_line(event, today)}\n\n"
            f"Create a comprehensive event marketing strategy for {client} targeting the '{event}' event. "
            f"Budget: ${budget:,}. Objective: {objective}. Competitors: {competitors}. Markets: {markets}. "
            f"Include: 1) Channel allocation with percentages, 2) Creative direction and messaging themes, "
            f"3) Timeline with key milestones (if the event is past, write a retrospective with lessons instead of "
            f"a forward plan), 4) Expected impact metrics (reach, engagement, conversions), 5) Competitive positioning "
            f"strategy. {CONFIDENCE_RULES} Base recommendations on both historical campaign performance data and the "
            f"stored market intelligence. End with a '## Sources' section that lists, for each competitor claim, the "
            f"news article (title and source) or web-intelligence query it comes from, and include this line in it: "
            f"\"Competitive claims come from live web research and need verification.\" "
            f"Start directly with a ## heading and use ## markdown headers for each section. "
            f"Do not end with offers of further help.")
