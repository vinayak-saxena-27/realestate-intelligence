import streamlit as st

from _styles import inject_css
from config import APP_ICON, APP_TITLE, RF_FEATURES
from data_loader import get_data
from feature_engineering import engineer_features
from models import label_segments, predict_prices, train_price_model, train_segment_model
from scoring import compute_investment_score

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
inject_css()

with st.sidebar:
    st.markdown(
        f"<div style='color:#1B3A5C;font-size:20px;font-weight:700;"
        f"padding:8px 0;border-bottom:2px solid #C9A84C;margin-bottom:16px'>"
        f"{APP_ICON} {APP_TITLE}</div>",
        unsafe_allow_html=True,
    )
    st.caption("Powered by real estate market intelligence")

st.title(f"{APP_ICON} {APP_TITLE}")

FILE_PATH = None  # swap to 'data/market_data.csv' for production
raw_df, pop_stats = get_data(source=FILE_PATH)
df, pop_stats     = engineer_features(raw_df, pop_stats)

price_model, price_metrics            = train_price_model(df)
df["predicted_price_6m"]              = predict_prices(df, price_model)
st.session_state["price_model"]       = price_model
st.session_state["price_metrics"]     = price_metrics
st.session_state["price_importances"] = dict(zip(RF_FEATURES, price_model.feature_importances_))

df = compute_investment_score(df, pop_stats)
pop_stats["median_investment_score"] = float(df["investment_score"].median())
pop_stats["median_sale_price"]       = float(df["median_sale_price"].median())
pop_stats["median_net_yield"]        = float(df["net_rental_yield"].median())

kmeans_model, kmeans_scaler      = train_segment_model(df)
df["market_segment"]             = label_segments(df, kmeans_model, kmeans_scaler)
st.session_state["kmeans_model"] = kmeans_model
st.session_state["kmeans_scaler"]= kmeans_scaler
st.session_state["df"]           = df
st.session_state["pop_stats"]    = pop_stats

latest = df[df["month"] == df["month"].max()]
n_zips   = latest["zip_code"].nunique()
n_metros = latest["metro"].nunique()
n_grades = latest["investment_grade"].value_counts()

st.markdown(
    f"Data loaded: **{n_zips} zip codes** across **{n_metros} metro areas** — "
    f"use the sidebar to navigate between pages."
)

cols = st.columns(5)
for col, grade in zip(cols, ["A", "B", "C", "D", "F"]):
    col.metric(label=f"Grade {grade}", value=int(n_grades.get(grade, 0)))
