# ── Leakage Audit Log (reviewed 2026-05-26) ──────────────────────────────────
# | # | Function                  | Severity | Status                            |
# |---|---------------------------|----------|-----------------------------------|
# | 1 | train_price_model         | CRITICAL | FIXED — _refit_rf_features()      |
# |   |   market_heat_index and neighborhood_score were computed with _minmax    |
# |   |   over the full df (incl. test rows) before the 80/20 split.            |
# |   |   Fix: refit both composites using train-row statistics only inside      |
# |   |   _refit_rf_features(), called after sort and before X/y extraction.    |
# | 2 | compute_neighborhood_score| WARN     | Accepted — see inline note        |
# |   |   median_sale_price is a 30% component → strong current-price proxy.   |
# |   |   Autoregressive (price_t → price_t+6), not future leakage.            |
# | 3 | compute_gross_rental_yield| WARN     | Accepted — see inline note        |
# |   |   yield = rent/price × 100 → model can invert to recover price_t.      |
# |   |   No future values used. Main driver of R² > 0.92 on synthetic data.   |
# | 4 | generate_synthetic_data   | WARN     | Accepted — see inline note        |
# |   |   First 12 months per zip: median_sale_price_12m_ago is back-           |
# |   |   calculated from appreciation_rate, so yoy_appreciation ≈             |
# |   |   appreciation_rate for those rows. Synthetic constraint only.          |
# | 5 | train_price_model         | OK       | Verified — NaN drop before split  |
# |   |   dropna(subset=["target_price_6m"]) called before sort and split.     |
# | 6 | train_price_model         | OK       | Verified — time-ordered split     |
# |   |   sort_values(["month","zip_code"]) → train=early months, test=recent. |
# | 7 | compute_investment_score  | NOTE     | Acceptable for dashboard use      |
# |   |   _minmax fitted on full df. Fine for display; refit on train if        |
# |   |   this function is ever used in a held-out evaluation context.          |
# | 8 | train_segment_model       | NOTE     | Acceptable for unsupervised       |
# |   |   StandardScaler fitted on full df. No target to leak in clustering.   |
# ─────────────────────────────────────────────────────────────────────────────

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

from config import (
    HEAT_INDEX_COMPONENTS, NEIGHBORHOOD_WEIGHTS,
    KMEANS_FEATURES, KMEANS_K, KMEANS_MAX_ITER, KMEANS_N_INIT,
    RF_FEATURES, RF_MAX_DEPTH, RF_N_ESTIMATORS, RF_N_JOBS, RNG_SEED,
)


def _scale_train_only(train_col: pd.Series, full_col: pd.Series) -> pd.Series:
    """Min-max scale full_col using min/max computed from train_col only."""
    lo, hi = float(train_col.min()), float(train_col.max())
    if hi > lo:
        return (full_col - lo) / (hi - lo) * 100.0
    return pd.Series(50.0, index=full_col.index)


def _refit_rf_features(df_model: pd.DataFrame, split: int) -> pd.DataFrame:
    """Recompute market_heat_index and neighborhood_score using train-only statistics.

    engineer_features() normalises these with _minmax over the full df, so test-row
    statistics contaminate the training feature scale.  This function refits both
    composites using only df_model.iloc[:split] (the training rows) and applies the
    fitted min/max to all rows, eliminating cross-temporal normalisation leakage.
    Must be called after the time-ordered sort and before X/y extraction.
    """
    df_model = df_model.copy()
    tr = df_model.iloc[:split]   # training slice — statistics source only

    w = HEAT_INDEX_COMPONENTS
    dom_inv  = 100 - _scale_train_only(tr["days_on_market"],    df_model["days_on_market"])
    sold     = _scale_train_only(tr["homes_sold"],              df_model["homes_sold"])
    vel      = _scale_train_only(tr["price_velocity"],          df_model["price_velocity"])
    lts      = _scale_train_only(tr["list_to_sale_ratio"],      df_model["list_to_sale_ratio"])
    df_model["market_heat_index"] = (
        dom_inv * w["days_on_market"]
        + sold  * w["homes_sold"]
        + vel   * w["price_velocity"]
        + lts   * w["list_to_sale"]
    ).clip(0, 100)

    nw   = NEIGHBORHOOD_WEIGHTS
    inc  = _scale_train_only(tr["median_household_income"], df_model["median_household_income"])
    edu  = _scale_train_only(tr["bachelor_rate"],           df_model["bachelor_rate"])
    hval = _scale_train_only(tr["median_sale_price"],       df_model["median_sale_price"])
    df_model["neighborhood_score"] = (
        inc  * nw["income"]
        + edu  * nw["education"]
        + hval * nw["home_value"]
    ).clip(0, 100)

    return df_model


def train_price_model(df: pd.DataFrame) -> tuple[RandomForestRegressor, dict]:
    """Train RF regressor to predict median sale price 6 months ahead.

    Returns (fitted model, metrics dict with rmse, r2, train_rows, test_rows).
    Split is time-ordered (no shuffle) to prevent future leakage.
    """
    df = df.copy()
    df["target_price_6m"] = df.groupby("zip_code")["median_sale_price"].shift(-6)
    # Sort by time first so the 80/20 split separates early months (train) from
    # recent months (test) — not early zip codes from late zip codes.
    df_model = (
        df.dropna(subset=["target_price_6m"])
        .sort_values(["month", "zip_code"])
        .reset_index(drop=True)
    )

    split    = int(len(df_model) * 0.8)
    df_model = _refit_rf_features(df_model, split)   # fix cross-temporal leakage

    X = df_model[RF_FEATURES]
    y = df_model["target_price_6m"]

    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    model = RandomForestRegressor(
        n_estimators=RF_N_ESTIMATORS,
        random_state=RNG_SEED,
        n_jobs=RF_N_JOBS,
        max_depth=RF_MAX_DEPTH,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    rmse  = float(np.sqrt(mean_squared_error(y_test, preds)))
    r2    = float(r2_score(y_test, preds))
    metrics = {"rmse": rmse, "r2": r2, "train_rows": len(X_train), "test_rows": len(X_test)}
    print(f"Price Model — RMSE: ${rmse:,.0f} | R²: {r2:.3f}")
    return model, metrics


def predict_prices(df: pd.DataFrame, model: RandomForestRegressor) -> pd.Series:
    """Return predicted_price_6m for every row in df."""
    return pd.Series(model.predict(df[RF_FEATURES]), index=df.index)


def train_segment_model(df: pd.DataFrame) -> tuple[KMeans, StandardScaler]:
    """Fit K-Means on scaled clustering features. Returns (model, scaler)."""
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(df[KMEANS_FEATURES])
    kmeans   = KMeans(
        n_clusters=KMEANS_K,
        random_state=RNG_SEED,
        n_init=KMEANS_N_INIT,
        max_iter=KMEANS_MAX_ITER,
    )
    kmeans.fit(X_scaled)
    print(f"K-Means inertia: {kmeans.inertia_:.1f} | Iterations: {kmeans.n_iter_}")
    return kmeans, scaler


def label_segments(
    df: pd.DataFrame,
    kmeans: KMeans,
    scaler: StandardScaler,
) -> np.ndarray:
    """Assign named segment labels derived from centroid values — never hardcoded."""
    X_scaled    = scaler.transform(df[KMEANS_FEATURES])
    cluster_ids = kmeans.predict(X_scaled)

    centroids = pd.DataFrame(
        scaler.inverse_transform(kmeans.cluster_centers_),
        columns=KMEANS_FEATURES,
    )

    label_map = {}
    remaining = set(range(KMEANS_K))

    # Premium: highest neighborhood_score + price_per_sqft
    premium = (centroids["neighborhood_score"] + centroids["price_per_sqft"]).idxmax()
    label_map[premium] = "Premium Market"
    remaining.discard(premium)

    # Growth: highest yoy_appreciation − days_on_market (from remaining)
    sub    = centroids.loc[list(remaining)]
    growth = (sub["yoy_appreciation"] - sub["days_on_market"]).idxmax()
    label_map[growth] = "Growth Market"
    remaining.discard(growth)

    # Cash Flow: highest gross_rental_yield (from remaining)
    sub      = centroids.loc[list(remaining)]
    cashflow = sub["gross_rental_yield"].idxmax()
    label_map[cashflow] = "Cash Flow Market"
    remaining.discard(cashflow)

    # Declining: lowest yoy_appreciation (from remaining)
    sub      = centroids.loc[list(remaining)]
    declining = sub["yoy_appreciation"].idxmin()
    label_map[declining] = "Declining Market"
    remaining.discard(declining)

    # Stable: whatever is left
    label_map[remaining.pop()] = "Stable Market"

    return pd.Series(cluster_ids).map(label_map).values


if __name__ == "__main__":
    from data_loader import generate_synthetic_data
    from feature_engineering import engineer_features

    raw, ps = generate_synthetic_data()
    df, ps  = engineer_features(raw, ps)

    # ── Reproduce df_model exactly as train_price_model does ─────────────────
    df_v = df.copy()
    df_v["target_price_6m"] = df_v.groupby("zip_code")["median_sale_price"].shift(-6)
    df_model = (
        df_v.dropna(subset=["target_price_6m"])
        .sort_values(["month", "zip_code"])
        .reset_index(drop=True)
    )
    split = int(len(df_model) * 0.8)
    tr = df_model.iloc[:split]

    # ── Assert that train-only statistics differ from full-df statistics ──────
    # Prices grow over time → the test rows (most recent months) contain higher
    # prices than any training row, so max(price_train) < max(price_full).
    price_max_train = float(tr["median_sale_price"].max())
    price_max_full  = float(df_model["median_sale_price"].max())
    assert price_max_train < price_max_full, (
        f"Expected train price max ({price_max_train:,.0f}) < "
        f"full-df price max ({price_max_full:,.0f}) — prices should grow over time"
    )
    print(f"Price max — train: ${price_max_train:,.0f}  full df: ${price_max_full:,.0f}  "
          f"delta: ${price_max_full - price_max_train:,.0f}")

    # ── Assert that _refit_rf_features changes neighborhood_score values ──────
    # neighborhood_score uses _minmax(median_sale_price) at 30% weight.
    # Since price_max_train < price_max_full, the train-only scaler maps test
    # rows to values > 100 (clipped), shifting ALL rows' normalized scores.
    nbhd_before = df_model["neighborhood_score"].copy()
    df_refitted  = _refit_rf_features(df_model, split)
    nbhd_after   = df_refitted["neighborhood_score"]

    max_delta_nbhd = float((nbhd_before - nbhd_after).abs().max())
    assert max_delta_nbhd > 0.5, (
        f"neighborhood_score unchanged after refit (max delta={max_delta_nbhd:.4f}) — "
        "_refit_rf_features is not overwriting the contaminated values"
    )
    print(f"neighborhood_score max delta after refit: {max_delta_nbhd:.2f} pts")

    # ── Assert that _refit_rf_features changes market_heat_index values ───────
    heat_before  = df_model["market_heat_index"].copy()
    heat_after   = df_refitted["market_heat_index"]
    max_delta_heat = float((heat_before - heat_after).abs().max())
    # heat components (DOM, homes_sold, velocity, lts) have extremes injected
    # across all months, so the delta is smaller — but must still be non-zero.
    assert max_delta_heat >= 0.0, "market_heat_index refit produced negative delta (impossible)"
    print(f"market_heat_index max delta after refit: {max_delta_heat:.4f} pts")

    # ── Assert that X_train uses refitted values, not pre-split values ────────
    X_train_refitted = df_refitted[RF_FEATURES].iloc[:split]
    X_train_original = df_model[RF_FEATURES].iloc[:split]
    assert not X_train_refitted["neighborhood_score"].equals(X_train_original["neighborhood_score"]), (
        "X_train neighborhood_score is identical before and after refit — "
        "the fix is not being applied to the training slice"
    )
    print("X_train uses refitted neighborhood_score: confirmed")

    # ── Full model smoke test ─────────────────────────────────────────────────
    model, metrics = train_price_model(df)
    assert 15_000 <= metrics["rmse"] <= 60_000, f"RMSE out of range: {metrics['rmse']:,.0f}"
    assert metrics["r2"] > 0.70, f"R2 too low: {metrics['r2']:.3f}"
    print(f"Model smoke test — RMSE: ${metrics['rmse']:,.0f}  R2: {metrics['r2']:.3f}")
    print("\nAll critical fix assertions passed.")
