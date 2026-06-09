import streamlit as st

from _styles import grade_badge, inject_css, load_page_data
from charts import create_price_history, create_score_components
from config import GRADE_COLORS, PAGE_TITLES, SEGMENT_LABELS
from narrative import generate_investment_narrative, get_key_pros_cons

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

try:
    metric_cols = st.columns(3)
    for i, (label, value, delta, delta_color) in enumerate(metrics):
        kwargs = dict(label=label, value=value, delta=delta)
        if delta_color:
            kwargs["delta_color"] = delta_color
        with metric_cols[i % 3]:
            st.metric(**kwargs)
except Exception as e:
    st.warning(f"Metric cards could not be rendered — some data may be missing: {e}")

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

try:
    narrative = generate_investment_narrative(row, pop_stats)
    narrative_html = f"""
    <div style='background:white;border:1px solid #DDE4EE;border-left:4px solid {GRADE_COLORS[row["investment_grade"]]};
    border-radius:0 12px 12px 0;padding:20px 24px;
    box-shadow:0 1px 3px rgba(27,58,92,0.06),0 4px 12px rgba(27,58,92,0.03);'>
        <div style='font-size:10px;font-weight:600;color:#8A9BB0;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:10px'>
            Investment Analysis
        </div>
        <p style='color:#2D3748;line-height:1.8;margin:0;font-size:14px'>{narrative}</p>
    </div>"""
    col_narr.markdown(narrative_html, unsafe_allow_html=True)
except Exception as e:
    col_narr.warning(f"Investment narrative unavailable: {e}")

try:
    pros, cons = get_key_pros_cons(row, pop_stats)
    verdict    = VERDICTS[row['investment_grade']]
    grade      = row['investment_grade']

    pros_html = "".join(
        f"<div style='display:flex;align-items:flex-start;gap:8px;margin-bottom:7px'>"
        f"<span style='color:#1A7A4A;font-size:13px;line-height:1.5;flex-shrink:0'>✓</span>"
        f"<span style='color:#2D3748;font-size:13px;line-height:1.5'>{p}</span></div>"
        for p in pros
    )
    cons_html = "".join(
        f"<div style='display:flex;align-items:flex-start;gap:8px;margin-bottom:7px'>"
        f"<span style='color:#C0392B;font-size:13px;line-height:1.5;flex-shrink:0'>✗</span>"
        f"<span style='color:#2D3748;font-size:13px;line-height:1.5'>{c}</span></div>"
        for c in cons
    )
    invest_html = f"""
    <div style='background:white;border:1px solid #DDE4EE;border-radius:12px;
    padding:22px 24px;box-shadow:0 1px 3px rgba(27,58,92,0.06),0 4px 12px rgba(27,58,92,0.03);'>
        <div style='font-size:10px;font-weight:600;color:#8A9BB0;text-transform:uppercase;
        letter-spacing:0.8px;margin-bottom:12px'>Should I Invest Here?</div>
        <div style='margin-bottom:10px'>{grade_badge(grade)}</div>
        <div style='font-size:15px;font-weight:700;color:{GRADE_COLORS[grade]};
        margin-bottom:18px;line-height:1.3'>{verdict}</div>
        <div style='font-size:10px;font-weight:600;color:#8A9BB0;text-transform:uppercase;
        letter-spacing:0.5px;margin-bottom:8px'>Strengths</div>
        {pros_html}
        <div style='font-size:10px;font-weight:600;color:#8A9BB0;text-transform:uppercase;
        letter-spacing:0.5px;margin:14px 0 8px'>Watch Points</div>
        {cons_html}
    </div>"""
    col_invest.markdown(invest_html, unsafe_allow_html=True)
except Exception as e:
    col_invest.warning(f"Investment panel unavailable: {e}")
