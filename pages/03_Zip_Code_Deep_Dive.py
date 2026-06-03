import streamlit as st

from _styles import inject_css, load_page_data
from charts import create_price_history, create_score_components
from config import APP_ICON, PAGE_TITLES, SEGMENT_LABELS

st.set_page_config(page_title=PAGE_TITLES["deep_dive"], page_icon=APP_ICON, layout="wide")
inject_css()
st.title(PAGE_TITLES["deep_dive"])

df, pop_stats, latest = load_page_data()

# ── Zip selector ──────────────────────────────────────────────────────────────
# Pre-build lookup so format_func doesn't re-filter df on every render
zip_info   = latest.set_index("zip_code")[["metro", "investment_score"]].to_dict("index")
sorted_zips = latest.sort_values("investment_score", ascending=False)["zip_code"].tolist()

# Pre-select from query param if navigated from Command Center opportunity card
query_zip    = st.query_params.get("zip", None)
default_idx  = sorted_zips.index(query_zip) if query_zip in sorted_zips else 0

selected_zip = st.selectbox(
    "Select Zip Code",
    options=sorted_zips,
    index=default_idx,
    format_func=lambda z: f"{z} — {zip_info[z]['metro']} (Score: {zip_info[z]['investment_score']:.1f})",
)

# ── Row for selected zip (latest month) ───────────────────────────────────────
zip_rows = latest[latest["zip_code"] == selected_zip]
if zip_rows.empty:
    st.warning("No data found for the selected zip code.")
    st.stop()
row = zip_rows.iloc[0]

st.divider()

# ── 6 Metric cards (2 rows × 3 cols) ─────────────────────────────────────────
metrics = [
    (
        "Median Sale Price",
        f"${row['median_sale_price']:,.0f}",
        f"${row['median_sale_price'] - df['median_sale_price'].median():+,.0f} vs median",
        None,
    ),
    (
        "Investment Score",
        f"{row['investment_score']:.1f} / 100",
        row["investment_grade"],
        None,
    ),
    (
        "YoY Appreciation",
        f"{row['yoy_appreciation']:.1f}%",
        f"{row['yoy_appreciation'] - pop_stats['median_yoy_appreciation']:+.1f}% vs median",
        None,
    ),
    (
        "Gross Rental Yield",
        f"{row['gross_rental_yield']:.1f}%",
        f"{row['gross_rental_yield'] - pop_stats['median_gross_rental_yield']:+.1f}% vs median",
        None,
    ),
    (
        "Days on Market",
        f"{int(row['days_on_market'])} days",
        f"{int(row['days_on_market'] - pop_stats['median_days_on_market']):+d} vs median",
        "inverse",  # lower DOM is better — flip green/red
    ),
    (
        "Market Segment",
        row["market_segment"],
        SEGMENT_LABELS.get(row["market_segment"], ""),
        "off",  # descriptive text, no directional colour
    ),
]

metric_cols = st.columns(3)
for i, (label, value, delta, delta_color) in enumerate(metrics):
    kwargs = dict(label=label, value=value, delta=delta)
    if delta_color:
        kwargs["delta_color"] = delta_color
    with metric_cols[i % 3]:
        st.metric(**kwargs)

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
try:
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.subheader("Price History & Forecast")
        st.plotly_chart(create_price_history(df, selected_zip), use_container_width=True)
    with chart_right:
        st.subheader("Score Breakdown")
        st.plotly_chart(create_score_components(row, df), use_container_width=True)
except Exception as e:
    st.error(f"Chart rendering failed: {e}")

# ── Week 5 placeholder ────────────────────────────────────────────────────────
st.divider()
st.subheader("Investment Analysis")
st.info("Narrative analysis coming in Week 5.")
# Week 5: replace with generate_investment_narrative(row, pop_stats)
