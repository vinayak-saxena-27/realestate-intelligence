import pandas as pd
import streamlit as st

from config import COLORS, GRADE_COLORS, GRADE_LABEL_MAP


def inject_css() -> None:
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* ── Global ─────────────────────────────────────────── */
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }}
    .stDeployButton {{ display: none !important; }}
    footer {{ visibility: hidden !important; }}
    #MainMenu {{ visibility: hidden !important; }}
    .stApp {{ background-color: #F4F7FA; }}
    .block-container {{ padding-top: 1.75rem; padding-bottom: 2rem; }}
    hr {{ border-color: #E2E8F0 !important; margin: 1.25rem 0 !important; }}
    h1 {{
        font-weight: 800 !important;
        color: {COLORS['navy']} !important;
        letter-spacing: -0.5px !important;
        margin-bottom: 0.2rem !important;
    }}
    h2, h3 {{
        font-weight: 700 !important;
        color: {COLORS['navy']} !important;
        letter-spacing: -0.2px !important;
    }}

    /* ── Custom scrollbar ──────────────────────────────────── */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: #F4F7FA; }}
    ::-webkit-scrollbar-thumb {{ background: #C5D3E0; border-radius: 10px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: #8A9BB0; }}

    /* ── Sidebar title (injected above nav via ::before) ────── */
    [data-testid="stSidebarNav"]::before {{
        content: "🏠  RE Intelligence";
        display: block;
        padding: 22px 20px 14px;
        font-size: 18px;
        font-weight: 800;
        color: #EBF4FF;
        letter-spacing: -0.3px;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        border-bottom: 1px solid #1E3A56;
        margin-bottom: 8px;
    }}

    /* ── Sidebar ─────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background-color: #0D1F33 !important;
        border-right: 1px solid #162E48;
    }}
    [data-testid="stSidebar"] * {{ color: #C5D3E0 !important; }}
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {{ color: #EBF4FF !important; }}
    [data-testid="stSidebarNavItems"] a {{
        color: #A0AFC0 !important;
        border-radius: 8px !important;
        padding: 6px 12px !important;
        margin: 2px 0 !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        transition: background 0.15s, color 0.15s !important;
        display: block !important;
    }}
    [data-testid="stSidebarNavItems"] a:hover {{
        background: rgba(255,255,255,0.07) !important;
        color: #EBF4FF !important;
    }}
    [data-testid="stSidebarNavItems"] [aria-selected="true"] a {{
        background: rgba(201,168,76,0.18) !important;
        color: {COLORS['gold']} !important;
        font-weight: 600 !important;
    }}

    /* ── Buttons ─────────────────────────────────────────── */
    [data-testid="stBaseButton-primary"],
    button[data-testid="baseButton-primary"],
    [data-testid="stButton"] > button[kind="primary"] {{
        background: {COLORS['navy']} !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 13.5px !important;
        letter-spacing: 0.2px !important;
        padding: 0.45rem 1.25rem !important;
        transition: background 0.18s ease, transform 0.12s ease, box-shadow 0.18s ease !important;
        box-shadow: 0 2px 8px rgba(27,58,92,0.20) !important;
    }}
    [data-testid="stBaseButton-primary"]:hover,
    button[data-testid="baseButton-primary"]:hover,
    [data-testid="stButton"] > button[kind="primary"]:hover {{
        background: {COLORS['gold']} !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(27,58,92,0.25) !important;
    }}
    [data-testid="stBaseButton-secondary"],
    button[data-testid="baseButton-secondary"],
    [data-testid="stButton"] > button[kind="secondary"] {{
        background: white !important;
        color: {COLORS['navy']} !important;
        border: 1.5px solid #DDE4EE !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 13.5px !important;
        padding: 0.45rem 1.25rem !important;
        transition: border-color 0.15s, background 0.15s, transform 0.12s !important;
    }}
    [data-testid="stBaseButton-secondary"]:hover,
    button[data-testid="baseButton-secondary"]:hover,
    [data-testid="stButton"] > button[kind="secondary"]:hover {{
        border-color: {COLORS['navy']} !important;
        background: #F4F7FA !important;
        transform: translateY(-1px) !important;
    }}

    /* ── Selectbox ──────────────────────────────────────────── */
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child {{
        background: white !important;
        border: 1.5px solid #DDE4EE !important;
        border-radius: 8px !important;
        transition: border-color 0.15s !important;
    }}
    [data-testid="stSelectbox"] [data-baseweb="select"] > div:hover {{
        border-color: {COLORS['navy']} !important;
    }}
    [data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within {{
        border-color: {COLORS['navy']} !important;
        box-shadow: 0 0 0 3px rgba(27,58,92,0.10) !important;
    }}

    /* ── Multiselect ────────────────────────────────────────── */
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div:first-child {{
        background: white !important;
        border: 1.5px solid #DDE4EE !important;
        border-radius: 8px !important;
        transition: border-color 0.15s !important;
    }}
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div:hover {{
        border-color: {COLORS['navy']} !important;
    }}
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div:focus-within {{
        border-color: {COLORS['navy']} !important;
        box-shadow: 0 0 0 3px rgba(27,58,92,0.10) !important;
    }}
    [data-testid="stMultiSelect"] span[data-baseweb="tag"] {{
        background: rgba(27,58,92,0.10) !important;
        border-radius: 6px !important;
        border-color: transparent !important;
    }}
    [data-testid="stMultiSelect"] span[data-baseweb="tag"] span:first-child {{
        color: {COLORS['navy']} !important;
        font-weight: 600 !important;
        font-size: 12px !important;
    }}

    /* ── Dropdown option list ───────────────────────────────── */
    [data-baseweb="menu"] [role="option"]:hover {{
        background: #F0F6FF !important;
    }}
    [data-baseweb="menu"] [aria-selected="true"] {{
        background: rgba(27,58,92,0.08) !important;
    }}

    /* ── st.metric widget ─────────────────────────────────── */
    [data-testid="metric-container"] {{
        background: white !important;
        border: 1px solid #DDE4EE !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: 0 1px 3px rgba(27,58,92,0.06), 0 4px 12px rgba(27,58,92,0.03) !important;
    }}
    [data-testid="stMetricLabel"] p {{
        font-size: 10.5px !important;
        font-weight: 600 !important;
        color: #8A9BB0 !important;
        text-transform: uppercase;
        letter-spacing: 0.7px;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 22px !important;
        font-weight: 800 !important;
        color: {COLORS['navy']} !important;
        letter-spacing: -0.3px;
    }}
    [data-testid="stMetricDelta"] {{ font-size: 12px !important; }}

    /* ── st.caption ────────────────────────────────────────── */
    [data-testid="stCaptionContainer"] p {{
        color: #8A9BB0 !important;
        font-size: 13px !important;
        font-style: normal !important;
    }}

    /* ── Alerts ─────────────────────────────────────────────── */
    [data-testid="stAlert"] {{
        border-radius: 10px !important;
        padding: 12px 16px !important;
        font-size: 13.5px !important;
        border-left-width: 4px !important;
    }}

    /* ── KPI Cards ─────────────────────────────────────────── */
    .kpi-card {{
        background: white;
        border: 1px solid #DDE4EE;
        border-radius: 12px;
        padding: 18px 22px 16px;
        box-shadow: 0 1px 3px rgba(27,58,92,0.06), 0 4px 12px rgba(27,58,92,0.03);
        position: relative;
        overflow: hidden;
        height: 100%;
        box-sizing: border-box;
        transition: transform 0.16s ease, box-shadow 0.16s ease;
    }}
    .kpi-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 8px 28px rgba(27,58,92,0.12), 0 2px 8px rgba(27,58,92,0.06) !important;
    }}
    .kpi-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, {COLORS['navy']}, {COLORS['gold']});
    }}
    .kpi-label {{
        font-size: 10.5px;
        font-weight: 600;
        color: #8A9BB0;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 6px;
    }}
    .kpi-value {{
        font-size: 26px;
        font-weight: 800;
        color: {COLORS['navy']};
        letter-spacing: -0.5px;
        line-height: 1.15;
        margin: 0;
    }}
    .kpi-delta {{
        font-size: 11.5px;
        font-weight: 500;
        color: {COLORS['green']};
        margin-top: 5px;
    }}

    /* ── Grade Badges ─────────────────────────────────────── */
    .grade-badge {{
        display: inline-flex;
        align-items: center;
        padding: 3px 10px;
        border-radius: 100px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.3px;
        color: white;
    }}

    /* ── Opportunity Cards ─────────────────────────────────── */
    .opp-card {{
        background: white;
        border: 1px solid #DDE4EE;
        border-radius: 12px;
        padding: 22px 24px 20px;
        box-shadow: 0 1px 3px rgba(27,58,92,0.06), 0 4px 12px rgba(27,58,92,0.03);
        height: 100%;
        box-sizing: border-box;
        transition: transform 0.16s ease, box-shadow 0.16s ease;
    }}
    .opp-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 8px 28px rgba(27,58,92,0.12), 0 2px 8px rgba(27,58,92,0.06) !important;
    }}
    .opp-card a {{
        display: inline-block;
        color: {COLORS['navy']};
        font-size: 12.5px;
        font-weight: 600;
        text-decoration: none;
        border-bottom: 1.5px solid {COLORS['gold']};
        padding-bottom: 1px;
    }}
    .opp-card a:hover {{
        color: {COLORS['gold']};
        border-bottom-color: transparent;
    }}

    /* ── Section subheadings (gold accent) ────────────────────── */
    h3 {{
        border-left: 3px solid {COLORS['gold']} !important;
        padding-left: 10px !important;
        margin-top: 0.25rem !important;
    }}

    /* ── Table wrapper card ─────────────────────────────────── */
    .table-wrapper {{
        border: 1px solid #DDE4EE;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(27,58,92,0.06), 0 4px 12px rgba(27,58,92,0.03);
    }}
    .table-wrapper table {{ border: none; }}

    /* ── HTML Tables ───────────────────────────────────────── */
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }}
    th {{
        background: {COLORS['navy']};
        color: rgba(255,255,255,0.88);
        padding: 10px 14px;
        text-align: left;
        font-size: 10.5px;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        border: none;
    }}
    th.num {{ text-align: right; }}
    td {{
        padding: 10px 14px;
        border-bottom: 1px solid #EEF2F7;
        color: #2D3748;
    }}
    td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    tr:nth-child(even) td {{ background: #F8FAFC; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: #F0F6FF !important; }}
    </style>
    """, unsafe_allow_html=True)


def page_subtitle(text: str) -> None:
    st.markdown(
        f"<p style='color:#8A9BB0;font-size:13.5px;margin-top:-8px;margin-bottom:1rem'>{text}</p>",
        unsafe_allow_html=True,
    )


def table_card(html: str) -> str:
    """Wraps raw table HTML in a styled card container with border and shadow."""
    return f'<div class="table-wrapper">{html}</div>'


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
