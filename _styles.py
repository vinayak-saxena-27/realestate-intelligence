import streamlit as st

from config import COLORS


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
