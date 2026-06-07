import pandas as pd
import streamlit as st

from config import COLORS, GRADE_COLORS, GRADE_LABEL_MAP


def inject_css() -> None:
    """Inject shared CSS into the current Streamlit page."""
    st.markdown(f"""
    <style>
    /* ── Global ────────────────────────────────────────── */
    .stDeployButton {{ display: none !important; }}
    .block-container {{ padding-top: 1.5rem; }}
    [data-testid='stMetricDelta'] {{ font-size: 12px; }}

    /* ── KPI Cards ─────────────────────────────────────── */
    .kpi-card {{
        background: white;
        border: 1px solid #E0E7EF;
        border-top: 4px solid {COLORS['gold']};
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(27,58,92,0.08);
        text-align: center;
    }}
    .kpi-label {{
        font-size: 12px;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .kpi-value {{
        font-size: 26px;
        font-weight: 700;
        color: {COLORS['navy']};
        margin: 4px 0;
    }}
    .kpi-delta {{
        font-size: 12px;
        color: {COLORS['green']};
    }}

    /* ── Grade Badge Pills ─────────────────────────────── */
    .grade-badge {{
        display: inline-block;
        padding: 3px 12px;
        border-radius: 14px;
        font-size: 12px;
        font-weight: 700;
        color: white;
    }}

    /* ── Opportunity Cards ─────────────────────────────── */
    .opp-card {{
        background: white;
        border: 1px solid #E0E7EF;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(27,58,92,0.08);
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
