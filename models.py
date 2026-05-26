import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score

from config import RF_FEATURES, RF_MAX_DEPTH, RF_N_ESTIMATORS, RF_N_JOBS, RNG_SEED


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
