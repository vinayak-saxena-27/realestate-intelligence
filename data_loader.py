import logging
from typing import Tuple

import numpy as np
import pandas as pd
import streamlit as st

from config import (
    APPR_ROUND_DP,
    BACHELOR_RATE_RANGE,
    DATA_END_MONTH,
    DATAFRAME_SCHEMA,
    DAYS_ON_MARKET_RANGE,
    HOMES_SOLD_RANGE,
    INVENTORY_LEVEL_RANGE,
    LIST_TO_SALE_RATIO_RANGE,
    LOGNORMAL_BASE_PRICE,
    METROS,
    METRO_ZIP_BASE,
    N_MONTHS,
    OPTIONAL_CSV_COLUMNS,
    PRICE_ROUND_DP,
    REQUIRED_CSV_COLUMNS,
    REQUIRED_POP_STAT_KEYS,
    RNG_SEED,
    SYNTH_PARAMS,
    ZIP_CODES_PER_METRO,
)


def validate_schema(df: pd.DataFrame) -> None:
    for col, spec in DATAFRAME_SCHEMA.items():
        if col not in df.columns:
            if not spec["nullable"]:
                raise ValueError(f"DataFrame is missing required column: '{col}'")
            continue
        expected_type = spec["type"]
        if expected_type in (int, float):
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise TypeError(f"Column '{col}': expected numeric, got {df[col].dtype}")
        elif expected_type is str:
            if not pd.api.types.is_string_dtype(df[col]):
                raise TypeError(f"Column '{col}': expected string/object, got {df[col].dtype}")


def validate_csv(df: pd.DataFrame) -> None:
    missing_required = [c for c in REQUIRED_CSV_COLUMNS if c not in df.columns]
    if missing_required:
        raise ValueError(f"CSV is missing required columns: {missing_required}")

    # month column extra checks — required for correct time-series feature computation.
    # compute_price_velocity and the 12m-lag price both depend on rows being sortable by month.
    month_col = df["month"]
    if pd.api.types.is_string_dtype(month_col):
        # Accept YYYY-MM strings (lexicographically sortable) or any parseable date string.
        try:
            pd.to_datetime(month_col)
        except Exception:
            raise ValueError(
                "CSV 'month' column contains values that cannot be parsed as dates. "
                "Expected format: YYYY-MM (e.g. '2024-01')."
            )
    elif not (
        pd.api.types.is_integer_dtype(month_col)
        or pd.api.types.is_datetime64_any_dtype(month_col)
        or hasattr(month_col, "dt")
    ):
        raise TypeError(
            f"CSV 'month' column must be a sortable type (string YYYY-MM, integer, or datetime), "
            f"got {month_col.dtype}."
        )

    if "zip_code" in df.columns:
        dupes = df.duplicated(subset=["zip_code", "month"])
        if dupes.any():
            n = dupes.sum()
            example = df.loc[dupes, ["zip_code", "month"]].iloc[0].to_dict()
            raise ValueError(
                f"CSV contains {n} duplicate (zip_code, month) pair(s). "
                f"First duplicate: {example}. Each zip code must have at most one row per month."
            )

    missing_optional = [c for c in OPTIONAL_CSV_COLUMNS if c not in df.columns]
    if missing_optional:
        logging.warning("CSV is missing optional columns (synthetic fallback will be used): %s", missing_optional)


def _month_range(end: str, n: int) -> list[str]:
    """Return n consecutive YYYY-MM strings ending at `end` (inclusive)."""
    end_period = pd.Period(end, freq="M")
    return [(end_period - (n - 1 - i)).strftime("%Y-%m") for i in range(n)]


def _draw_zip_params(
    rng: np.random.Generator,
    anchor: dict,
    n: int,
    p: dict,
) -> dict[str, np.ndarray]:
    """Draw one cross-sectional value per zip. All arrays have shape (n,).

    These are the time-invariant zip characteristics that seed the time series.
    Adding a new zip-level variable: add the rng draw here and include it in
    the returned dict — _expand_to_panel receives it via the `zp` argument.
    """
    metro_price  = anchor["median_price"]
    metro_income = anchor["median_income"]

    heat = rng.uniform(p["heat_min"], p["heat_max"], size=n)

    income = np.maximum(
        p["income_floor"],
        np.round(
            rng.normal(metro_income, metro_income * p["income_spread_pct"], size=n),
            PRICE_ROUND_DP,
        ),
    )

    sqft = rng.uniform(p["sqft_min"], p["sqft_max"], size=n)

    income_ratio = income / metro_income
    mu_adjusted  = anchor["lognormal_mu"] + np.log(income_ratio)
    price_latest = np.maximum(
        p["price_floor"],
        np.round(rng.lognormal(mu_adjusted, p["price_noise_std"], size=n), PRICE_ROUND_DP),
    )

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

    # Metro-level trend (one draw) + zip residuals (n draws)
    metro_heat_draw = rng.uniform(p["heat_min"], p["heat_max"])
    metro_trend = rng.normal(
        metro_heat_draw * p["appr_heat_scale"] + p["appr_heat_offset"],
        p["appr_metro_std"],
    )
    yoy_appr = np.round(
        metro_trend + rng.normal(0.0, p["appr_zip_residual_std"], size=n),
        APPR_ROUND_DP,
    )

    # DOM base: inversely correlated with heat and income
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

    # Homes-sold base: price-scaled bounds, same for all zips in this metro
    price_factor = metro_price / p["sold_norm_price"]
    sold_low_s   = max(p["sold_floor_low"],  int(p["sold_base_low"]  / price_factor))
    sold_high_s  = max(p["sold_floor_high"], int(p["sold_base_high"] / price_factor))

    # list_to_sale_ratio: heat-correlated — hotter markets push ratio toward/above 1.0
    list_to_sale_ratio = np.clip(
        rng.normal(0.97 + heat * 0.06, 0.02, size=n),
        *LIST_TO_SALE_RATIO_RANGE,
    )

    # bachelor_rate: positively correlated with income (income_ratio already computed above)
    bachelor_rate = np.clip(
        rng.normal(income_ratio * 0.4, 0.08, size=n),
        *BACHELOR_RATE_RANGE,
    )

    # inventory_level: inversely correlated with heat — hot markets have low supply
    lo_inv, hi_inv = INVENTORY_LEVEL_RANGE
    inv_mid = lo_inv + (1.0 - heat) * (hi_inv - lo_inv)
    inventory_level = np.clip(
        np.round(rng.normal(inv_mid, 40.0, size=n)).astype(int),
        lo_inv, hi_inv,
    )

    return {
        "income":            income,
        "sqft":              sqft,
        "price_latest":      price_latest,
        "gross_yield":       gross_yield,
        "yoy_appr":          yoy_appr,
        "monthly_rate":      (1.0 + yoy_appr) ** (1.0 / 12) - 1.0,
        "dom_base":          rng.integers(dom_low, dom_high + 1),           # (n,)
        "sold_base":         rng.integers(sold_low_s, sold_high_s + 1, size=n).astype(float),
        "list_to_sale_ratio": list_to_sale_ratio,
        "bachelor_rate":      bachelor_rate,
        "inventory_level":    inventory_level,
    }


def _expand_to_panel(
    rng: np.random.Generator,
    zip_codes: list[str],
    metro: str,
    zp: dict[str, np.ndarray],
    months: list[str],
    p: dict,
) -> dict[str, list]:
    """Expand cross-sectional zip params into a (n_months × n_zips) panel.

    Returns a flat dict of lists, length = n_months * n_zips, ordered
    month-first then zip — matching the row-major flatten of any matrix here.
    Adding a new time-varying column: build its (n_months, n) matrix,
    flatten it, and add it to the return dict.
    """
    n        = len(zip_codes)
    n_months = len(months)
    month_nums = np.array([int(m.split("-")[1]) for m in months])   # (n_months,) → 1-12

    # ── Price ─────────────────────────────────────────────────────────────────
    # Back-project from price_latest using compound monthly rate, then add noise
    months_from_end = np.arange(n_months - 1, -1, -1, dtype=float)
    compound        = (1.0 + zp["monthly_rate"][np.newaxis, :]) ** months_from_end[:, np.newaxis]
    price_trend     = zp["price_latest"][np.newaxis, :] / compound
    price_noise     = rng.normal(1.0, p["monthly_price_noise_std"], size=(n_months, n))
    price_matrix    = np.maximum(p["price_floor"], np.round(price_trend * price_noise, PRICE_ROUND_DP))

    ppsqft_matrix = np.round(price_matrix / zp["sqft"][np.newaxis, :], PRICE_ROUND_DP)

    # Rent follows price each month (same gross yield applied monthly)
    rent_matrix = np.maximum(
        p["rent_floor"],
        np.round(price_matrix * zp["gross_yield"][np.newaxis, :] / 12, PRICE_ROUND_DP),
    )

    # ── Days on market ─────────────────────────────────────────────────────────
    # Seasonal: cos peaks in Jan (month 1), troughs in Jul (month 7)
    seasonal_dom = p["seasonal_dom_amplitude"] * np.cos(2 * np.pi * (month_nums - 1) / 12)
    dom_noise    = rng.normal(0.0, p["monthly_dom_noise_std"], size=(n_months, n))
    dom_matrix   = np.clip(
        np.round(zp["dom_base"][np.newaxis, :] + seasonal_dom[:, np.newaxis] + dom_noise).astype(int),
        *DAYS_ON_MARKET_RANGE,
    )

    # ── Homes sold ─────────────────────────────────────────────────────────────
    # Seasonal: sin peaks in Apr (month 4), troughs in Jan (month 1)
    seasonal_sold = p["seasonal_sold_amplitude"] * np.sin(2 * np.pi * (month_nums - 4) / 12)
    sold_noise    = rng.normal(1.0, p["monthly_sold_noise_std"], size=(n_months, n))
    sold_matrix   = np.clip(
        np.round(
            zp["sold_base"][np.newaxis, :] * (1 + seasonal_sold[:, np.newaxis]) * sold_noise
        ).astype(int),
        *HOMES_SOLD_RANGE,
    )

    # ── median_list_price ──────────────────────────────────────────────────────
    # Applies the zip-level list_to_sale_ratio to each month's price
    median_list_price_matrix = np.round(
        price_matrix * zp["list_to_sale_ratio"][np.newaxis, :],
        PRICE_ROUND_DP,
    )

    # ── price_history ─────────────────────────────────────────────────────────
    # One list of 24 floats per zip (oldest → newest); same value repeated for
    # every month row belonging to that zip — get_price_history_df() unpacks it.
    price_histories = [price_matrix[:, i].tolist() for i in range(n)]

    # ── Index columns ─────────────────────────────────────────────────────────
    # np.repeat gives [month0]*n, [month1]*n, ... — aligns with row-major matrix flatten
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
        "median_household_income": np.tile(zp["income"],            (n_months, 1)).flatten().tolist(),
        "fair_market_rent_2br":    rent_matrix.flatten().tolist(),
        # appreciation_rate in percentage points (e.g. 8.0 for 8%); engineer_features()
        # produces yoy_appreciation from the 12m-lag price — these are parallel columns.
        "appreciation_rate":       np.tile(zp["yoy_appr"] * 100,    (n_months, 1)).flatten().tolist(),
        "list_to_sale_ratio":      np.tile(zp["list_to_sale_ratio"], (n_months, 1)).flatten().tolist(),
        "bachelor_rate":           np.tile(zp["bachelor_rate"],      (n_months, 1)).flatten().tolist(),
        "inventory_level":         np.tile(zp["inventory_level"],    (n_months, 1)).flatten().tolist(),
        "median_list_price":       median_list_price_matrix.flatten().tolist(),
        "price_history":           price_histories * n_months,
    }


def _compute_pop_stats(df: pd.DataFrame) -> dict:
    """Compute population stats from raw data. Called once inside generate_synthetic_data()."""
    gross_yield  = df["fair_market_rent_2br"] * 12 / df["median_sale_price"] * 100
    metro_appr   = df.groupby("metro")["appreciation_rate"].mean()
    metro_yield  = gross_yield.groupby(df["metro"]).mean()

    pop_stats = {
        "median_yoy_appreciation":   float(df["appreciation_rate"].median()),
        "median_gross_rental_yield": float(gross_yield.median()),
        "median_market_heat_index":  50.0,   # placeholder — updated after engineer_features()
        "median_neighborhood_score": 50.0,   # placeholder — updated after engineer_features()
        "median_days_on_market":     float(df["days_on_market"].median()),
        "median_investment_score":   0.0,    # placeholder — filled in Week 3
        "top_metro_appreciation":    str(metro_appr.idxmax()),
        "best_yield_metro":          str(metro_yield.idxmax()),
    }

    assert set(pop_stats.keys()) >= REQUIRED_POP_STAT_KEYS, \
        f"pop_stats is missing keys: {REQUIRED_POP_STAT_KEYS - set(pop_stats.keys())}"
    assert pop_stats["top_metro_appreciation"] in METROS, \
        f"top_metro_appreciation '{pop_stats['top_metro_appreciation']}' not in METROS"
    assert pop_stats["best_yield_metro"] in METROS, \
        f"best_yield_metro '{pop_stats['best_yield_metro']}' not in METROS"

    return pop_stats


def generate_synthetic_data() -> Tuple[pd.DataFrame, dict]:
    """Build the panel dataset: 10 metros × 20 zips × 24 months = 4 800 rows.

    No arguments. Uses np.random.default_rng(RNG_SEED) for full reproducibility.
    Returns a validated DataFrame matching DATAFRAME_SCHEMA sorted by
    (metro, zip_code, month).
    """
    rng    = np.random.default_rng(RNG_SEED)
    p      = SYNTH_PARAMS
    months = _month_range(DATA_END_MONTH, N_MONTHS)

    blocks = []
    for metro in METROS:
        zip_codes  = [str(METRO_ZIP_BASE[metro] + i).zfill(5) for i in range(ZIP_CODES_PER_METRO)]
        metro_data = METROS[metro]  # metro is always a key of METROS (iterating its keys above)
        anchor     = {
            "median_price":  sum(metro_data["median_price_range"]) / 2,
            "median_income": metro_data["median_income"],
            "lognormal_mu":  LOGNORMAL_BASE_PRICE[metro],
        }
        zp    = _draw_zip_params(rng, anchor, len(zip_codes), p)
        block = _expand_to_panel(rng, zip_codes, metro, zp, months, p)
        blocks.append(pd.DataFrame(block))

    df = pd.concat(blocks, ignore_index=True)

    expected_rows = len(METROS) * ZIP_CODES_PER_METRO * N_MONTHS
    assert df.shape[0] == expected_rows,             f"Expected {expected_rows} rows, got {df.shape[0]}"
    assert df.isnull().sum().sum() == 0,             "DataFrame contains NaN values"
    assert (df["median_sale_price"] >= p["price_floor"]).all()
    assert (df["fair_market_rent_2br"] >= p["rent_floor"]).all()
    assert (df["median_household_income"] >= p["income_floor"]).all()

    validate_schema(df)
    df = df.sort_values(["metro", "zip_code", "month"]).reset_index(drop=True)

    # 12-month lag price: actual shifted value where available; for the first 12 months of each
    # zip (where no prior-year row exists), back-calculate from appreciation_rate (%).
    # appreciation_rate is never overwritten by engineer_features() — no order-of-ops risk.
    df["median_sale_price_12m_ago"] = df.groupby("zip_code")["median_sale_price"].shift(12)
    early = df["median_sale_price_12m_ago"].isna()
    df.loc[early, "median_sale_price_12m_ago"] = np.round(
        df.loc[early, "median_sale_price"] / (1 + df.loc[early, "appreciation_rate"] / 100),
        PRICE_ROUND_DP,
    )

    pop_stats = _compute_pop_stats(df)
    return df, pop_stats


# ── Public API ────────────────────────────────────────────────────────────────
# App modules call get_data() for the Streamlit-cached version.
# No caller should call generate_synthetic_data() directly.

@st.cache_data
def get_data() -> Tuple[pd.DataFrame, dict]:
    return generate_synthetic_data()


if __name__ == "__main__":
    df, pop_stats = generate_synthetic_data()
    print("Shape:", df.shape)
    print(df.head(10).to_string())
    print("\npop_stats:")
    for k, v in pop_stats.items():
        print(f"  {k}: {v}")
