import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from snowflake.snowpark.context import get_active_session

# -- Page config --
st.set_page_config(page_title="NovaSpark Marketing Co-Pilot", page_icon="📊", layout="wide")

# -- Color palette --
PRIMARY = "#0068FF"
SECONDARY = "#00D4AA"
ACCENT = "#FF6B35"
COLORS = [PRIMARY, SECONDARY, ACCENT, "#8B5CF6", "#F43F5E", "#FBBF24", "#34D399", "#60A5FA", "#A78BFA", "#FB923C"]

PLOTLY_TEMPLATE = "plotly_dark"

# -- Session --
session = get_active_session()


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
                for c in m.get("content", []):
                    if c.get("type") == "text":
                        texts.append(c["text"])
        return "\n\n".join(texts) if texts else raw
    except Exception:
        return raw


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

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Client Intelligence",
    "🎯 Campaign Recommendation",
    "🔀 What-If Analysis",
    "📋 Generate Pitch",
    "🌍 Event Intelligence"
])

# ============================
# TAB 1: Client Intelligence
# ============================
with tab1:
    kpis = load_client_kpis(client_id)
    sentiment = load_sentiment(client_id)
    k = kpis.iloc[0]
    s = sentiment.iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Campaigns", int(k["TOTAL_CAMPAIGNS"]))
    c2.metric("Avg ROAS", f"{k['AVG_ROAS']}x")
    c3.metric("Total Spend", format_usd(k["TOTAL_SPEND"]))
    c4.metric("Avg Sentiment", f"{s['AVG_SENTIMENT']:.2f}")

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
        with st.spinner("Analyzing campaign data and generating recommendation (auto-continues if needed)..."):
            prompt = (
                f"Create a detailed campaign recommendation for {selected_client} "
                f"for their product '{selected_product}'. "
                f"Campaign objective: {objective}. "
                f"Budget: ${budget:,}. "
                f"Include: recommended channels with budget allocation percentages, "
                f"target audience segments, expected KPIs (ROAS, impressions, conversions), "
                f"and strategy rationale. Ground everything in historical performance data."
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
        st.markdown(rec)

        if response_is_incomplete(rec):
            st.warning("The recommendation may still be incomplete after auto-continuation.")

        st.divider()

        col_a, col_b = st.columns([1, 4])
        with col_a:
            if st.button("✅ Approve Recommendation", type="primary"):
                st.session_state["recommendation_approved"] = True
                st.success("Recommendation approved. Go to 'Generate Pitch' tab.")
        with col_b:
            if st.button("🔄 Regenerate"):
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
            st.markdown("**Current Allocation (equal split)**")
            for ch in channel_list:
                current_alloc[ch] = budget * default_pct / 100
                st.text(f"{ch}: {format_usd(current_alloc[ch])} ({default_pct}%)")

        with col_proposed:
            st.markdown("**Proposed Allocation**")
            remaining = 100
            for i, ch in enumerate(channel_list):
                max_val = remaining if i == len(channel_list) - 1 else remaining
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

            m1, m2, m3 = st.columns(3)
            m1.metric("Projected Revenue (Current)", format_usd(total_cur_rev))
            m2.metric("Projected Revenue (Proposed)", format_usd(total_prop_rev),
                       delta=format_usd(delta_rev))
            m3.metric("Projected Conversions (Proposed)", format_number(total_prop_conv),
                       delta=format_number(total_prop_conv - total_cur_conv))

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


# ============================
# TAB 4: Generate Pitch
# ============================
with tab4:
    if st.session_state.get("recommendation_approved"):
        st.subheader(f"Campaign Pitch: {selected_product} for {selected_client}")
        if "pitch_content" not in st.session_state:
            if st.button("📝 Generate Full Pitch", type="primary"):
                with st.spinner("Generating pitch document (auto-continues if needed)..."):
                    prompt = (
                        f"Generate a complete client-ready campaign pitch document for {selected_client}, "
                        f"product: {selected_product}, objective: {objective}, budget: ${budget:,}. "
                        f"Include these sections: "
                        f"1. Executive Summary, "
                        f"2. Client & Product Overview, "
                        f"3. Campaign Objective & KPIs, "
                        f"4. Target Audience Analysis, "
                        f"5. Channel Strategy with budget allocation, "
                        f"6. Creative Direction (based on brand guidelines), "
                        f"7. Expected Impact and projected metrics. "
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
                st.warning("The pitch may still be incomplete after auto-continuation.")

            sections = pitch.split("\n## ")
            if len(sections) > 1:
                st.markdown(sections[0])
                for s in sections[1:]:
                    title = s.split("\n")[0].strip().lstrip("#").strip()
                    body = "\n".join(s.split("\n")[1:])
                    with st.expander(f"📌 {title}", expanded=True):
                        st.markdown(body)
            else:
                st.markdown(pitch)

            st.divider()
            col_dl, col_reset = st.columns([1, 4])
            with col_dl:
                st.download_button(
                    "⬇️ Download Pitch (.md)",
                    pitch,
                    file_name=f"pitch_{selected_client}_{selected_product}.md",
                    mime="text/markdown"
                )
            with col_reset:
                if st.button("🔄 Start Over"):
                    for key in ["recommendation", "recommendation_approved", "pitch_content"]:
                        st.session_state.pop(key, None)
                    st.experimental_rerun()
    else:
        st.info("Approve a campaign recommendation in the **Campaign Recommendation** tab first to generate a pitch document.")


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
            key="ei_competitors"
        )

        markets_input = st.text_input(
            "Target Markets (comma-separated)",
            value="US, UK, India",
            key="ei_markets"
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
            "1. **Research Phase** — The Internet Intelligence Agent pulls Google Trends, "
            "news articles, and web intelligence for your event and competitors.\n\n"
            "2. **Analysis Phase** — Data is loaded into Snowflake dynamic tables for "
            "real-time analytics: trend patterns, news sentiment, competitor presence.\n\n"
            "3. **Strategy Phase** — The Strategy Synthesis Agent combines internal campaign "
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

        # Step 1: Call Internet Intelligence Agent
        progress.progress(10, text="Calling Internet Intelligence Agent...")
        intel_prompt = (
            f"Research the market event '{selected_event}' for client {selected_client}. "
            f"Keywords: {', '.join(keywords_list)}. "
            f"Competitors: {', '.join(competitors_list)}. "
            f"Target markets: {', '.join(markets_list)}. "
            f"Gather Google Trends data, recent news articles, and web intelligence about "
            f"competitive positioning and market opportunities for this event."
        )

        intel_response = call_named_agent(
            'MARKETING_COPILOT.SEMANTIC.INTERNET_INTELLIGENCE_AGENT',
            intel_prompt
        )
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

        # Display Intelligence Results
        st.session_state["ei_trends_data"] = trends_df
        st.session_state["ei_news_data"] = news_df
        st.session_state["ei_competitors_data"] = competitor_df

        progress.progress(100, text="Research complete!")

    # -- Display cached intelligence results --
    if "ei_intel_response" in st.session_state:
        st.divider()

        # Agent response
        with st.expander("🤖 Intelligence Agent Findings", expanded=True):
            st.markdown(st.session_state["ei_intel_response"])

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

                peak_rows = trends_df[trends_df.get("IS_PEAK_DATE", pd.Series(dtype=bool)) == True]
                if not peak_rows.empty:
                    st.success(f"Peak interest detected on: {', '.join(peak_rows['TREND_DATE'].astype(str).unique()[:3])}")

        # News sentiment
        news_df = st.session_state.get("ei_news_data", pd.DataFrame())
        if not news_df.empty:
            with st.expander("📰 News Sentiment Overview", expanded=True):
                sent_cols = st.columns(3)
                pos_count = len(news_df[news_df.get("SENTIMENT_LABEL", pd.Series()) == "positive"])
                neg_count = len(news_df[news_df.get("SENTIMENT_LABEL", pd.Series()) == "negative"])
                neu_count = len(news_df) - pos_count - neg_count
                sent_cols[0].metric("Positive", pos_count)
                sent_cols[1].metric("Neutral", neu_count)
                sent_cols[2].metric("Negative", neg_count)

                if "SENTIMENT_LABEL" in news_df.columns:
                    sent_fig = px.pie(
                        news_df["SENTIMENT_LABEL"].value_counts().reset_index(),
                        values="count", names="SENTIMENT_LABEL",
                        color_discrete_sequence=[SECONDARY, "#94A3B8", ACCENT],
                        template=PLOTLY_TEMPLATE
                    )
                    sent_fig.update_layout(height=300, margin=dict(t=20, b=20))
                    st.plotly_chart(sent_fig, use_container_width=True)

                st.dataframe(
                    news_df[["TITLE", "SOURCE", "SENTIMENT_LABEL", "PUBLISHED_DATE"]].head(15),
                    use_container_width=True, hide_index=True
                )

        # Competitor presence
        competitor_df = st.session_state.get("ei_competitors_data", pd.DataFrame())
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
                with st.spinner("Strategy Synthesis Agent is building your event strategy..."):
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
                        f"Base recommendations on both historical campaign performance data "
                        f"and current market intelligence."
                    )
                    strategy = call_named_agent(
                        'MARKETING_COPILOT.SEMANTIC.STRATEGY_SYNTHESIS_AGENT',
                        strategy_prompt
                    )
                    st.session_state["ei_strategy"] = strategy
                    st.experimental_rerun()
        else:
            strategy = st.session_state["ei_strategy"]

            if response_is_incomplete(strategy):
                st.warning("The strategy was cut short. Click below to continue.")
                if st.button("🔄 Continue strategy", key="continue_ei_strategy"):
                    with st.spinner("Continuing strategy..."):
                        continuation = call_named_agent(
                            'MARKETING_COPILOT.SEMANTIC.STRATEGY_SYNTHESIS_AGENT',
                            f"Continue the event marketing strategy you were writing for "
                            f"{selected_client} and '{selected_event}'. Pick up where you left off."
                        )
                        st.session_state["ei_strategy"] = strategy.rstrip() + "\n\n" + continuation
                        st.experimental_rerun()

            # Display strategy in expandable sections
            sections = strategy.split("\n## ")
            if len(sections) > 1:
                st.markdown(sections[0])
                for sec in sections[1:]:
                    title = sec.split("\n")[0].strip().lstrip("#").strip()
                    body = "\n".join(sec.split("\n")[1:])
                    with st.expander(f"📌 {title}", expanded=True):
                        st.markdown(body)
            else:
                st.markdown(strategy)

            st.divider()

            dl_col, reset_col = st.columns([1, 4])
            with dl_col:
                st.download_button(
                    "⬇️ Download Strategy (.md)",
                    strategy,
                    file_name=f"event_strategy_{selected_client}_{selected_event.replace(' ', '_')}.md",
                    mime="text/markdown",
                    key="ei_download"
                )
            with reset_col:
                if st.button("🔄 New Research", key="ei_reset"):
                    for key in ["ei_intel_response", "ei_trends_data", "ei_news_data",
                                "ei_competitors_data", "ei_strategy"]:
                        st.session_state.pop(key, None)
                    st.experimental_rerun()
