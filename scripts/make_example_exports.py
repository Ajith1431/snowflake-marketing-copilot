"""
Regenerate the four example HTML exports with the same code paths as the app (no browser):
  1. Tab 2 recommendation   Nike / Running Collection / $200,000 / Brand Awareness
  2. Tab 4 pitch            same, using the approved Tab 2 channel plan (not recomputed)
  3. Tab 5 event strategy   Samsung / Black Friday 2026 (the live example)
  4. Tab 3 predictor        preset (b), scored by CREATIVE.SCORE_AD
Writes output/examples/*.html and prints the Tab 2 / Tab 4 KPI tables.
Usage: python scripts/make_example_exports.py [--skip-agents]
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != ROOT]
sys.path.insert(0, str(ROOT / "streamlit"))
sys.path.insert(0, str(ROOT / "src"))

import snowflake.connector  # noqa: E402

from copilot_core import (CHANNEL_RATES_SQL, build_html_document, compute_channel_plan, pitch_prompt,  # noqa: E402
                          plan_markdown, recommendation_prompt, strategy_prompt, today_iso)
from env_keys import get_secret  # noqa: E402

OUT = ROOT / "output" / "examples"
CLIENT, PRODUCT, BUDGET, OBJECTIVE = "Nike", "Running Collection", 200000, "Brand Awareness"


def connect():
    name = get_secret("SNOWFLAKE_CONNECTION", required=False) or "clvulgz-zj61620"
    return snowflake.connector.connect(connection_name=name)


def query(cur, sql, params=None):
    cur.execute(sql, params)
    cols = [c[0].lower() for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def agent_text(raw):
    """Same extraction as call_named_agent in the app: assistant text blocks only."""
    try:
        resp = json.loads(raw)
    except Exception:
        return str(raw)
    if resp.get("code") and "message" in resp:
        return f"Agent error ({resp['code']}): {resp['message']}"
    texts = []
    messages = resp.get("messages") or ([resp] if "content" in resp else [])
    for m in messages:
        if m.get("role") != "assistant":
            continue
        for block in m.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text" and block.get("text", "").strip():
                texts.append(block["text"])
    return "\n\n".join(texts)


def call_agent(cur, agent, prompt):
    body = json.dumps({"messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]})
    cur.execute("SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN(%s, %s)", (agent, body))
    return agent_text(cur.fetchone()[0])


def as_text(html_doc, n=30):
    body = html_doc.split('<div class="content-card">', 1)[-1]
    body = re.sub(r"</(h1|h2|h3|p|li|tr|table|ul)>", "\n", body)
    body = re.sub(r"<(td|th)>", " | ", body)
    body = re.sub(r"<[^>]+>", "", body)
    body = re.sub(r"&amp;", "&", body)
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    return "\n".join(lines[:n])


def main():
    skip_agents = "--skip-agents" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    conn = connect()
    cur = conn.cursor()
    cur.execute("USE WAREHOUSE MARKETING_WH")
    try:
        client_id = query(cur, "SELECT client_id FROM MARKETING_COPILOT.ANALYTICS.DIM_CLIENT WHERE client_name = %s",
                          (CLIENT,))[0]["client_id"]
        tab2_plan = compute_channel_plan(query(cur, CHANNEL_RATES_SQL.format(client_id=client_id)), BUDGET, OBJECTIVE)
        approved = {"client": CLIENT, "product": PRODUCT, "objective": OBJECTIVE, "budget": BUDGET, "plan": tab2_plan}
        tab4_plan = approved["plan"]  # Tab 4 reads the approved plan from session state
        t = tab2_plan["totals"]
        print(f"=== Tab 2 KPI table ({CLIENT} / {PRODUCT} / ${BUDGET:,} / {OBJECTIVE}) ===\n{plan_markdown(tab2_plan)}")
        print(f"clicks x CPC = ${t['clicks'] * t['cpc']:,.0f} (budget ${BUDGET:,})")
        print(f"\n=== Tab 4 KPI table (approved plan passed to the agent) ===\n{plan_markdown(tab4_plan)}")
        print("Tab 2 and Tab 4 tables identical:", plan_markdown(tab2_plan) == plan_markdown(tab4_plan))

        meta = {"Client": CLIENT, "Product": PRODUCT, "Objective": OBJECTIVE, "Budget": f"${BUDGET:,}", "Date": today_iso()}
        docs = {}
        if not skip_agents:
            rec = call_agent(cur, "MARKETING_COPILOT.SEMANTIC.MARKETING_COPILOT",
                             recommendation_prompt(CLIENT, PRODUCT, OBJECTIVE, BUDGET, tab2_plan))
            docs["1_Nike_Running_Collection_recommendation.html"] = build_html_document(
                "Campaign Recommendation", f"{CLIENT} — {PRODUCT}", meta, rec)
            pitch = call_agent(cur, "MARKETING_COPILOT.SEMANTIC.MARKETING_COPILOT",
                               pitch_prompt(CLIENT, PRODUCT, OBJECTIVE, BUDGET, tab4_plan))
            docs["2_Nike_Running_Collection_pitch.html"] = build_html_document(
                "Campaign Pitch", f"{CLIENT} — {PRODUCT}", meta, pitch)
            strat = call_agent(cur, "MARKETING_COPILOT.SEMANTIC.STRATEGY_SYNTHESIS_AGENT",
                               strategy_prompt("Samsung", "Black Friday 2026", 500000, "Drive Event-Day Sales",
                                               "Apple, Xiaomi", "US"))
            docs["3_Samsung_Black_Friday_2026_strategy.html"] = build_html_document(
                "Event Campaign Strategy", "Black Friday 2026 — Samsung",
                {"Client": "Samsung", "Event": "Black Friday 2026", "Budget": "$500,000", "Markets": "US",
                 "Date": today_iso()}, strat)

        base = {"brand": "Nike", "market": "UK", "objective": "LINK_CLICKS", "placement": "feed", "budget": 2000,
                "attributes": {"hook_type": "product_led", "headline_tone": "urgent", "cta_tone": "transactional",
                               "background": "studio", "color_temp": "warm", "has_person": "Y",
                               "word_count_group": "0-5", "has_logo_first_3s": "N"}}
        scen_b = {**base, "attributes": {**base["attributes"], "hook_type": "person_on_camera",
                                         "headline_tone": "conversational"}}
        scores = []
        for p in (base, scen_b):
            cur.execute("CALL MARKETING_COPILOT.CREATIVE.SCORE_AD(PARSE_JSON(%s))", (json.dumps(p, sort_keys=True),))
            scores.append(json.loads(cur.fetchone()[0]))
        ra, rb = scores
        lift = (rb["predicted_ctr"] / ra["predicted_ctr"] - 1) * 100
        pred_md = (f"## Scenario A\n- Inputs: urgent headline, product-led hook (Nike, UK, LINK_CLICKS, feed, $2,000/week)\n"
                   f"- Predicted CTR: {ra['predicted_ctr'] * 100:.2f}% (p10 {ra['p10'] * 100:.2f}%, p90 {ra['p90'] * 100:.2f}%)\n\n"
                   f"## Scenario B\n- Inputs: conversational headline, person on camera (placement held constant)\n"
                   f"- Predicted CTR: {rb['predicted_ctr'] * 100:.2f}% (p10 {rb['p10'] * 100:.2f}%, p90 {rb['p90'] * 100:.2f}%)\n\n"
                   f"## Comparison\n| Measure | Value |\n|---|---|\n| Lift of B vs A (point estimate) | {lift:+.1f}% |\n"
                   f"| Individual ad-week ranges overlap | {'yes' if not (rb['p10'] > ra['p90'] or rb['p90'] < ra['p10']) else 'no'} |\n\n"
                   f"## Caveat\nIllustrative synthetic data. Brand names are labels only. Outputs are scenario estimates, "
                   f"not real forecasts.")
        docs["4_Creative_Predictor_scenario.html"] = build_html_document(
            "Creative Predictor: Scenario Estimate", "Scenario A vs B", {"Data": "Synthetic", "Date": today_iso()}, pred_md)

        for name, doc in docs.items():
            (OUT / name).write_text(doc, encoding="utf-8")
            print(f"\n=== {name}: first 30 lines as text ===\n{as_text(doc)}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
