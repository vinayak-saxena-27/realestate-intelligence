import streamlit as st

from _styles import grade_badge, inject_css, load_page_data
from charts import create_price_history, create_score_components
from config import APP_ICON, GRADE_COLORS, PAGE_TITLES, SEGMENT_LABELS
from narrative import generate_investment_narrative, get_key_pros_cons

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

# ── Narrative + Investment Panel ──────────────────────────────────────────────
VERDICTS = {
    'A': 'Strong Buy — high conviction opportunity.',
    'B': 'Buy — solid fundamentals with minor caveats.',
    'C': 'Hold — monitor before committing capital.',
    'D': 'Caution — significant risk factors present.',
    'F': 'Avoid — does not meet investment criteria.',
}

st.divider()
col_narr, col_invest = st.columns([3, 2])

narrative = generate_investment_narrative(row, pop_stats)
narrative_html = f"""<div style='border-left:4px solid #1B3A5C;background:#EAF2FB;
padding:16px 20px;border-radius:4px;'>
<h4 style='color:#1B3A5C;margin:0 0 8px 0'>Investment Analysis</h4>
<p style='color:#444;line-height:1.7;margin:0'>{narrative}</p>
</div>"""
col_narr.markdown(narrative_html, unsafe_allow_html=True)

pros, cons = get_key_pros_cons(row, pop_stats)
verdict    = VERDICTS[row['investment_grade']]
grade      = row['investment_grade']

with col_invest:
    st.markdown(f"<p style='font-weight:bold;color:#1B3A5C;font-size:14px;margin-bottom:6px'>"
                f"Should I Invest Here?</p>", unsafe_allow_html=True)
    st.markdown(grade_badge(grade), unsafe_allow_html=True)
    st.markdown(f"<p style='font-weight:bold;color:{GRADE_COLORS[grade]};margin:8px 0'>"
                f"{verdict}</p>", unsafe_allow_html=True)
    st.markdown("**Strengths**")
    for pro in pros:
        st.markdown(f'<span style="color:#1A7A4A">&#10003;</span> {pro}',
                    unsafe_allow_html=True)
    st.markdown("**Watch Points**")
    for con in cons:
        st.markdown(f'<span style="color:#C0392B">&#10007;</span> {con}',
                    unsafe_allow_html=True)
