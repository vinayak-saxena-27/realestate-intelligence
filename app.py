import plotly.express as px
import streamlit as st

from _styles import inject_css, load_page_data
from config import APP_ICON, APP_TITLE, GRADE_COLORS, RF_FEATURES

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
inject_css()

# ── Pipeline — runs once per browser session ──────────────────────────────────
if "df" not in st.session_state:
    from data_loader import get_data
    from feature_engineering import engineer_features
    from models import label_segments, predict_prices, train_price_model, train_segment_model
    from scoring import compute_investment_score

    FILE_PATH = None  # swap to 'data/market_data.csv' for real data

    with st.spinner("Loading market data and training models…"):
        raw_df, pop_stats            = get_data(source=FILE_PATH)
        df, pop_stats                = engineer_features(raw_df, pop_stats)
        price_model, price_metrics   = train_price_model(df)
        df["predicted_price_6m"]     = predict_prices(df, price_model)
        st.session_state["price_model"]       = price_model
        st.session_state["price_metrics"]     = price_metrics
        st.session_state["price_importances"] = dict(
            zip(RF_FEATURES, price_model.feature_importances_)
        )
        df                                   = compute_investment_score(df, pop_stats)
        pop_stats["median_investment_score"] = float(df["investment_score"].median())
        pop_stats["median_sale_price"]       = float(df["median_sale_price"].median())
        pop_stats["median_net_yield"]        = float(df["net_rental_yield"].median())
        kmeans_model, kmeans_scaler          = train_segment_model(df)
        df["market_segment"]                 = label_segments(df, kmeans_model, kmeans_scaler)
        st.session_state["kmeans_model"]     = kmeans_model
        st.session_state["kmeans_scaler"]    = kmeans_scaler
        st.session_state["df"]               = df
        st.session_state["pop_stats"]        = pop_stats


# ── Home page ─────────────────────────────────────────────────────────────────
def home_page() -> None:
    df, pop_stats, latest = load_page_data()

    st.title(f"{APP_ICON} Market Overview")
    st.markdown(
        f"<p style='color:#8A9BB0;font-size:13.5px;margin-top:-8px;margin-bottom:1.5rem'>"
        f"Investment intelligence across {latest['zip_code'].nunique()} zip codes "
        f"and {latest['metro'].nunique()} US metro areas</p>",
        unsafe_allow_html=True,
    )

    # Grade count summary
    n_grades = latest["investment_grade"].value_counts()
    grade_cols = st.columns(5)
    for col, grade in zip(grade_cols, ["A", "B", "C", "D", "F"]):
        col.metric(label=f"Grade {grade}", value=int(n_grades.get(grade, 0)))

    st.divider()
    st.subheader("Investment Grade Map")
    st.caption("Bubble size = investment score · Color = grade · Hover for details")

    fig = px.scatter_mapbox(
        latest.sort_values("investment_grade"),
        lat="latitude",
        lon="longitude",
        color="investment_grade",
        size="investment_score",
        color_discrete_map=GRADE_COLORS,
        category_orders={"investment_grade": ["A", "B", "C", "D", "F"]},
        hover_name="zip_code",
        hover_data={
            "metro":              True,
            "investment_score":   ":.1f",
            "yoy_appreciation":   ":.1f",
            "gross_rental_yield": ":.1f",
            "investment_grade":   False,
            "latitude":           False,
            "longitude":          False,
        },
        zoom=3.5,
        center={"lat": 37.5, "lon": -96.0},
        mapbox_style="open-street-map",
        size_max=18,
    )
    fig.update_layout(
        height=560,
        margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor="white",
        font=dict(family="Inter, -apple-system, sans-serif"),
        legend=dict(
            title=dict(text="Grade", font=dict(size=12)),
            orientation="v",
            yanchor="top",  y=0.99,
            xanchor="left", x=0.01,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#DDE4EE",
            borderwidth=1,
            font=dict(size=12),
        ),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Navigation ────────────────────────────────────────────────────────────────
pages = st.navigation({
    "Overview": [
        st.Page(home_page, title="Market Overview", icon="🗺️"),
    ],
    "Analysis": [
        st.Page("pages/01_Command_Center.py",     title="Command Center",    icon="📊"),
        st.Page("pages/02_Zip_Code_Explorer.py",  title="Zip Code Explorer", icon="🔍"),
        st.Page("pages/03_Zip_Code_Deep_Dive.py", title="Deep Dive",         icon="📈"),
        st.Page("pages/04_Market_Comparison.py",  title="Market Comparison", icon="⚖️"),
        st.Page("pages/05_Model_Intelligence.py", title="Model Intelligence", icon="🤖"),
    ],
})
pages.run()
