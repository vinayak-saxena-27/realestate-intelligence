import pandas as pd
import plotly.graph_objects as go

from config import (
    COLORS,
    GRADE_COLORS,
    GRADE_THRESHOLDS,
    INVESTMENT_SCORE_WEIGHTS,
)
from data_loader import get_price_history_df

# ── Shared chart styling ───────────────────────────────────────────────────────
_FONT_STACK = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

_BASE_LAYOUT: dict = dict(
    font=dict(family=_FONT_STACK, size=12, color="#2D3748"),
    plot_bgcolor="white",
    paper_bgcolor="white",
    hoverlabel=dict(
        bgcolor=COLORS["navy"],
        font_size=12,
        font_family=_FONT_STACK,
        font_color="white",
        bordercolor=COLORS["navy"],
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
)

_AX: dict = dict(
    gridcolor="#EEF2F7",
    linecolor="#DDE4EE",
    zerolinecolor="#DDE4EE",
    tickfont=dict(size=11, color="#6B7A8D"),
)


def style_figure(fig: go.Figure, **extra) -> go.Figure:
    """Apply shared styling to any Plotly figure. Call after all traces are added."""
    fig.update_layout(**{**_BASE_LAYOUT, **extra})
    fig.update_xaxes(**_AX)
    fig.update_yaxes(**_AX)
    return fig

# ── Component column → human-readable label (derived from config weights) ─────
_COMPONENT_WEIGHT_KEY: dict[str, str] = {
    "score_appreciation": "appreciation",
    "score_yield":        "yield",
    "score_heat":         "heat",
    "score_neighborhood": "neighborhood",
    "score_velocity":     "velocity",
    "score_net_yield":    "net_yield",
}

_COMPONENT_DISPLAY_NAME: dict[str, str] = {
    "score_appreciation": "Appreciation",
    "score_yield":        "Yield",
    "score_heat":         "Market Heat",
    "score_neighborhood": "Neighbourhood",
    "score_velocity":     "Price Velocity",
    "score_net_yield":    "Net Yield",
}

COMPONENT_COLS: dict[str, str] = {
    col: f"{_COMPONENT_DISPLAY_NAME[col]} ({int(INVESTMENT_SCORE_WEIGHTS[key] * 100)}%)"
    for col, key in _COMPONENT_WEIGHT_KEY.items()
}


def create_grade_donut(df: pd.DataFrame) -> go.Figure:
    """Donut chart of investment grade distribution across unique zip codes (latest month)."""
    grade_order = ["A", "B", "C", "D", "F"]
    label_map = {g["letter"]: g["label"] for g in GRADE_THRESHOLDS}

    # One grade per zip — snapshot at latest month
    latest = df[df["month"] == df["month"].max()]
    counts = latest["investment_grade"].value_counts().reindex(grade_order, fill_value=0)
    labels = [f"{g} — {label_map[g]}" for g in grade_order]
    clrs   = [GRADE_COLORS[g] for g in grade_order]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=counts.values,
        hole=0.55,
        marker_colors=clrs,
        hovertemplate="%{label}<br>Count: %{value}<br>Share: %{percent}<extra></extra>",
        sort=False,
    ))
    fig.add_annotation(
        text=f"<b>{len(latest)}</b><br><span style='font-size:11px'>Zips</span>",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=18, color=COLORS["navy"], family=_FONT_STACK),
    )
    style_figure(
        fig,
        showlegend=True,
        margin=dict(t=20, b=60, l=20, r=20),
        legend=dict(
            orientation="h", yanchor="top", y=-0.02,
            xanchor="center", x=0.5, font=dict(size=11),
        ),
    )
    return fig


def create_price_history(df: pd.DataFrame, zip_code: str) -> go.Figure:
    """Line chart: 24-month price history (navy) + 6-month flat forecast (gold dashed)."""
    row = df[df["zip_code"] == zip_code]
    if row.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig

    history_df = get_price_history_df(df, zip_code)   # sorted oldest → newest
    pred_price = row.sort_values("month").iloc[-1]["predicted_price_6m"]
    last_price = history_df["median_sale_price"].iloc[-1]
    last_month = history_df["month"].iloc[-1]

    x_hist = history_df["month"].tolist()
    # Forecast trace anchors at last history point for visual continuity
    future_months = [
        (pd.Period(last_month, "M") + i).strftime("%Y-%m") for i in range(1, 7)
    ]
    x_fore = [last_month] + future_months
    y_fore = [last_price] + [pred_price] * 6

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_hist,
        y=history_df["median_sale_price"].tolist(),
        name="Price History",
        line=dict(color=COLORS["navy"], width=2),
    ))
    fig.add_trace(go.Scatter(
        x=x_fore,
        y=y_fore,
        name="6M Forecast",
        line=dict(color=COLORS["gold"], width=2, dash="dash"),
    ))
    style_figure(fig, margin=dict(t=30, b=30, l=60, r=20))
    fig.update_yaxes(tickprefix="$", tickformat=",")
    return fig


def create_score_components(row: pd.Series, df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart of 6 weighted score components for a single zip."""
    labels      = list(COMPONENT_COLS.values())
    values      = [row[col] for col in COMPONENT_COLS]
    pop_medians = [df[col].median() for col in COMPONENT_COLS]
    bar_colors  = [
        COLORS["green"] if v >= m else COLORS["red"]
        for v, m in zip(values, pop_medians)
    ]

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker_color=bar_colors,
        hovertemplate="%{y}: %{x:.1f}<extra></extra>",
    ))
    style_figure(
        fig,
        title=dict(
            text=f"Overall Score: {row['investment_score']:.1f}",
            font=dict(size=14, color=COLORS["navy"]),
        ),
        margin=dict(t=40, b=20, l=160, r=20),
    )
    fig.update_xaxes(range=[0, max(INVESTMENT_SCORE_WEIGHTS.values()) * 100], title_text="Weighted Score")
    return fig


def create_top10_table(df: pd.DataFrame) -> pd.DataFrame:
    """Top 10 zip codes by investment score as a display-ready DataFrame (latest month snapshot)."""
    cols = [
        "zip_code", "metro", "investment_score", "investment_grade",
        "yoy_appreciation", "gross_rental_yield",
    ]
    latest = df[df["month"] == df["month"].max()]
    top10 = (
        latest.nlargest(10, "investment_score")[cols]
        .reset_index(drop=True)
    )
    top10.insert(0, "rank", range(1, 11))
    top10["investment_score"]   = top10["investment_score"].round(1)
    top10["yoy_appreciation"]   = top10["yoy_appreciation"].round(2)
    top10["gross_rental_yield"] = top10["gross_rental_yield"].round(2)
    top10.columns = ["#", "Zip Code", "Metro", "Score", "Grade", "YoY Appr %", "Gross Yield %"]
    return top10
