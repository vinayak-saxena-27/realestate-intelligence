import pandas as pd
import streamlit as st

from config import COLORS, GRADE_COLORS, GRADE_LABEL_MAP


def inject_css() -> None:
    """Inject shared CSS into the current Streamlit page."""
    st.markdown(f"""
    <style>
    /* ── KPI Cards ─────────────────────────────────────── */
    .kpi-card {{
        background: {COLORS['navy']};
        border-radius: 10px;
        padding: 20px 16px;
        text-align: center;
        margin: 4px 0;
    }}
    .kpi-label {{
        font-size: 11px;
        color: rgba(255,255,255,0.75);
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 8px;
    }}
    .kpi-value {{
        font-size: 22px;
        font-weight: bold;
        color: {COLORS['gold']};
    }}
    .kpi-delta {{
        font-size: 11px;
        color: rgba(255,255,255,0.6);
        margin-top: 4px;
    }}

    /* ── Opportunity Cards ─────────────────────────────── */
    .opp-card {{
        background: {COLORS['light_blue']};
        border-left: 4px solid {COLORS['navy']};
        border-radius: 8px;
        padding: 18px 16px;
        height: 100%;
        box-sizing: border-box;
    }}
    .opp-card a {{
        color: {COLORS['navy']};
        font-weight: bold;
        text-decoration: none;
    }}
    .opp-card a:hover {{
        text-decoration: underline;
    }}

    /* ── HTML Tables ───────────────────────────────────── */
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }}
    th {{
        background: {COLORS['navy']};
        color: white;
        padding: 8px 12px;
        text-align: left;
    }}
    td {{
        padding: 8px 12px;
        border-bottom: 1px solid {COLORS['light_blue']};
    }}
    tr:hover td {{
        background: {COLORS['light_blue']};
    }}
    </style>
    """, unsafe_allow_html=True)


def grade_badge(grade: str) -> str:
    color = GRADE_COLORS.get(grade, COLORS["navy"])
    label = GRADE_LABEL_MAP.get(grade, grade)
    return (
        f'<span style="background:{color};color:white;padding:2px 10px;'
        f'border-radius:12px;font-size:12px;font-weight:bold">{grade} — {label}</span>'
    )


def load_page_data() -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    if "df" not in st.session_state or st.session_state["df"] is None:
        st.warning("No data loaded — please navigate to the home page first.")
        st.stop()
    df: pd.DataFrame = st.session_state["df"]
    pop_stats: dict  = st.session_state["pop_stats"]
    if df.empty:
        st.warning("No data available — check your data source.")
        st.stop()
    latest = df[df["month"] == df["month"].max()]
    return df, pop_stats, latest
