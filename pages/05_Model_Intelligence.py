import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _styles import inject_css, load_page_data
from charts import style_figure
from config import (
    APP_ICON,
    APP_METHODOLOGY_TEXT,
    CHART_COLORS,
    COLORS,
    INVESTMENT_SCORE_WEIGHTS,
    RF_FEATURES,
)

inject_css()

df, pop_stats, latest = load_page_data()

st.header("Model Intelligence")
st.caption("How the price forecast model and investment score work under the hood.")

st.divider()

# ── 1. Model Performance Table ────────────────────────────────────────────────
st.subheader("Price Forecast Model Performance")

metrics = st.session_state.get("price_metrics", {})
if not metrics:
    st.warning("Model metrics not available — ensure app.py ran train_price_model().")
else:
    perf_data = {
        "Metric": ["Model Type", "Training Rows", "Test Rows", "RMSE", "R-Squared", "Features"],
        "Value": [
            "Random Forest Regressor",
            metrics["train_rows"],
            metrics["test_rows"],
            f"${metrics['rmse']:,.0f}",
            f"{metrics['r2']:.3f}",
            len(RF_FEATURES),
        ],
        "Notes": [
            "n_estimators=100, random_state=42",
            "80% of data by time order",
            "20% of data — never seen during training",
            "Average $ prediction error on test set",
            "Proportion of price variance explained",
            "Appreciation, velocity, heat, neighbourhood, yield",
        ],
    }
    st.dataframe(pd.DataFrame(perf_data), use_container_width=True, hide_index=True)

st.divider()

# ── 2. Feature Importance Chart ───────────────────────────────────────────────
st.subheader("Feature Importance — Price Forecast Model")

importances = st.session_state.get("price_importances", {})
if not importances:
    st.warning("Feature importances not available — ensure app.py ran train_price_model().")
else:
    imp_df = (
        pd.Series(importances)
        .sort_values(ascending=True)   # ascending so largest value renders at top in horizontal bar
        .reset_index()
    )
    imp_df.columns = ["Feature", "Importance"]

    fig = go.Figure(go.Bar(
        x=imp_df["Importance"],
        y=imp_df["Feature"],
        orientation="h",
        marker_color=COLORS["navy"],
        hovertemplate="%{y}: %{x:.3f}<extra></extra>",
    ))
    style_figure(fig, margin=dict(l=160, t=40, b=20, r=20))
    fig.update_xaxes(title_text="Importance Score")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── 3. Investment Score Weight Pie ────────────────────────────────────────────
st.subheader("Investment Score Weight Distribution")

try:
    assert abs(sum(INVESTMENT_SCORE_WEIGHTS.values()) - 1.0) < 1e-9, \
        "INVESTMENT_SCORE_WEIGHTS must sum to 1.0"

    labels = [k.replace("_", " ").title() for k in INVESTMENT_SCORE_WEIGHTS.keys()]
    values = list(INVESTMENT_SCORE_WEIGHTS.values())

    fig_pie = go.Figure(go.Pie(
        labels=labels,
        values=values,
        marker_colors=CHART_COLORS,
        hole=0.3,
        hovertemplate="%{label}: %{percent}<extra></extra>",
    ))
    style_figure(fig_pie, title=dict(text="Investment Score Weight Distribution", font=dict(size=14)))
    st.plotly_chart(fig_pie, use_container_width=True)
except Exception as e:
    st.error(f"Score weight chart failed to render: {e}")

st.divider()

# ── 4. Plain-English Methodology ──────────────────────────────────────────────
st.markdown("### How This Works")
st.markdown(APP_METHODOLOGY_TEXT.format(
    n_zips=latest["zip_code"].nunique(),
    n_metros=latest["metro"].nunique(),
))
