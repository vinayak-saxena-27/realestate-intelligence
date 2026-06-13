import streamlit as st

from _styles import grade_badge, inject_css, load_page_data, page_subtitle
from charts import create_price_history, create_score_components
from config import COLORS, GRADE_COLORS, KMEANS_FEATURES, PAGE_TITLES, SEGMENT_LABELS
from narrative import generate_investment_narrative, get_key_pros_cons
from report import generate_html_report
from watchlist import add_zip, load_watchlist, remove_zip

inject_css()
st.title(PAGE_TITLES["deep_dive"])
page_subtitle("Full metric breakdown, price history, and AI-generated investment narrative")

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

# ── Watchlist toggle ──────────────────────────────────────────────────────────
_wl = load_watchlist()
_in_wl = selected_zip in _wl
if st.button(
    "✓ In Watchlist — Remove" if _in_wl else "☆ Add to Watchlist",
    type="secondary" if _in_wl else "primary",
):
    remove_zip(selected_zip) if _in_wl else add_zip(selected_zip)
    st.rerun()

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

st.divider()

# ── Export Report ──────────────────────────────────────────────────────────────
st.subheader("Export Report")
try:
    _narrative   = generate_investment_narrative(row, pop_stats)
    _pros, _cons = get_key_pros_cons(row, pop_stats)
    _report_html = generate_html_report(row, pop_stats, _pros, _cons, _narrative)
    col_btn, col_hint = st.columns([1, 3])
    col_btn.download_button(
        label="Download Report",
        data=_report_html.encode("utf-8"),
        file_name=f"investment_report_{selected_zip}.html",
        mime="text/html",
        type="primary",
        use_container_width=True,
    )
    col_hint.caption(
        "Downloads a self-contained HTML report for this zip code. "
        "Open in any browser and use **File → Print → Save as PDF** to export as PDF."
    )
except Exception as e:
    st.warning(f"Report generation failed: {e}")

st.divider()

# ── Similar Markets ───────────────────────────────────────────────────────────

def _find_similar(anchor, pool, n: int = 4):
    """Return the n nearest zip codes in the same K-Means segment by Euclidean distance."""
    same = pool[
        (pool["market_segment"] == anchor["market_segment"]) &
        (pool["zip_code"] != anchor["zip_code"])
    ].copy()
    if same.empty:
        return same
    a_vals = anchor[KMEANS_FEATURES].values.astype(float)
    dists = ((same[KMEANS_FEATURES].values.astype(float) - a_vals) ** 2).sum(axis=1) ** 0.5
    same["_dist"] = dists
    return same.nsmallest(n, "_dist").drop(columns=["_dist"])


st.subheader("Similar Markets")
st.caption(
    f"Nearest zip codes by market profile within the **{row['market_segment']}** segment"
)

try:
    similar = _find_similar(row, latest)
    if similar.empty:
        st.info("No other zip codes share this market segment in the current data.")
    else:
        sim_cols = st.columns(len(similar))
        for col, (_, sr) in zip(sim_cols, similar.iterrows()):
            mini = f"""
            <div style="background:white;border:1px solid #DDE4EE;border-radius:12px;
            padding:16px 18px;box-shadow:0 1px 3px rgba(27,58,92,0.06),0 4px 12px rgba(27,58,92,0.03);
            height:100%;box-sizing:border-box;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
                    <div>
                        <div style="font-size:17px;font-weight:800;color:{COLORS['navy']};
                        letter-spacing:-0.3px">{sr['zip_code']}</div>
                        <div style="font-size:11px;color:#8A9BB0;margin-top:1px">{sr['metro']}</div>
                    </div>
                    {grade_badge(sr['investment_grade'])}
                </div>
                <div style="font-size:22px;font-weight:800;color:{COLORS['gold']};
                letter-spacing:-0.5px">{sr['investment_score']:.1f}</div>
                <div style="font-size:10px;font-weight:600;color:#8A9BB0;text-transform:uppercase;
                letter-spacing:0.5px;margin-bottom:8px">Score</div>
                <div style="font-size:12px;color:#4A5568;margin-bottom:12px">
                    {sr['yoy_appreciation']:.1f}% appr · {sr['gross_rental_yield']:.1f}% yield
                </div>
                <a href="/Zip_Code_Deep_Dive?zip={sr['zip_code']}"
                style="font-size:12px;font-weight:600;color:{COLORS['navy']};text-decoration:none;
                border-bottom:1.5px solid {COLORS['gold']};padding-bottom:1px">View Analysis →</a>
            </div>"""
            col.markdown(mini, unsafe_allow_html=True)
except Exception as e:
    st.error(f"Similar markets section failed: {e}")
