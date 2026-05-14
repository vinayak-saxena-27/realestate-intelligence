import numpy as np
import pandas as pd
import streamlit as st

from config import (
    APPR_ROUND_DP,
    DATAFRAME_SCHEMA,
    FALLBACK_ANCHOR,
    METRO_ANCHORS,
    METROS,
    METRO_ZIPS,
    PRICE_ROUND_DP,
    RNG_SEED,
    SYNTH_PARAMS,
)


def validate_schema(df: pd.DataFrame) -> None:
    missing = set(DATAFRAME_SCHEMA) - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame is missing required columns: {missing}")
    for col, expected_type in DATAFRAME_SCHEMA.items():
        if expected_type in (int, float):
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise TypeError(f"Column '{col}': expected numeric, got {df[col].dtype}")
        elif expected_type is str:
            if not pd.api.types.is_string_dtype(df[col]):
                raise TypeError(f"Column '{col}': expected string/object, got {df[col].dtype}")


def _build_metro_block(
    rng: np.random.Generator,
    metro: str,
    zip_codes: list[str],
    anchor: dict,
    p: dict,
) -> dict[str, list]:
    n            = len(zip_codes)
    metro_price  = anchor["median_price"]
    metro_income = anchor["median_income"]

    # Heat: one draw per zip
    heat = rng.uniform(p["heat_min"], p["heat_max"], size=n)

    # Income: zip-level spread around the metro median
    income = np.maximum(
        p["income_floor"],
        np.round(rng.normal(metro_income, metro_income * p["income_spread_pct"], size=n), PRICE_ROUND_DP),
    )

    # Price: anchored to metro, nudged by local income deviation
    income_ratio = income / metro_income
    price = np.maximum(
        p["price_floor"],
        np.round(metro_price * income_ratio * rng.normal(1.0, p["price_noise_std"], size=n), PRICE_ROUND_DP),
    )

    # Sqft first; price_per_sqft derived (not the other way around)
    sqft           = rng.uniform(p["sqft_min"], p["sqft_max"], size=n)
    price_per_sqft = np.round(price / sqft, PRICE_ROUND_DP)

    # Yield compression: pricier metros produce lower gross yields
    # yield_mid = base * (norm_price / metro_price)^exponent, then clamped
    yield_mid = np.clip(
        p["gross_yield_base"] * (p["yield_norm_price"] / metro_price) ** p["yield_price_exponent"],
        p["gross_yield_min"],
        p["gross_yield_max"],
    )
    gross_yield = np.clip(
        rng.normal(yield_mid, p["yield_noise_std"], size=n),
        p["gross_yield_min"],
        p["gross_yield_max"],
    )
    rent = np.maximum(
        p["rent_floor"],
        np.round(price * gross_yield / 12, PRICE_ROUND_DP),
    )

    # DOM: inversely correlated with heat AND income
    # income_norm clips at 1.5 so ultra-high-income zips don't collapse DOM to zero alone
    income_norm  = np.clip(income / p["dom_norm_income"], 0.0, 1.5)
    market_speed = p["dom_heat_weight"] * heat + p["dom_income_weight"] * income_norm
    cold_factor  = np.maximum(0.0, 1.0 - market_speed)
    dom_low  = np.maximum(
        p["dom_floor_low"],
        (p["dom_base_low"]  + cold_factor * p["dom_cold_spread_low"]).astype(int),
    )
    dom_high = np.maximum(
        p["dom_floor_high"],
        (p["dom_base_high"] + cold_factor * p["dom_cold_spread_high"]).astype(int),
    )
    dom = rng.integers(dom_low, dom_high + 1)  # numpy supports per-element [low, high)

    # Homes sold: same price-scaled bounds for every zip in this metro
    price_factor = metro_price / p["sold_norm_price"]
    sold_low  = max(p["sold_floor_low"],  int(p["sold_base_low"]  / price_factor))
    sold_high = max(p["sold_floor_high"], int(p["sold_base_high"] / price_factor))
    homes_sold = rng.integers(sold_low, sold_high + 1, size=n)

    # Appreciation: metro-level trend (one draw) + zip-level residual (n draws)
    # This ensures zips within a metro move together while still diverging slightly
    metro_heat  = rng.uniform(p["heat_min"], p["heat_max"])
    metro_trend = rng.normal(
        metro_heat * p["appr_heat_scale"] + p["appr_heat_offset"],
        p["appr_metro_std"],
    )
    appr = np.round(metro_trend + rng.normal(0.0, p["appr_zip_residual_std"], size=n), APPR_ROUND_DP)

    return {
        "zip_code":                list(zip_codes),
        "metro":                   [metro] * n,
        "median_sale_price":       price.tolist(),
        "price_per_sqft":          price_per_sqft.tolist(),
        "days_on_market":          dom.tolist(),
        "homes_sold":              homes_sold.tolist(),
        "median_household_income": income.tolist(),
        "fair_market_rent_2br":    rent.tolist(),
        "yoy_appreciation":        appr.tolist(),
    }


def _build_dataframe() -> pd.DataFrame:
    """Synthetic data source — pure NumPy/Pandas, no Streamlit dependency.

    To switch to a real feed: replace the body of this function with your API /
    database call and return a DataFrame. load_data() and the rest of the app
    need no changes — validate_schema() will catch any schema mismatches.
    """
    rng = np.random.default_rng(RNG_SEED)
    p   = SYNTH_PARAMS

    blocks = [
        _build_metro_block(rng, metro, METRO_ZIPS[metro], METRO_ANCHORS.get(metro, FALLBACK_ANCHOR), p)
        for metro in METROS
    ]
    df = pd.concat([pd.DataFrame(b) for b in blocks], ignore_index=True)

    expected = sum(len(v) for v in METRO_ZIPS.values())
    assert df.shape[0] == expected, f"Expected {expected} rows, got {df.shape[0]}"
    assert df.isnull().sum().sum() == 0, "DataFrame contains NaN values"
    assert (df["median_sale_price"] >= p["price_floor"]).all(), "median_sale_price below price_floor"
    assert (df["fair_market_rent_2br"] >= p["rent_floor"]).all(), "fair_market_rent_2br below rent_floor"
    assert (df["median_household_income"] >= p["income_floor"]).all(), "median_household_income below income_floor"

    return df


# ── Public API ────────────────────────────────────────────────────────────────
# All app modules must import and call load_data() — never _build_dataframe()
# directly. The cache sits here, above the data source, so the data source can
# be swapped without touching the cache layer or any call site in the app.
# For a real feed that refreshes: @st.cache_data(ttl=3600)

@st.cache_data
def load_data() -> pd.DataFrame:
    df = _build_dataframe()  # ← only this line changes when switching data sources
    validate_schema(df)
    return df


if __name__ == "__main__":
    df = load_data()
    print("Shape:", df.shape)
    print(df.head())
