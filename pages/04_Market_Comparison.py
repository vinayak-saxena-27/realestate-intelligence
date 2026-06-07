import plotly.graph_objects as go
import streamlit as st

from _styles import grade_badge, inject_css, load_page_data
from config import APP_ICON, CHART_COLORS, PAGE_TITLES
from data_loader import get_price_history_df

st.set_page_config(page_title="Market Comparison", page_icon=APP_ICON, layout="wide")
inject_css()

df, pop_stats, latest = load_page_data()

st.header("Market Comparison")

# ── Zip selector ──────────────────────────────────────────────────────────────
zip_info   = latest.set_index("zip_code")[["metro", "investment_score"]].to_dict("index")
sorted_zips = latest.sort_values("investment_score", ascending=False)["zip_code"].tolist()

selected = st.multiselect(
    "Select up to 4 zip codes to compare",
    options=sorted_zips,
    default=sorted_zips[:2],
    max_selections=4,
    format_func=lambda z: f"{z} ({zip_info[z]['metro']}, Score: {zip_info[z]['investment_score']:.1f})",
)

if len(selected) < 2:
    st.warning("Select at least 2 zip codes to compare.")
    st.stop()

comp_latest = latest[latest["zip_code"].isin(selected)].set_index("zip_code").loc[selected]

# ── Comparison table ──────────────────────────────────────────────────────────

def _fmt(col: str, v: float) -> str:
    if col in ("median_sale_price", "predicted_price_6m"):
        return f"${v:,.0f}"
    if col in ("yoy_appreciation", "gross_rental_yield"):
        return f"{v:.1f}%"
    if col == "days_on_market":
        return f"{int(v)} days"
    if col in ("market_heat_index", "neighborhood_score"):
        return f"{v:.1f} / 100"
    return f"{v:.1f}"


def build_comparison_table(rows_df) -> str:
    metrics = [
        ("Investment Score",   "investment_score",   "higher"),
        ("Median Sale Price",  "median_sale_price",  "lower"),
        ("YoY Appreciation",   "yoy_appreciation",   "higher"),
        ("Gross Rental Yield", "gross_rental_yield", "higher"),
        ("Days on Market",     "days_on_market",     "lower"),
        ("Market Heat",        "market_heat_index",  "higher"),
        ("Neighbourhood",      "neighborhood_score", "higher"),
        ("6M Forecast",        "predicted_price_6m", "higher"),
    ]

    zip_codes = rows_df.index.tolist()
    header_cells = "".join(
        f"<th>{z}<br><small style='font-weight:normal'>{zip_info[z]['metro']}</small></th>"
        for z in zip_codes
    )
    header_row = f"<tr><th>Metric</th>{header_cells}</tr>"

    # Grade row (non-numeric, badge rendering)
    grade_cells = "".join(
        f"<td style='padding:6px 10px'>{grade_badge(rows_df.loc[z, 'investment_grade'])}</td>"
        for z in zip_codes
    )
    grade_row = f"<tr><td><b>Grade</b></td>{grade_cells}</tr>"

    # Segment row (text, no highlight)
    seg_cells = "".join(
        f"<td style='padding:6px 10px'>{rows_df.loc[z, 'market_segment']}</td>"
        for z in zip_codes
    )
    seg_row = f"<tr><td><b>Market Segment</b></td>{seg_cells}</tr>"

    metric_rows = [grade_row]
    for label, col, direction in metrics:
        vals   = rows_df[col].values
        best   = vals.max() if direction == "higher" else vals.min()
        cells  = ""
        for z in zip_codes:
            v  = rows_df.loc[z, col]
            bg = "#E8F5EE" if v == best else "white"
            cells += f"<td style='background:{bg};padding:6px 10px'>{_fmt(col, v)}</td>"
        metric_rows.append(f"<tr><td><b>{label}</b></td>{cells}</tr>")

    metric_rows.append(seg_row)
    rows_html = "".join(metric_rows)
    return f"<table>{header_row}{rows_html}</table>"


st.subheader("Side-by-Side Metrics")
st.markdown(build_comparison_table(comp_latest), unsafe_allow_html=True)

st.divider()

# ── Overlaid price history chart ──────────────────────────────────────────────

def create_comparison_chart(selected_zips) -> go.Figure:
    fig = go.Figure()
    for i, zip_code in enumerate(selected_zips):
        hist  = get_price_history_df(df, zip_code)
        metro = zip_info[zip_code]["metro"]
        fig.add_trace(go.Scatter(
            x=hist["month"],
            y=hist["median_sale_price"],
            name=f"{zip_code} ({metro})",
            line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=2),
        ))
    fig.update_layout(
        title="24-Month Price History Comparison",
        yaxis=dict(tickprefix="$", tickformat=","),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=60),
    )
    return fig


st.subheader("Price History")
st.plotly_chart(create_comparison_chart(selected), use_container_width=True)
