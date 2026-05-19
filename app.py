import streamlit as st

from config import APP_ICON, APP_TITLE
from data_loader import load_data
from feature_engineering import engineer_features, get_population_stats

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
st.title(f"{APP_ICON} {APP_TITLE}")

raw_df       = load_data()
df           = engineer_features(raw_df)
pop_stats    = get_population_stats(df)

st.write(f"Loaded {len(df):,} rows across {df['metro'].nunique()} metros and {df['zip_code'].nunique()} zip codes.")
st.dataframe(df.head(20))
