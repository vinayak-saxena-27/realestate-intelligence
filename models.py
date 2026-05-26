import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

from config import (
    KMEANS_FEATURES, KMEANS_K, KMEANS_MAX_ITER, KMEANS_N_INIT,
    RF_FEATURES, RF_MAX_DEPTH, RF_N_ESTIMATORS, RF_N_JOBS, RNG_SEED,
)


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

    X = df_model[RF_FEATURES]
    y = df_model["target_price_6m"]

    split = int(len(df_model) * 0.8)
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
