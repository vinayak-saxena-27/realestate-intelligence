import streamlit as st

from config import APP_ICON, APP_TITLE, RF_FEATURES
from data_loader import get_data
from feature_engineering import engineer_features
from models import label_segments, predict_prices, train_price_model, train_segment_model
from scoring import compute_investment_score

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
st.title(f"{APP_ICON} {APP_TITLE}")

FILE_PATH = None  # swap to 'data/market_data.csv' for production
raw_df, pop_stats = get_data(source=FILE_PATH)
df, pop_stats     = engineer_features(raw_df, pop_stats)

price_model, price_metrics        = train_price_model(df)
df["predicted_price_6m"]          = predict_prices(df, price_model)
st.session_state["price_model"]   = price_model
st.session_state["price_metrics"] = price_metrics
st.session_state["price_importances"] = dict(zip(RF_FEATURES, price_model.feature_importances_))

df = compute_investment_score(df)
pop_stats["median_investment_score"] = float(df["investment_score"].median())

kmeans_model, kmeans_scaler          = train_segment_model(df)
df["market_segment"]                 = label_segments(df, kmeans_model, kmeans_scaler)
st.session_state["kmeans_model"]     = kmeans_model
st.session_state["kmeans_scaler"]    = kmeans_scaler

st.write(f"Loaded {len(df):,} rows across {df['metro'].nunique()} metros and {df['zip_code'].nunique()} zip codes.")
st.dataframe(df.head(20))
