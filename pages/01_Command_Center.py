import pandas as pd
import streamlit as st

from _styles import grade_badge, inject_css, load_page_data
from charts import create_grade_donut, create_top10_table
from config import APP_ICON, COLORS, PAGE_TITLES

st.set_page_config(page_title=PAGE_TITLES["command_center"], page_icon=APP_ICON, layout="wide")
inject_css()
st.title("Command Center")


def kpi_card(label: str, value: str, delta: str = "") -> str:
    delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>"""


def opportunity_card(row: pd.Series, pop_stats: dict) -> str:
    grade       = row["investment_grade"]
    appr_color  = COLORS["green"] if row["yoy_appreciation"]  > pop_stats["median_yoy_appreciation"]    else COLORS["red"]
    yield_color = COLORS["green"] if row["gross_rental_yield"] > pop_stats["median_gross_rental_yield"] else COLORS["red"]
    segment     = row.get("market_segment", "N/A")
    return f"""
    <div class="opp-card">
        <div style="font-size:16px;font-weight:bold;color:{COLORS['navy']};margin-bottom:8px">
            {row['zip_code']} — {row['metro']}
        </div>
        <div style="margin-bottom:8px">
            {grade_badge(grade)}
        </div>
        <div style="color:{COLORS['gold']};font-weight:bold;margin-bottom:6px">
            Score: {row['investment_score']:.1f}
        </div>
        <div style="color:{appr_color};margin-bottom:4px">
            YoY Appreciation: {row['yoy_appreciation']:.1f}%
        </div>
        <div style="color:{yield_color};margin-bottom:4px">
            Gross Yield: {row['gross_rental_yield']:.1f}%
        </div>
        <div style="margin-bottom:12px">Market Segment: {segment}</div>
        <a href="/Zip_Code_Deep_Dive?zip={row['zip_code']}">View Deep Dive →</a>
    </div>"""


df, pop_stats, latest = load_page_data()

# ── Row 1: KPI Cards ──────────────────────────────────────────────────────────
try:
    ab_count = int(latest["investment_grade"].isin(["A", "B"]).sum())
    kpis = [
        ("Total Zip Codes",          str(latest["zip_code"].nunique()),         ""),
        ("Avg Investment Score",     f"{latest['investment_score'].mean():.1f}", ""),
        ("Top Metro — Appreciation", pop_stats["top_metro_appreciation"],       ""),
        ("Best Rental Yield Metro",  pop_stats["best_yield_metro"],             ""),
        ("Grade A + B Zips",         str(ab_count),                            ""),
    ]
    cols = st.columns(5)
    for col, (label, value, delta) in zip(cols, kpis):
        col.markdown(kpi_card(label, value, delta), unsafe_allow_html=True)
except Exception as e:
    st.error(f"KPI section failed: {e}")

st.divider()

# ── Row 2: Grade Donut + Top 10 Table ─────────────────────────────────────────
try:
    col_left, col_right = st.columns([1, 1.6])
    with col_left:
        st.subheader("Grade Distribution")
        st.plotly_chart(create_grade_donut(df), use_container_width=True)
    with col_right:
        st.subheader("Top 10 Zip Codes")
        top10 = create_top10_table(df).copy()
        top10["Grade"] = top10["Grade"].apply(grade_badge)
        st.markdown(top10.to_html(escape=False, index=False), unsafe_allow_html=True)
except Exception as e:
    st.error(f"Charts section failed: {e}")

st.divider()

# ── Row 3: Best Opportunity Cards ─────────────────────────────────────────────
try:
    st.subheader("Best Opportunities Right Now")
    top3 = latest[latest["investment_grade"] == "A"].nlargest(3, "investment_score")
    if len(top3) < 3:
        backfill = latest[latest["investment_grade"] == "B"].nlargest(
            3 - len(top3), "investment_score"
        )
        top3 = pd.concat([top3, backfill])

    opp_cols = st.columns(3)
    for col, (_, row) in zip(opp_cols, top3.iterrows()):
        col.markdown(opportunity_card(row, pop_stats), unsafe_allow_html=True)
except Exception as e:
    st.error(f"Opportunities section failed: {e}")
