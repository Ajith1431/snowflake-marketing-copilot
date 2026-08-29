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


def call_agent(prompt):
    request_body = json.dumps(
        {"messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]}
    )
    request_body = request_body.replace("$$", "$ $")
    sql = f"""
        SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN(
            'MARKETING_COPILOT.SEMANTIC.MARKETING_COPILOT',
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

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Client Intelligence",
    "🎯 Campaign Recommendation",
    "🔀 What-If Analysis",
    "📋 Generate Pitch"
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
        with st.spinner("Analyzing campaign data and generating recommendation..."):
            prompt = (
                f"Create a detailed campaign recommendation for {selected_client} "
                f"for their product '{selected_product}'. "
                f"Campaign objective: {objective}. "
                f"Budget: ${budget:,}. "
                f"Include: recommended channels with budget allocation percentages, "
                f"target audience segments, expected KPIs (ROAS, impressions, conversions), "
                f"and strategy rationale. Ground everything in historical performance data."
            )
            response = call_agent(prompt)
            st.session_state["recommendation"] = response
            st.session_state["recommendation_approved"] = False

    if "recommendation" in st.session_state:
        rec = st.session_state["recommendation"]
        st.markdown(rec)

        if response_is_incomplete(rec):
            st.warning("The recommendation was cut short by the agent time limit.")
            if st.button("🔄 Continue generating", key="continue_rec"):
                with st.spinner("Continuing recommendation..."):
                    continuation = call_agent(
                        f"Continue the campaign recommendation you were writing for {selected_client}. "
                        f"Pick up exactly where you left off. Do not repeat sections already written."
                    )
                    st.session_state["recommendation"] = rec.rstrip() + "\n\n" + continuation
                    st.experimental_rerun()

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
                with st.spinner("Generating pitch document with brand guidelines..."):
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
                    pitch = call_agent(prompt)
                    st.session_state["pitch_content"] = pitch
                    st.experimental_rerun()
        else:
            pitch = st.session_state["pitch_content"]

            if response_is_incomplete(pitch):
                st.warning("The pitch was cut short by the agent time limit. Click below to continue.")
                if st.button("🔄 Continue generating pitch", key="continue_pitch"):
                    with st.spinner("Continuing pitch generation..."):
                        continuation = call_agent(
                            f"Continue the campaign pitch document you were writing for {selected_client}, "
                            f"product: {selected_product}. Pick up exactly where you left off. "
                            f"Do not repeat sections already written. Complete the remaining sections."
                        )
                        st.session_state["pitch_content"] = pitch.rstrip() + "\n\n" + continuation
                        st.experimental_rerun()

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
