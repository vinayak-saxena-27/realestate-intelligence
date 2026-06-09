import hashlib
import io
import logging
import os
from typing import BinaryIO, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from config import (
    APPR_ROUND_DP,
    BACHELOR_RATE_RANGE,
    DATA_END_MONTH,
    DATAFRAME_SCHEMA,
    DAYS_ON_MARKET_RANGE,
    DECLINING_COUNT,
    DECLINING_METROS,
    HOMES_SOLD_RANGE,
    HOT_DOM_CEILING,
    HOT_MARKET_COUNT,
    INVENTORY_LEVEL_RANGE,
    LIST_TO_SALE_RATIO_RANGE,
    LOGNORMAL_BASE_PRICE,
    METROS,
    MAX_CSV_SIZE_MB,
    METRO_ZIP_BASE,
    N_MONTHS,
    OPTIONAL_CSV_COLUMNS,
    PRICE_ROUND_DP,
    REQUIRED_CSV_COLUMNS,
    REQUIRED_POP_STAT_KEYS,
    RNG_SEED,
    SLOW_DOM_FLOOR,
    SLOW_MARKET_COUNT,
    SYNTH_PARAMS,
    TOP_APPRECIATING_COUNT,
    ZIP_CODES_PER_METRO,
)


_COLUMN_RANGES: dict[str, tuple] = {
    "days_on_market":     DAYS_ON_MARKET_RANGE,
    "homes_sold":         HOMES_SOLD_RANGE,
    "list_to_sale_ratio": LIST_TO_SALE_RATIO_RANGE,
    "inventory_level":    INVENTORY_LEVEL_RANGE,
    "bachelor_rate":      BACHELOR_RATE_RANGE,
}


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

    for col, (lo, hi) in _COLUMN_RANGES.items():
        if DATAFRAME_SCHEMA.get(col, {}).get("nullable", True) or col not in df.columns:
            continue
        out_of_range = ~df[col].between(lo, hi)
        if not out_of_range.any():
            continue
        n_below = int((df[col] < lo).sum())
        n_above = int((df[col] > hi).sum())
        parts = []
        if n_below:
            parts.append(f"{n_below} row(s) below minimum {lo}")
        if n_above:
            parts.append(f"{n_above} row(s) above maximum {hi}")
        raise ValueError(
            f"Column '{col}' out of range [{lo}, {hi}]: {'; '.join(parts)}"
        )


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
    return [p.strftime("%Y-%m") for p in pd.period_range(end=end, periods=n, freq="M")]


def _compute_dom(
    heat: np.ndarray,
    income: np.ndarray,
    metro_income: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Vectorized heat + income composite DOM base per zip.

    heat=1 → ~8 days, heat=0 → ~90 days; wealthier areas sell 10-20% faster.
    Lognormal noise (sigma=0.25) preserves realistic right-skew.
    """
    income_ratio = np.clip(income / metro_income, 0.5, 2.0)
    base_dom     = 90.0 - heat * 82.0                               # [8, 90]
    income_adj   = np.maximum(base_dom * (1.0 - (income_ratio - 1.0) * 0.15), 3.0)
    dom          = rng.lognormal(mean=np.log(income_adj), sigma=0.25)
    return np.clip(np.round(dom).astype(int), *DAYS_ON_MARKET_RANGE)


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

    # DOM base: heat + income composite (replaces bounds-based approach)
    dom_base = _compute_dom(heat, income, metro_income, rng)

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
        "dom_base":          dom_base,
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
    }


def _inject_market_patterns(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Apply deliberate market patterns after base generation. Returns a new DataFrame.

    Operates at zip level so appreciation_rate stays uniform per zip and DOM
    changes apply to all months of the selected zips.
    Called after sorting and before the 12m-lag backfill so appreciation_rate
    is final when prior prices are back-calculated.
    """
    df = df.copy()
    # Reset any naturally negative rates so injection is the sole source of negatives
    neg_mask = df["appreciation_rate"] < 0
    df.loc[neg_mask, "appreciation_rate"] = df.loc[neg_mask, "appreciation_rate"].abs()

    # Top TOP_APPRECIATING_COUNT zips — boost by 1.4×, cap at 25%
    zip_appr  = df.groupby("zip_code")["appreciation_rate"].first()
    top_zips  = zip_appr.nlargest(TOP_APPRECIATING_COUNT).index
    top_mask  = df["zip_code"].isin(top_zips)
    df.loc[top_mask, "appreciation_rate"] = (
        df.loc[top_mask, "appreciation_rate"] * 1.4
    ).clip(upper=25.0)

    # DECLINING_COUNT zips concentrated in DECLINING_METROS — set to −2% … −5%
    zip_pool     = df[df["metro"].isin(DECLINING_METROS)]["zip_code"].unique()
    decline_zips = rng.choice(zip_pool, size=min(DECLINING_COUNT, len(zip_pool)), replace=False)
    decline_rates = np.round(rng.uniform(-5.0, -2.0, size=len(decline_zips)), APPR_ROUND_DP)
    zip_rate_map  = dict(zip(decline_zips, decline_rates))
    decline_mask  = df["zip_code"].isin(decline_zips)
    df.loc[decline_mask, "appreciation_rate"] = df.loc[decline_mask, "zip_code"].map(zip_rate_map)

    # Determine hot/slow target zips before DOM injection
    zip_mean_dom = df.groupby("zip_code")["days_on_market"].mean()
    hot_zips     = zip_mean_dom.nsmallest(HOT_MARKET_COUNT).index
    slow_zips    = zip_mean_dom.nlargest(SLOW_MARKET_COUNT).index

    # HOT_MARKET_COUNT zips — all DOM rows forced below HOT_DOM_CEILING
    hot_mask = df["zip_code"].isin(hot_zips)
    df.loc[hot_mask, "days_on_market"] = rng.integers(DAYS_ON_MARKET_RANGE[0], HOT_DOM_CEILING, size=hot_mask.sum())

    # Cap other (non-hot, non-slow) zips at SLOW_DOM_FLOOR so injection is the sole
    # source of DOM > SLOW_DOM_FLOOR — the new _compute_dom() formula can naturally
    # produce high DOM for cold markets, which would break the exact-count AC otherwise.
    other_mask = ~df["zip_code"].isin(hot_zips) & ~df["zip_code"].isin(slow_zips)
    overflow   = other_mask & (df["days_on_market"] > SLOW_DOM_FLOOR)
    df.loc[overflow, "days_on_market"] = SLOW_DOM_FLOOR

    # SLOW_MARKET_COUNT zips — all DOM rows forced above SLOW_DOM_FLOOR
    slow_mask = df["zip_code"].isin(slow_zips)
    df.loc[slow_mask, "days_on_market"] = rng.integers(
        SLOW_DOM_FLOOR + 1, DAYS_ON_MARKET_RANGE[1] + 1, size=slow_mask.sum()
    )
    return df



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
        "median_investment_score":   0.0,    # placeholder — filled after compute_investment_score()
        "median_sale_price":         float(df["median_sale_price"].median()),
        "median_net_yield":          0.0,    # placeholder — updated after engineer_features()
        "top_metro_appreciation":    str(metro_appr.idxmax()),
        "best_yield_metro":          str(metro_yield.idxmax()),
        "is_finalized":              False,
        "loaded_metros":             sorted(df["metro"].unique().tolist()),
    }

    missing_keys = REQUIRED_POP_STAT_KEYS - set(pop_stats.keys())
    if missing_keys:
        raise ValueError(f"pop_stats is missing keys: {missing_keys}")
    if pop_stats["top_metro_appreciation"] not in METROS:
        raise ValueError(f"top_metro_appreciation '{pop_stats['top_metro_appreciation']}' not in METROS")
    if pop_stats["best_yield_metro"] not in METROS:
        raise ValueError(f"best_yield_metro '{pop_stats['best_yield_metro']}' not in METROS")

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
    if df.shape[0] != expected_rows:
        raise ValueError(f"Expected {expected_rows} rows, got {df.shape[0]}")
    if df.isnull().sum().sum() != 0:
        raise ValueError("DataFrame contains NaN values after generation")
    if not (df["median_sale_price"] >= p["price_floor"]).all():
        raise ValueError(f"median_sale_price contains values below price_floor ({p['price_floor']})")
    if not (df["fair_market_rent_2br"] >= p["rent_floor"]).all():
        raise ValueError(f"fair_market_rent_2br contains values below rent_floor ({p['rent_floor']})")
    if not (df["median_household_income"] >= p["income_floor"]).all():
        raise ValueError(f"median_household_income contains values below income_floor ({p['income_floor']})")

    validate_schema(df)
    df = df.sort_values(["metro", "zip_code", "month"]).reset_index(drop=True)

    # Inject before the 12m-lag backfill so appreciation_rate is final when
    # back-calculating prior prices for months 1–12 of each zip.
    df = _inject_market_patterns(df, rng)

    # 12-month lag price: actual shifted value where available; for the first 12 months of each
    # zip (where no prior-year row exists), back-calculate from appreciation_rate (%).
    # appreciation_rate is never overwritten by engineer_features() — no order-of-ops risk.
    #
    # LEAKAGE AUDIT — WARN (accepted): for months 1–12 of each zip, the shifted
    # price does not exist, so median_sale_price_12m_ago is derived algebraically
    # from appreciation_rate.  This means yoy_appreciation ≈ appreciation_rate
    # for those rows (engineer_features() computes yoy from the same lag column).
    # appreciation_rate is a time-invariant zip label set before any ML training,
    # not a future-derived value, so no real-world leakage risk exists.  This is
    # a synthetic-data constraint: a real dataset would have 24+ months of history
    # and the back-calculation path would never be reached.
    df["median_sale_price_12m_ago"] = df.groupby("zip_code")["median_sale_price"].shift(12)
    early = df["median_sale_price_12m_ago"].isna()
    df.loc[early, "median_sale_price_12m_ago"] = np.round(
        df.loc[early, "median_sale_price"] / (1 + df.loc[early, "appreciation_rate"] / 100),
        PRICE_ROUND_DP,
    )

    pop_stats = _compute_pop_stats(df)
    return df, pop_stats


def load_csv_data(source: str | BinaryIO) -> Tuple[pd.DataFrame, dict]:
    """
    Load and validate a real estate CSV.
    Returns the same (df, pop_stats) tuple as generate_synthetic_data().
    Accepts either a file-path string or a file-like object (e.g. io.BytesIO).
    Raises ValueError with a clear message if required columns are missing.
    """
    if isinstance(source, str):
        size_mb = os.path.getsize(source) / (1024 * 1024)
    else:
        source.seek(0, 2)
        size_mb = source.tell() / (1024 * 1024)
        source.seek(0)
    if size_mb > MAX_CSV_SIZE_MB:
        raise ValueError(
            f"CSV file is {size_mb:.1f} MB, which exceeds the {MAX_CSV_SIZE_MB} MB limit. "
            "Split the file or increase MAX_CSV_SIZE_MB in config.py."
        )

    df = pd.read_csv(source)

    # Reuse existing validator: required columns, month format, zip/month duplicates
    validate_csv(df)

    # ── Type coercion — bad CSV data should fail loudly ──────────────────────
    numeric_cols = [
        "median_sale_price", "price_per_sqft", "days_on_market",
        "homes_sold", "median_household_income", "fair_market_rent_2br",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[numeric_cols].isnull().any().any():
        bad = df[numeric_cols].isnull().sum()
        raise ValueError(
            f"Non-numeric values found after coercion: {bad[bad > 0].to_dict()}"
        )

    # Optional columns present in the CSV must also be numeric — a present-but-bad
    # optional column is just as dangerous as a bad required column downstream.
    optional_numeric = [
        "bachelor_rate", "list_to_sale_ratio", "inventory_level",
        "appreciation_rate", "median_list_price", "yoy_appreciation",
    ]
    for col in optional_numeric:
        if col not in df.columns:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
        bad_count = df[col].isnull().sum()
        if bad_count:
            raise ValueError(
                f"Non-numeric values found in optional column '{col}': {bad_count} bad value(s)"
            )

    # Zip code: string, zero-padded to 5 digits
    df["zip_code"] = df["zip_code"].astype(str).str.zfill(5)

    # Unknown metros: warn and filter rather than hard-reject, so a CSV with
    # a mix of known and unknown metros still loads the known rows.
    unknown = set(df["metro"].unique()) - set(METROS.keys())
    if unknown:
        logging.warning(
            "load_csv_data: ignoring %d unknown metro value(s): %s",
            len(unknown), sorted(unknown),
        )
        df = df[~df["metro"].isin(unknown)].reset_index(drop=True)
    if df.empty:
        raise ValueError(
            f"All rows were filtered out after removing unknown metro values: {sorted(unknown)}. "
            "Ensure the CSV 'metro' column uses names from config.METROS."
        )

    # ── Optional column defaults ─────────────────────────────────────────────
    if "bachelor_rate" not in df.columns:
        df["bachelor_rate"] = 0.30

    if "list_to_sale_ratio" not in df.columns:
        df["list_to_sale_ratio"] = 0.97

    if "inventory_level" not in df.columns:
        df["inventory_level"] = 100

    if "appreciation_rate" not in df.columns:
        if "median_sale_price_12m_ago" in df.columns:
            p_12m = pd.to_numeric(df["median_sale_price_12m_ago"], errors="coerce").fillna(
                df["median_sale_price"]
            )
            df["appreciation_rate"] = np.where(
                p_12m > 0,
                (df["median_sale_price"] - p_12m) / p_12m * 100,
                0.0,
            )
        else:
            df["appreciation_rate"] = 0.0

    if "median_list_price" not in df.columns:
        df["median_list_price"] = np.round(
            df["median_sale_price"] * df["list_to_sale_ratio"], PRICE_ROUND_DP
        )

    # median_sale_price_12m_ago required by engineer_features()
    if "median_sale_price_12m_ago" not in df.columns:
        df["median_sale_price_12m_ago"] = np.round(
            df["median_sale_price"] / (1 + df["appreciation_rate"] / 100), PRICE_ROUND_DP
        )

    pop_stats = _compute_pop_stats(df)
    return df, pop_stats


def get_price_history_df(df: pd.DataFrame, zip_code: str) -> pd.DataFrame:
    """
    Return a long-format price history DataFrame for a single zip.
    Columns: month (YYYY-MM str), median_sale_price (float), zip_code (str).
    Rows are sorted oldest → newest by month.
    Used by create_price_history() in charts.py.
    Raises ValueError if zip_code is not found in df.
    """
    mask = df["zip_code"] == zip_code
    if not mask.any():
        raise ValueError(f"zip_code '{zip_code}' not found in DataFrame.")
    zip_rows = df.loc[mask].sort_values("month")
    return pd.DataFrame({
        "month":             zip_rows["month"].tolist(),
        "median_sale_price": zip_rows["median_sale_price"].tolist(),
        "zip_code":          zip_code,
    })


# ── Public API ────────────────────────────────────────────────────────────────
# App modules call get_data() for the Streamlit-cached version.
# No caller should call generate_synthetic_data() or load_csv_data() directly.

@st.cache_data
def _get_data_cached(
    file_path: str | None,
    file_mtime: float,      # noqa: ARG001 — cache-key discriminator only; not used in body
    file_size: int,         # noqa: ARG001 — cache-key discriminator only; not used in body
    file_head_sha256: str,  # noqa: ARG001 — cache-key discriminator only; not used in body
) -> Tuple[pd.DataFrame, dict]:
    if file_path is not None:
        return load_csv_data(file_path)
    return generate_synthetic_data()


@st.cache_data
def _get_uploaded_data_cached(
    file_id: str,   # noqa: ARG001 — Streamlit assigns a new file_id per upload; sole cache discriminator
    content: bytes,
) -> Tuple[pd.DataFrame, dict]:
    return load_csv_data(io.BytesIO(content))


# Stores (mtime, size, sha256_head) per path so the 64 KB read is skipped
# when mtime and size are unchanged between calls.
_path_key_cache: dict[str, tuple[float, int, str]] = {}


def get_data(source=None) -> Tuple[pd.DataFrame, dict]:
    """Return (df, pop_stats) from synthetic data, a file path, or an UploadedFile.

    source=None              → synthetic data
    source=str               → load from file path (cache key: mtime + size + head hash)
    source=st.UploadedFile   → load from in-memory upload (cache key: file_id)
    """
    if source is None:
        return _get_data_cached(None, 0.0, 0, "")
    if isinstance(source, str):
        s      = os.stat(source)
        cached = _path_key_cache.get(source)
        if cached and cached[0] == s.st_mtime and cached[1] == s.st_size:
            head_hash = cached[2]
        else:
            with open(source, "rb") as fh:
                head_hash = hashlib.sha256(fh.read(65536)).hexdigest()
            _path_key_cache[source] = (s.st_mtime, s.st_size, head_hash)
        return _get_data_cached(source, s.st_mtime, s.st_size, head_hash)
    # Streamlit UploadedFile: use file_id as the sole cache discriminator
    return _get_uploaded_data_cached(source.file_id, source.getvalue())


if __name__ == "__main__":
    df, pop_stats = generate_synthetic_data()
    print("Shape:", df.shape)
    print(df.head(10).to_string())
    print("\npop_stats:")
    for k, v in pop_stats.items():
        print(f"  {k}: {v}")

    assert not pop_stats["is_finalized"], "generate_synthetic_data() must return unfinalized pop_stats"
    print("\nAssertion passed: pop_stats is unfinalized after generate_synthetic_data()")
