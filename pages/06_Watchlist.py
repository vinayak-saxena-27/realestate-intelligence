import pandas as pd
import streamlit as st

from _styles import grade_badge, inject_css, load_page_data, page_subtitle, table_card
from config import COLORS
from watchlist import add_zip, load_watchlist, remove_zip

inject_css()
st.title("Watchlist")
page_subtitle("Zip codes you're tracking — aggregate metrics update live with your data")

df, pop_stats, latest = load_page_data()

watchlist = load_watchlist()
valid = [z for z in watchlist if z in latest["zip_code"].values]

if not valid:
    st.info(
        "Your watchlist is empty. "
        "Add zip codes from the **Zip Code Deep Dive** page using the Add to Watchlist button."
    )
    # Still show the Add section so users can build it from scratch here too
else:
    wl_df = latest[latest["zip_code"].isin(valid)].copy()

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    def kpi_card(label: str, value: str, delta: str = "") -> str:
        delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else ""
        return f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {delta_html}
        </div>"""

    top_row = wl_df.sort_values("investment_score", ascending=False).iloc[0]
    kpis = [
        ("Watchlisted Zips",     str(len(wl_df)),                                  ""),
        ("Avg Investment Score", f"{wl_df['investment_score'].mean():.1f}",         ""),
        ("Blended Gross Yield",  f"{wl_df['gross_rental_yield'].mean():.1f}%",      ""),
        ("Avg Appreciation",     f"{wl_df['yoy_appreciation'].mean():.1f}%",        ""),
        ("Top Pick",             top_row["zip_code"],                               f"Score {top_row['investment_score']:.1f}"),
    ]
    cols = st.columns(5)
    for col, (label, value, delta) in zip(cols, kpis):
        col.markdown(kpi_card(label, value, delta), unsafe_allow_html=True)

    st.divider()

    # ── Watchlist Table ────────────────────────────────────────────────────────
    st.subheader("Watchlisted Zip Codes")

    def build_wl_table(rows: pd.DataFrame) -> str:
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
                f'<td class="num">{r["yoy_appreciation"]:.1f}%</td>'
                f'<td class="num">{r["gross_rental_yield"]:.1f}%</td>'
                f"<td>{r['market_segment']}</td>"
                f'<td class="num">{int(r["days_on_market"])}</td>'
                f"</tr>"
            )
        return f"<table><tr>{th_cells}</tr>{''.join(row_htmls)}</table>"

    tbl = wl_df.sort_values("investment_score", ascending=False)
    st.markdown(table_card(build_wl_table(tbl)), unsafe_allow_html=True)

    st.divider()

    # ── Remove zips ────────────────────────────────────────────────────────────
    st.subheader("Manage Watchlist")
    zip_info_lookup = latest.set_index("zip_code")["metro"].to_dict()
    to_remove = st.multiselect(
        "Select zip codes to remove",
        options=valid,
        format_func=lambda z: f"{z}  ({zip_info_lookup.get(z, '')})",
    )
    if st.button("Remove Selected", disabled=not to_remove, type="secondary"):
        for z in to_remove:
            remove_zip(z)
        st.rerun()

    st.divider()

# ── Add zips ───────────────────────────────────────────────────────────────────
st.subheader("Add Zip Codes")
already_watching = set(valid if valid else [])
zip_info_lookup = latest.set_index("zip_code")[["metro", "investment_score"]].to_dict("index")
available = [z for z in latest["zip_code"].tolist() if z not in already_watching]

to_add = st.multiselect(
    "Search and add zip codes to your watchlist",
    options=available,
    format_func=lambda z: (
        f"{z} — {zip_info_lookup[z]['metro']} (Score: {zip_info_lookup[z]['investment_score']:.1f})"
    ),
)
if st.button("Add to Watchlist", disabled=not to_add, type="primary"):
    for z in to_add:
        add_zip(z)
    st.rerun()
