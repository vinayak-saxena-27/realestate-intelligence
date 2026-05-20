import numpy as np
import pandas as pd
import streamlit as st

from config import (
    HEAT_INDEX_COMPONENTS,
    NEIGHBORHOOD_WEIGHTS,
    NET_YIELD_EXPENSE_RATIO,
    SYNTH_PARAMS,
)


def compute_yoy_appreciation(df: pd.DataFrame) -> pd.Series:
    p_now = df["median_sale_price"]
    p_12m = df["median_sale_price_12m_ago"]
    return pd.Series(
        np.where(p_12m > 0, (p_now - p_12m) / p_12m * 100, 0.0),
        index=df.index,
    )


def compute_price_velocity(df: pd.DataFrame) -> pd.Series:
    w = SYNTH_PARAMS["velocity_window"]
    return (
        df.groupby("zip_code")["median_sale_price"]
        .transform(lambda x: x.pct_change().mul(100).rolling(w).mean())
        .fillna(0.0)
    )


def _minmax(series: pd.Series) -> pd.Series:
    """Min-max scale `series` to [0, 100]. Returns 50.0 for constant input.

    WARNING — global normalization scope:
    This function scales relative to the min/max of the entire input series,
    which currently spans all metros, all zip codes, and all months.
    Consequence: adding a metro with extreme values (e.g. NYC median price)
    shifts every existing zip's market_heat_index and neighborhood_score
    silently — no error fires, scores just change.

    Long-term fix: introduce a NORMALIZATION_SCOPE flag in config.py
    ('global' | 'per_metro') and, when set to 'per_metro', apply this
    function inside a groupby('metro') before combining. Gate behind the
    flag so existing behaviour is unchanged until the change is deliberate.
    """
    lo, hi = series.min(), series.max()
    return pd.Series(
        np.where(hi > lo, (series - lo) / (hi - lo) * 100, 50.0),
        index=series.index,
    )


def compute_market_heat_index(df: pd.DataFrame) -> pd.Series:
    w        = HEAT_INDEX_COMPONENTS
    dom_inv  = 100 - _minmax(df["days_on_market"])
    sold     = _minmax(df["homes_sold"])
    velocity = _minmax(df["price_velocity"])
    lts      = _minmax(df["list_to_sale_ratio"])
    return (
        dom_inv  * w["days_on_market"]
        + sold     * w["homes_sold"]
        + velocity * w["price_velocity"]
        + lts      * w["list_to_sale"]
    )


def compute_gross_rental_yield(df: pd.DataFrame) -> pd.Series:
    annual_rent = df["fair_market_rent_2br"] * 12
    return pd.Series(
        np.where(df["median_sale_price"] > 0, annual_rent / df["median_sale_price"] * 100, 0.0),
        index=df.index,
    )


def compute_net_rental_yield(df: pd.DataFrame) -> pd.Series:
    return df["gross_rental_yield"] * NET_YIELD_EXPENSE_RATIO


def compute_neighborhood_score(df: pd.DataFrame) -> pd.Series:
    w    = NEIGHBORHOOD_WEIGHTS
    inc  = _minmax(df["median_household_income"])
    edu  = _minmax(df["bachelor_rate"])   # guaranteed by data_loader PRD 2
    hval = _minmax(df["median_sale_price"])
    return inc * w["income"] + edu * w["education"] + hval * w["home_value"]


_REQUIRED_COLUMNS = [
    "zip_code",              # groupby key for price_velocity
    "month",                 # sort key for correct time-series ordering
    "median_sale_price",
    "median_sale_price_12m_ago",
    "fair_market_rent_2br",
    "median_household_income",
    "days_on_market",
    "homes_sold",
    "list_to_sale_ratio",
    "bachelor_rate",         # guaranteed by data_loader; no fallback in compute_neighborhood_score
]


@st.cache_data
def engineer_features(df: pd.DataFrame, pop_stats: dict) -> tuple[pd.DataFrame, dict]:
    """Run full feature engineering pipeline on raw data.

    Returns (df, pop_stats) where df has 6 new feature columns and pop_stats
    has its 50.0 placeholders replaced with real medians. Input df is never mutated.
    """
    missing = [c for c in _REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df       = df.copy()
    pop_stats = pop_stats.copy()
    df = df.sort_values(["zip_code", "month"]).reset_index(drop=True)
    df["yoy_appreciation"]   = compute_yoy_appreciation(df)
    df["price_velocity"]     = compute_price_velocity(df)
    df["market_heat_index"]  = compute_market_heat_index(df)
    df["gross_rental_yield"] = compute_gross_rental_yield(df)
    df["net_rental_yield"]   = compute_net_rental_yield(df)
    df["neighborhood_score"] = compute_neighborhood_score(df)

    pop_stats["median_market_heat_index"]  = float(df["market_heat_index"].median())
    pop_stats["median_neighborhood_score"] = float(df["neighborhood_score"].median())
    return df, pop_stats


_POPULATION_STATS_COLUMNS = [
    "yoy_appreciation", "gross_rental_yield", "market_heat_index",
    "neighborhood_score", "days_on_market",
]


def get_population_stats(df: pd.DataFrame) -> dict:
    """Return population-level medians for narrative comparison.

    Must be called on the output of engineer_features(), not the raw df.
    """
    missing = [c for c in _POPULATION_STATS_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"get_population_stats requires engineered columns — missing: {missing}. "
            "Call engineer_features(df) first."
        )
    return {
        "median_yoy_appreciation":   df["yoy_appreciation"].median(),
        "median_gross_rental_yield": df["gross_rental_yield"].median(),
        "median_market_heat_index":  df["market_heat_index"].median(),
        "median_neighborhood_score": df["neighborhood_score"].median(),
        "median_days_on_market":     df["days_on_market"].median(),
    }


if __name__ == "__main__":
    from data_loader import generate_synthetic_data

    raw, ps = generate_synthetic_data()
    feature_cols = [
        "yoy_appreciation", "price_velocity", "market_heat_index",
        "gross_rental_yield", "net_rental_yield", "neighborhood_score",
    ]

    # engineer_features must not mutate the input df
    df, ps = engineer_features(raw, ps)
    assert set(feature_cols).issubset(df.columns), "Missing feature columns"
    assert df.isnull().sum().sum() == 0, "NaN values in engineered df"
    assert all(c in raw.columns for c in raw.columns), "Input df was mutated"

    # pop_stats placeholders must now be real values
    assert ps["median_market_heat_index"]  != 50.0, "placeholder not filled"
    assert ps["median_neighborhood_score"] != 50.0, "placeholder not filled"

    # determinism check
    _, ps2 = generate_synthetic_data()
    df2, _ = engineer_features(raw, ps2)
    for col in feature_cols:
        assert (df[col] == df2[col]).all(), f"{col} is non-deterministic"

    # ValueError on missing column
    try:
        engineer_features(raw.drop(columns=["median_sale_price"]), ps)
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        print(f"ValueError correctly raised: {e}")

    # range assertions
    assert (df["market_heat_index"].between(0, 100)).all()
    assert (df["gross_rental_yield"].between(2, 12)).mean() > 0.95
    assert (df["net_rental_yield"] == df["gross_rental_yield"] * NET_YIELD_EXPENSE_RATIO).all()
    assert (df["neighborhood_score"].between(0, 100)).all()

    print("\n--- PRD 1 features ---")
    for feat in ["yoy_appreciation", "price_velocity", "market_heat_index"]:
        s = df[feat].agg(["min", "max", "mean"])
        print(f"{feat:24s}  min={s['min']:8.4f}  max={s['max']:8.4f}  mean={s['mean']:8.4f}")

    print("\n--- PRD 2 features ---")
    for feat in ["gross_rental_yield", "net_rental_yield", "neighborhood_score"]:
        s = df[feat].agg(["min", "max", "mean"])
        print(f"{feat:24s}  min={s['min']:8.4f}  max={s['max']:8.4f}  mean={s['mean']:8.4f}")

    print("\npop_stats after engineer_features:")
    for k, v in ps.items():
        print(f"  {k}: {v}")
