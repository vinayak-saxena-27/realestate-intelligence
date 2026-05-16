import numpy as np
import pandas as pd
import streamlit as st

from config import (
    APPR_ROUND_DP,
    DATA_END_MONTH,
    DATAFRAME_SCHEMA,
    FALLBACK_ANCHOR,
    METRO_ANCHORS,
    METROS,
    METRO_ZIPS,
    N_MONTHS,
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


def _month_range(end: str, n: int) -> list[str]:
    """Return n consecutive YYYY-MM strings ending at `end` (inclusive)."""
    end_period = pd.Period(end, freq="M")
    return [(end_period - (n - 1 - i)).strftime("%Y-%m") for i in range(n)]


def _build_metro_block(
    rng: np.random.Generator,
    metro: str,
    zip_codes: list[str],
    anchor: dict,
    p: dict,
    months: list[str],
) -> dict[str, list]:
    """Return a dict of lists representing the panel for one metro.

    Each list has length len(zip_codes) * len(months). Matrices are built in
    (n_months, n_zips) shape then flattened row-major so that:
        rows 0..n-1   → month[0], all zips
        rows n..2n-1  → month[1], all zips
        ...
    """
    n        = len(zip_codes)
    n_months = len(months)
    metro_price  = anchor["median_price"]
    metro_income = anchor["median_income"]

    # ── Cross-sectional zip parameters (one draw per zip) ────────────────────
    heat = rng.uniform(p["heat_min"], p["heat_max"], size=n)

    income = np.maximum(
        p["income_floor"],
        np.round(
            rng.normal(metro_income, metro_income * p["income_spread_pct"], size=n),
            PRICE_ROUND_DP,
        ),
    )
    income_ratio = income / metro_income

    # Sqft fixed per zip — drives price_per_sqft but doesn't change month-to-month
    sqft = rng.uniform(p["sqft_min"], p["sqft_max"], size=n)

    # Latest-month price (anchor for the time series)
    price_latest = np.maximum(
        p["price_floor"],
        np.round(
            metro_price * income_ratio * rng.normal(1.0, p["price_noise_std"], size=n),
            PRICE_ROUND_DP,
        ),
    )

    # Gross yield — fixed per zip, drives rent
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

    # YoY appreciation — metro trend + zip residual; drives the price time series
    metro_heat_draw = rng.uniform(p["heat_min"], p["heat_max"])
    metro_trend = rng.normal(
        metro_heat_draw * p["appr_heat_scale"] + p["appr_heat_offset"],
        p["appr_metro_std"],
    )
    yoy_appr = np.round(
        metro_trend + rng.normal(0.0, p["appr_zip_residual_std"], size=n),
        APPR_ROUND_DP,
    )
    monthly_rate = (1.0 + yoy_appr) ** (1.0 / 12) - 1.0   # compound monthly rate per zip

    # DOM base — single draw per zip, representing that zip's typical market speed
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
    dom_base = rng.integers(dom_low, dom_high + 1)          # shape (n,)

    # Homes-sold base — same price-scaled bounds for every zip in this metro
    price_factor   = metro_price / p["sold_norm_price"]
    sold_low_s     = max(p["sold_floor_low"],  int(p["sold_base_low"]  / price_factor))
    sold_high_s    = max(p["sold_floor_high"], int(p["sold_base_high"] / price_factor))
    sold_base      = rng.integers(sold_low_s, sold_high_s + 1, size=n).astype(float)

    # ── Time-series matrices: shape (n_months, n) ─────────────────────────────
    # Price: back-project from price_latest using compound monthly rate, then add noise
    months_from_end = np.arange(n_months - 1, -1, -1, dtype=float)          # [23, 22, ..., 0]
    compound        = (1.0 + monthly_rate[np.newaxis, :]) ** months_from_end[:, np.newaxis]
    price_trend     = price_latest[np.newaxis, :] / compound                 # (n_months, n)
    price_noise     = rng.normal(1.0, p["monthly_price_noise_std"], size=(n_months, n))
    price_matrix    = np.maximum(
        p["price_floor"],
        np.round(price_trend * price_noise, PRICE_ROUND_DP),
    )

    ppsqft_matrix = np.round(price_matrix / sqft[np.newaxis, :], PRICE_ROUND_DP)

    # Rent follows price each month (same gross yield, monthly value = annual / 12)
    rent_matrix = np.maximum(
        p["rent_floor"],
        np.round(price_matrix * gross_yield[np.newaxis, :] / 12, PRICE_ROUND_DP),
    )

    # DOM: base + seasonal (peak Jan, trough May) + noise
    month_nums   = np.array([int(m.split("-")[1]) for m in months])          # (n_months,) → 1-12
    seasonal_dom = p["seasonal_dom_amplitude"] * np.cos(2 * np.pi * (month_nums - 1) / 12)
    dom_noise    = rng.normal(0.0, p["monthly_dom_noise_std"], size=(n_months, n))
    dom_matrix   = np.clip(
        np.round(dom_base[np.newaxis, :] + seasonal_dom[:, np.newaxis] + dom_noise).astype(int),
        5, 120,
    )

    # Homes sold: base × seasonal (peak Apr, trough Jan) × noise
    seasonal_sold = p["seasonal_sold_amplitude"] * np.sin(2 * np.pi * (month_nums - 4) / 12)
    sold_noise    = rng.normal(1.0, p["monthly_sold_noise_std"], size=(n_months, n))
    sold_matrix   = np.clip(
        np.round(
            sold_base[np.newaxis, :] * (1 + seasonal_sold[:, np.newaxis]) * sold_noise
        ).astype(int),
        2, 500,
    )

    # Income: annual metric — held constant across months for each zip
    income_matrix = np.tile(income, (n_months, 1))

    # YoY appreciation: zip-level trend constant — repeated for each month
    yoy_matrix = np.tile(yoy_appr, (n_months, 1))

    # ── Flatten row-major → (n_months * n,) per column ───────────────────────
    # np.repeat repeats each element of months n times:
    #   ["2023-01"]*n, ["2023-02"]*n, ... → aligns with price_matrix.flatten()
    months_col = np.repeat(months, n)
    zip_col    = np.tile(zip_codes, n_months)
    metro_col  = np.tile([metro] * n, n_months)

    return {
        "month":                   months_col.tolist(),
        "zip_code":                zip_col.tolist(),
        "metro":                   metro_col.tolist(),
        "median_sale_price":       price_matrix.flatten().tolist(),
        "price_per_sqft":          ppsqft_matrix.flatten().tolist(),
        "days_on_market":          dom_matrix.flatten().tolist(),
        "homes_sold":              sold_matrix.flatten().tolist(),
        "median_household_income": income_matrix.flatten().tolist(),
        "fair_market_rent_2br":    rent_matrix.flatten().tolist(),
        "yoy_appreciation":        yoy_matrix.flatten().tolist(),
    }


def generate_synthetic_data() -> pd.DataFrame:
    """Build the panel dataset: 200 zip codes × 24 months = 4 800 rows.

    No arguments. Uses np.random.default_rng(RNG_SEED) for full reproducibility.
    Returns a validated DataFrame matching DATAFRAME_SCHEMA sorted by
    (metro, zip_code, month).
    """
    rng    = np.random.default_rng(RNG_SEED)
    p      = SYNTH_PARAMS
    months = _month_range(DATA_END_MONTH, N_MONTHS)

    blocks = [
        _build_metro_block(
            rng, metro, METRO_ZIPS[metro],
            METRO_ANCHORS.get(metro, FALLBACK_ANCHOR), p, months,
        )
        for metro in METROS
    ]
    df = pd.concat([pd.DataFrame(b) for b in blocks], ignore_index=True)

    expected_rows = sum(len(v) for v in METRO_ZIPS.values()) * N_MONTHS
    assert df.shape[0] == expected_rows,            f"Expected {expected_rows} rows, got {df.shape[0]}"
    assert df.isnull().sum().sum() == 0,            "DataFrame contains NaN values"
    assert (df["median_sale_price"] >= p["price_floor"]).all(),       "median_sale_price below price_floor"
    assert (df["fair_market_rent_2br"] >= p["rent_floor"]).all(),     "fair_market_rent_2br below rent_floor"
    assert (df["median_household_income"] >= p["income_floor"]).all(),"median_household_income below income_floor"

    validate_schema(df)
    return df.sort_values(["metro", "zip_code", "month"]).reset_index(drop=True)


# ── Public API ────────────────────────────────────────────────────────────────
# Application modules should call load_data() for the Streamlit-cached version.
# Direct calls to generate_synthetic_data() are safe outside Streamlit (e.g., scripts, tests).

@st.cache_data
def load_data() -> pd.DataFrame:
    return generate_synthetic_data()


if __name__ == "__main__":
    df = generate_synthetic_data()
    print("Shape:", df.shape)
    print(df.head(10).to_string())
