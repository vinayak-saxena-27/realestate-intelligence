import logging
import numpy as np
import pandas as pd
import streamlit as st

from config import (
    HEAT_INDEX_COMPONENTS,
    NEIGHBORHOOD_WEIGHTS,
    NET_YIELD_EXPENSE_RATIO,
    NORMALIZATION_SCOPE,
    SYNTH_PARAMS,
)


def assert_pop_stats_finalized(pop_stats: dict) -> None:
    """Raise ValueError if pop_stats has not been finalized by engineer_features().

    Call at the top of any function that reads pop_stats for scoring or display.
    """
    if not pop_stats.get("is_finalized", False):
        raise ValueError(
            "pop_stats is not finalized: median fields still contain placeholders. "
            "Call engineer_features(df, pop_stats) before using pop_stats for scoring or display."
        )


def compute_yoy_appreciation(df: pd.DataFrame) -> pd.Series:
    p_now = df["median_sale_price"]
    p_12m = df["median_sale_price_12m_ago"]
    return pd.Series(
        np.where(p_12m > 0, (p_now - p_12m) / p_12m * 100, 0.0),
        index=df.index,
    )


def compute_price_velocity(df: pd.DataFrame) -> pd.Series:
    if not df.groupby("zip_code")["month"].apply(lambda x: x.is_monotonic_increasing).all():
        raise ValueError("compute_price_velocity requires df sorted by (zip_code, month)")
    w = int(SYNTH_PARAMS["velocity_window"])

    raw = (
        df.groupby("zip_code")["median_sale_price"]
        .transform(lambda x: x.pct_change().mul(100).rolling(w).mean())
    )

    # Forward-fill within each zip to bridge small mid-series gaps, capped at w rows.
    # Leading NaN (positions 0..w-1) have no prior value, so ffill leaves them as NaN.
    velocity = raw.groupby(df["zip_code"]).transform(lambda x: x.ffill(limit=w))

    # Positions 0..w-1 per zip are the expected leading window; any remaining NaN
    # outside that range came from a price gap wider than velocity_window.
    leading_mask = df.groupby("zip_code").cumcount() < w
    mid_series_nan = velocity.isna() & ~leading_mask
    n_nan = int(mid_series_nan.sum())
    if n_nan:
        zips  = df.loc[mid_series_nan, "zip_code"].unique().tolist()
        logging.warning(
            "compute_price_velocity: %d mid-series NaN in %d zip(s) after ffill — "
            "price gaps wider than velocity_window (%d): %s",
            n_nan, len(zips), w, zips,
        )

    return velocity.fillna(0.0)


def compute_volume_trend(df: pd.DataFrame) -> pd.Series:
    # 3-month rolling mean of MoM % change in homes_sold per zip.
    # Positive: accelerating transaction volume; negative: contracting. Source: homes_sold.
    if not df.groupby("zip_code")["month"].apply(lambda x: x.is_monotonic_increasing).all():
        raise ValueError("compute_volume_trend requires df sorted by (zip_code, month)")
    w = int(SYNTH_PARAMS["velocity_window"])

    raw = (
        df.groupby("zip_code")["homes_sold"]
        .transform(lambda x: x.pct_change().mul(100).rolling(w).mean())
    )

    # Positions 0..w-1 per zip are the expected leading window (no prior data).
    # Any remaining NaN outside that range came from a homes_sold gap wider than w.
    leading_mask = df.groupby("zip_code").cumcount() < w
    mid_series_nan = raw.isna() & ~leading_mask
    n_nan = int(mid_series_nan.sum())
    if n_nan:
        zips = df.loc[mid_series_nan, "zip_code"].unique().tolist()
        logging.warning(
            "compute_volume_trend: %d mid-series NaN in %d zip(s) — "
            "homes_sold gaps wider than velocity_window (%d): %s",
            n_nan, len(zips), w, zips,
        )

    return raw.fillna(0.0)


def _minmax(series: pd.Series, groups: pd.Series | None = None) -> pd.Series:
    """Min-max scale `series` to [0, 100]. Returns 50.0 for constant input.

    When `groups` is provided, scaling is applied independently within each group.
    """
    if groups is None:
        lo, hi = series.min(), series.max()
    else:
        g  = series.groupby(groups)
        lo = g.transform("min")
        hi = g.transform("max")
    return pd.Series(
        np.where(hi > lo, (series - lo) / (hi - lo) * 100, 50.0),
        index=series.index,
    )


def compute_market_heat_index(df: pd.DataFrame) -> pd.Series:
    w      = HEAT_INDEX_COMPONENTS
    groups = df["metro"] if NORMALIZATION_SCOPE == "per_metro" else None
    dom_inv  = 100 - _minmax(df["days_on_market"],    groups)
    sold     = _minmax(df["homes_sold"],               groups)
    velocity = _minmax(df["price_velocity"],           groups)
    lts      = _minmax(df["list_to_sale_ratio"],       groups)
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
    w      = NEIGHBORHOOD_WEIGHTS
    groups = df["metro"] if NORMALIZATION_SCOPE == "per_metro" else None
    inc  = _minmax(df["median_household_income"], groups)
    edu  = _minmax(df["bachelor_rate"],           groups)  # guaranteed by data_loader PRD 2
    hval = _minmax(df["median_sale_price"],       groups)
    return inc * w["income"] + edu * w["education"] + hval * w["home_value"]


_REQUIRED_COLUMNS = [
    "zip_code",              # groupby key for price_velocity and volume_trend
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

    Returns (df, pop_stats) where df has 7 new feature columns and pop_stats
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
    df["volume_trend"]       = compute_volume_trend(df)
    df["market_heat_index"]  = compute_market_heat_index(df)
    df["gross_rental_yield"] = compute_gross_rental_yield(df)
    df["net_rental_yield"]   = compute_net_rental_yield(df)
    df["neighborhood_score"] = compute_neighborhood_score(df)

    pop_stats["median_yoy_appreciation"]   = float(df["yoy_appreciation"].median())
    pop_stats["median_gross_rental_yield"] = float(df["gross_rental_yield"].median())
    pop_stats["median_market_heat_index"]  = float(df["market_heat_index"].median())
    pop_stats["median_neighborhood_score"] = float(df["neighborhood_score"].median())
    pop_stats["median_days_on_market"]     = float(df["days_on_market"].median())
    pop_stats["is_finalized"]              = True
    return df, pop_stats


if __name__ == "__main__":
    from data_loader import generate_synthetic_data

    raw, ps = generate_synthetic_data()
    raw_ps   = ps.copy()   # snapshot before finalization
    feature_cols = [
        "yoy_appreciation", "price_velocity", "volume_trend",
        "market_heat_index", "gross_rental_yield", "net_rental_yield", "neighborhood_score",
    ]

    # engineer_features must not mutate the input df
    df, ps = engineer_features(raw, ps)
    assert set(feature_cols).issubset(df.columns), "Missing feature columns"
    assert df.isnull().sum().sum() == 0, "NaN values in engineered df"
    assert "yoy_appreciation" not in raw.columns, "Input df was mutated"

    # pop_stats must be unfinalized before engineer_features() and finalized after
    assert not raw_ps["is_finalized"], "raw pop_stats should be unfinalized"
    assert ps["is_finalized"],         "engineer_features() must set is_finalized=True"

    # all five median keys must be set to real floats by engineer_features
    _median_keys = [
        "median_yoy_appreciation", "median_gross_rental_yield", "median_market_heat_index",
        "median_neighborhood_score", "median_days_on_market",
    ]
    for _key in _median_keys:
        assert _key in ps,                    f"missing key: {_key}"
        assert isinstance(ps[_key], float),   f"{_key} should be float"
        assert ps[_key] == ps[_key],          f"{_key} is NaN"  # NaN != NaN
    assert ps["median_market_heat_index"]  != 50.0, "heat index placeholder not replaced"
    assert ps["median_neighborhood_score"] != 50.0, "neighborhood score placeholder not replaced"

    # assert_pop_stats_finalized must pass on a finalized dict and raise on an unfinalized one
    assert_pop_stats_finalized(ps)
    try:
        assert_pop_stats_finalized(raw_ps)
        raise AssertionError("Should have raised ValueError for unfinalized pop_stats")
    except ValueError as e:
        print(f"ValueError correctly raised: {e}")

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
    for feat in ["yoy_appreciation", "price_velocity", "volume_trend", "market_heat_index"]:
        s = df[feat].agg(["min", "max", "mean"])
        print(f"{feat:24s}  min={s['min']:8.4f}  max={s['max']:8.4f}  mean={s['mean']:8.4f}")

    print("\n--- PRD 2 features ---")
    for feat in ["gross_rental_yield", "net_rental_yield", "neighborhood_score"]:
        s = df[feat].agg(["min", "max", "mean"])
        print(f"{feat:24s}  min={s['min']:8.4f}  max={s['max']:8.4f}  mean={s['mean']:8.4f}")

    print("\npop_stats after engineer_features:")
    for k, v in ps.items():
        print(f"  {k}: {v}")

    # ── per_metro scope ──────────────────────────────────────────────────────
    # Rebind the module global so compute_* functions pick up the new scope.
    NORMALIZATION_SCOPE = "per_metro"
    try:
        heat_pm = compute_market_heat_index(df)
        nbr_pm  = compute_neighborhood_score(df)

        assert heat_pm.between(0, 100).all(),   "per_metro heat_index outside [0, 100]"
        assert nbr_pm.between(0, 100).all(),    "per_metro neighborhood_score outside [0, 100]"
        assert heat_pm.isna().sum() == 0,       "NaN in per_metro heat_index"
        assert nbr_pm.isna().sum() == 0,        "NaN in per_metro neighborhood_score"
        # Synthetic metros have different price/DOM ranges, so per_metro scores differ
        # from global scores on the same data.
        assert not (heat_pm == df["market_heat_index"]).all(), \
            "per_metro and global heat_index are identical — scope has no effect"
        assert not (nbr_pm  == df["neighborhood_score"]).all(), \
            "per_metro and global neighborhood_score are identical — scope has no effect"

        print("\n--- per_metro scope ---")
        for feat, s in [("heat_index (pm)", heat_pm), ("neighborhood_score (pm)", nbr_pm)]:
            print(f"{feat:28s}  min={s.min():8.4f}  max={s.max():8.4f}  mean={s.mean():8.4f}")
    finally:
        NORMALIZATION_SCOPE = "global"
