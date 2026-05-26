import pandas as pd

from config import GRADE_THRESHOLDS, INVESTMENT_SCORE_WEIGHTS as W
from feature_engineering import _minmax

_COMPONENT_COLS = [
    "score_appreciation",
    "score_yield",
    "score_heat",
    "score_neighborhood",
    "score_velocity",
    "score_net_yield",
]


def assign_grade(score: float) -> str:
    """Map a 0–100 investment score to a letter grade."""
    for entry in GRADE_THRESHOLDS:
        if score >= entry["min_score"]:
            return entry["letter"]
    return "F"


def compute_investment_score(df: pd.DataFrame) -> pd.DataFrame:
    """Add investment score, grade, and 6 weighted component columns to df.

    Returns a copy of df — input is never mutated.
    All six components are min-max scaled to 0–100 before weighting.
    """
    df = df.copy()
    df["score_appreciation"] = _minmax(df["yoy_appreciation"])  * W["appreciation"]
    df["score_yield"]        = _minmax(df["gross_rental_yield"]) * W["yield"]
    df["score_heat"]         = _minmax(df["market_heat_index"])  * W["heat"]
    df["score_neighborhood"] = _minmax(df["neighborhood_score"]) * W["neighborhood"]
    df["score_velocity"]     = _minmax(df["price_velocity"])     * W["velocity"]
    df["score_net_yield"]    = _minmax(df["net_rental_yield"])   * W["net_yield"]
    raw_sum = df[_COMPONENT_COLS].sum(axis=1)
    df["investment_score"] = _minmax(raw_sum).clip(0, 100)
    df["investment_grade"]   = df["investment_score"].apply(assign_grade)
    return df


if __name__ == "__main__":
    from data_loader import generate_synthetic_data
    from feature_engineering import engineer_features

    raw, ps = generate_synthetic_data()
    df, ps  = engineer_features(raw, ps)
    df      = compute_investment_score(df)
    ps["median_investment_score"] = float(df["investment_score"].median())

    assert df["investment_score"].between(0, 100).all(), "investment_score out of [0, 100]"
    assert set(df["investment_grade"]) == {"A", "B", "C", "D", "F"}, "Not all grades present"
    assert all(c in df.columns for c in _COMPONENT_COLS), "Missing component columns"
    assert ps["median_investment_score"] != 0.0, "pop_stats placeholder not updated"

    # Grade distribution on the latest month (one row per zip code)
    latest = df[df["month"] == df["month"].max()]
    dist   = latest["investment_grade"].value_counts().sort_index()
    print("Grade distribution (latest month, 200 zips):")
    for grade, count in dist.items():
        print(f"  {grade}: {count} zip codes ({count / len(latest) * 100:.1f}%)")

    print(f"\nMedian investment score: {ps['median_investment_score']:.1f}")
    print("All assertions passed.")
