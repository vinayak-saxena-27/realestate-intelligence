import pandas as pd

from config import GRADE_THRESHOLDS, INVESTMENT_SCORE_WEIGHTS as W
from feature_engineering import assert_pop_stats_finalized

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


def compute_investment_score(df: pd.DataFrame, pop_stats: dict) -> pd.DataFrame:
    """Add investment score, grade, and 6 weighted component columns to df.

    Returns a copy of df — input is never mutated.
    Scoring is done on the latest-month snapshot (200 zips) using percentile rank
    so each zip is compared to contemporaries, not to the full time-series.
    Percentile rank is outlier-immune: extreme appreciation outliers can't distort
    the whole distribution the way min-max normalisation would.
    Scores are then broadcast back to all months by zip_code so charts work correctly.
    pop_stats must be finalized by engineer_features() before calling this function.
    """
    assert_pop_stats_finalized(pop_stats)
    df = df.copy()

    latest = df[df["month"] == df["month"].max()].copy()

    def _rank(s: pd.Series) -> pd.Series:
        return s.rank(pct=True, method="average") * 100

    latest["score_appreciation"] = _rank(latest["yoy_appreciation"])  * W["appreciation"]
    latest["score_yield"]        = _rank(latest["gross_rental_yield"]) * W["yield"]
    latest["score_heat"]         = _rank(latest["market_heat_index"])  * W["heat"]
    latest["score_neighborhood"] = _rank(latest["neighborhood_score"]) * W["neighborhood"]
    latest["score_velocity"]     = _rank(latest["price_velocity"])     * W["velocity"]
    latest["score_net_yield"]    = _rank(latest["net_rental_yield"])   * W["net_yield"]

    raw_sum = latest[_COMPONENT_COLS].sum(axis=1)
    latest["investment_score"] = raw_sum.clip(0, 100)
    latest["investment_grade"] = latest["investment_score"].apply(assign_grade)

    # Broadcast zip-level scores to all months — a zip's score reflects its
    # standing among contemporaries at the latest snapshot, not cross-time rank.
    zip_scores = latest.set_index("zip_code")[_COMPONENT_COLS + ["investment_score", "investment_grade"]]
    for col in zip_scores.columns:
        df[col] = df["zip_code"].map(zip_scores[col])

    return df


if __name__ == "__main__":
    from data_loader import generate_synthetic_data
    from feature_engineering import engineer_features

    raw, ps = generate_synthetic_data()
    df, ps  = engineer_features(raw, ps)
    df      = compute_investment_score(df, ps)
    ps["median_investment_score"] = float(df["investment_score"].median())

    assert df["investment_score"].between(0, 100).all(), "investment_score out of [0, 100]"
    assert set(df["investment_grade"]) == {"A", "B", "C", "D", "F"}, "Not all grades present"
    assert all(c in df.columns for c in _COMPONENT_COLS), "Missing component columns"
    assert ps["median_investment_score"] != 0.0, "pop_stats placeholder not updated"

    # Guard must fire on unfinalized pop_stats
    try:
        compute_investment_score(df, {"is_finalized": False})
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        print(f"ValueError correctly raised: {e}")

    # Grade distribution on the latest month (one row per zip code)
    latest = df[df["month"] == df["month"].max()]
    dist   = latest["investment_grade"].value_counts().sort_index()
    print("Grade distribution (latest month, 200 zips):")
    for grade, count in dist.items():
        print(f"  {grade}: {count} zip codes ({count / len(latest) * 100:.1f}%)")

    print(f"\nMedian investment score: {ps['median_investment_score']:.1f}")
    print("All assertions passed.")
