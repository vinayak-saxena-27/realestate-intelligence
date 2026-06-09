import pandas as pd
import streamlit as st

from _styles import grade_badge, inject_css, load_page_data
from config import COLORS, PAGE_TITLES

inject_css()
st.title(PAGE_TITLES["explorer"])

df, pop_stats, latest = load_page_data()

# ── Helpers ───────────────────────────────────────────────────────────────────


def colored_pct(value: float, median: float) -> str:
    color = COLORS["green"] if value > median else COLORS["red"]
    return f'<span style="color:{color}">{value:.1f}%</span>'


def build_table_html(rows: pd.DataFrame, pop_stats: dict) -> str:
    headers = [
        "Zip Code", "Metro", "Score", "Grade", "Median Price",
        "YoY Appr %", "Gross Yield %", "Market Segment", "Days on Market",
    ]
    th_cells = "".join(f"<th>{h}</th>" for h in headers)
    row_htmls = []
    for _, r in rows.iterrows():
        row_htmls.append(
            f"<tr>"
            f"<td>{r['zip_code']}</td>"
            f"<td>{r['metro']}</td>"
            f"<td>{r['investment_score']:.1f}</td>"
            f"<td>{grade_badge(r['investment_grade'])}</td>"
            f"<td>${r['median_sale_price']:,.0f}</td>"
            f"<td>{colored_pct(r['yoy_appreciation'],  pop_stats['median_yoy_appreciation'])}</td>"
            f"<td>{colored_pct(r['gross_rental_yield'], pop_stats['median_gross_rental_yield'])}</td>"
            f"<td>{r['market_segment']}</td>"
            f"<td>{int(r['days_on_market'])}</td>"
            f"</tr>"
        )
    return f"<table><tr>{th_cells}</tr>{''.join(row_htmls)}</table>"


# ── Sidebar filters ───────────────────────────────────────────────────────────
st.sidebar.header("Filters")

all_metros  = sorted(latest["metro"].unique())
metros      = st.sidebar.multiselect("Metro", options=all_metros, default=all_metros)
eff_metros  = metros if metros else all_metros

grades      = st.sidebar.multiselect("Grade", options=["A", "B", "C", "D", "F"], default=["A", "B", "C", "D", "F"])
eff_grades  = grades if grades else ["A", "B", "C", "D", "F"]

price_min   = int(latest["median_sale_price"].min())
price_max   = int(latest["median_sale_price"].max())
price_range = st.sidebar.slider(
    "Price Range", price_min, price_max, (price_min, price_max),
    step=10_000, format="$%d",
)

# ── Apply filters ─────────────────────────────────────────────────────────────
filtered = latest[
    latest["metro"].isin(eff_metros) &
    latest["investment_grade"].isin(eff_grades) &
    latest["median_sale_price"].between(*price_range)
]

# ── Zero-result guard ─────────────────────────────────────────────────────────
if filtered.empty:
    st.warning("No zip codes match your filters. Try widening the price range or selecting more grades.")
    st.stop()

st.caption(f"Showing {len(filtered)} of {len(latest)} zip codes — sorted by Investment Score")

# ── Results table ─────────────────────────────────────────────────────────────
try:
    sorted_filtered = filtered.sort_values("investment_score", ascending=False)
    st.markdown(build_table_html(sorted_filtered, pop_stats), unsafe_allow_html=True)
except Exception as e:
    st.error(f"Table rendering failed: {e}")

st.divider()

# ── CSV download ──────────────────────────────────────────────────────────────
csv_data = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    label=f"Download {len(filtered)} Zip Codes as CSV",
    data=csv_data,
    file_name="realestate_filtered.csv",
    mime="text/csv",
)
