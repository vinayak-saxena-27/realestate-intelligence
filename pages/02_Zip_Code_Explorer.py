import pandas as pd
import streamlit as st

from _styles import grade_badge, inject_css, load_page_data, table_card
from config import COLORS, GRADE_LABEL_MAP, PAGE_TITLES

inject_css()
st.title(PAGE_TITLES["explorer"])

df, pop_stats, latest = load_page_data()

# ── Helpers ───────────────────────────────────────────────────────────────────


def colored_pct(value: float, median: float) -> str:
    color = COLORS["green"] if value > median else COLORS["red"]
    return f'<span style="color:{color}">{value:.1f}%</span>'


def build_table_html(rows: pd.DataFrame, pop_stats: dict) -> str:
    headers = [
        ("Zip Code",       False),
        ("Metro",          False),
        ("Score",          True),
        ("Grade",          False),
        ("Median Price",   True),
        ("YoY Appr %",     True),
        ("Gross Yield %",  True),
        ("Market Segment", False),
        ("Days on Mkt",    True),
    ]
    th_cells = "".join(
        f'<th class="num">{h}</th>' if is_num else f"<th>{h}</th>"
        for h, is_num in headers
    )
    row_htmls = []
    for _, r in rows.iterrows():
        row_htmls.append(
            f"<tr>"
            f"<td>{r['zip_code']}</td>"
            f"<td>{r['metro']}</td>"
            f'<td class="num">{r["investment_score"]:.1f}</td>'
            f"<td>{grade_badge(r['investment_grade'])}</td>"
            f'<td class="num">${r["median_sale_price"]:,.0f}</td>'
            f'<td class="num">{colored_pct(r["yoy_appreciation"],  pop_stats["median_yoy_appreciation"])}</td>'
            f'<td class="num">{colored_pct(r["gross_rental_yield"], pop_stats["median_gross_rental_yield"])}</td>'
            f"<td>{r['market_segment']}</td>"
            f'<td class="num">{int(r["days_on_market"])}</td>'
            f"</tr>"
        )
    return f"<table><tr>{th_cells}</tr>{''.join(row_htmls)}</table>"


# ── Sidebar filters ───────────────────────────────────────────────────────────
st.sidebar.header("Filters")

# Metro
all_metros = sorted(latest["metro"].unique())
metros = st.sidebar.multiselect("Metro", options=all_metros, default=all_metros)
eff_metros = metros if metros else all_metros

# Grade — full labels for clarity
grades = st.sidebar.multiselect(
    "Investment Grade",
    options=["A", "B", "C", "D", "F"],
    default=["A", "B", "C", "D", "F"],
    format_func=lambda g: f"{g} — {GRADE_LABEL_MAP[g]}",
)
eff_grades = grades if grades else ["A", "B", "C", "D", "F"]

# Price range — display in $K so the slider labels are readable
price_lo_k = int(latest["median_sale_price"].min()) // 1000
price_hi_k = (int(latest["median_sale_price"].max()) // 1000) + 1
price_range_k = st.sidebar.slider(
    "Price Range",
    min_value=price_lo_k,
    max_value=price_hi_k,
    value=(price_lo_k, price_hi_k),
    step=10,
    format="$%dK",
)
price_range = (price_range_k[0] * 1000, price_range_k[1] * 1000)

# Investment score range
score_range = st.sidebar.slider("Investment Score", 0, 100, (0, 100))

# Market Segment
all_segments = sorted(latest["market_segment"].dropna().unique().tolist())
segments = st.sidebar.multiselect(
    "Market Segment", options=all_segments, default=all_segments
)
eff_segments = segments if segments else all_segments

# Sort By
_SORT_OPTIONS: dict[str, tuple[str, bool]] = {
    "Investment Score ↓":       ("investment_score",   False),
    "YoY Appreciation ↓":       ("yoy_appreciation",   False),
    "Gross Yield ↓":            ("gross_rental_yield", False),
    "Price ↑ (cheapest first)": ("median_sale_price",  True),
    "Days on Market ↑":         ("days_on_market",     True),
}
sort_label = st.sidebar.selectbox("Sort By", options=list(_SORT_OPTIONS.keys()))
sort_col, sort_asc = _SORT_OPTIONS[sort_label]

# ── Apply filters ─────────────────────────────────────────────────────────────
filtered = latest[
    latest["metro"].isin(eff_metros) &
    latest["investment_grade"].isin(eff_grades) &
    latest["median_sale_price"].between(*price_range) &
    latest["investment_score"].between(*score_range) &
    latest["market_segment"].isin(eff_segments)
]

# ── Zero-result guard ─────────────────────────────────────────────────────────
if filtered.empty:
    st.warning("No zip codes match your filters. Try widening the filters.")
    st.stop()

st.caption(
    f"Showing **{len(filtered)}** of **{len(latest)}** zip codes — "
    f"sorted by {sort_label}"
)

# ── Results table ─────────────────────────────────────────────────────────────
try:
    sorted_filtered = filtered.sort_values(sort_col, ascending=sort_asc)
    st.markdown(table_card(build_table_html(sorted_filtered, pop_stats)), unsafe_allow_html=True)
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
