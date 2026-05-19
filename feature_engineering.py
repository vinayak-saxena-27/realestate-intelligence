import numpy as np
import pandas as pd

from config import HEAT_INDEX_COMPONENTS, SYNTH_PARAMS


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


if __name__ == "__main__":
    from data_loader import generate_synthetic_data

    df = generate_synthetic_data()
    df["yoy_appreciation"]  = compute_yoy_appreciation(df)
    df["price_velocity"]    = compute_price_velocity(df)
    df["market_heat_index"] = compute_market_heat_index(df)

    assert (df["market_heat_index"].between(0, 100)).all(), "market_heat_index out of [0, 100]"

    for feat in ["yoy_appreciation", "price_velocity", "market_heat_index"]:
        s = df[feat].agg(["min", "max", "mean"])
        print(f"{feat:22s}  min={s['min']:8.4f}  max={s['max']:8.4f}  mean={s['mean']:8.4f}")
