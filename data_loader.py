import numpy as np
import pandas as pd

from config import METROS, METRO_ZIPS


def generate_synthetic_data() -> pd.DataFrame:
    """Synthetic stand-in for production data. Replace with a real feed (MLS, Zillow API, ATTOM, CoreLogic) before going live."""
    rng = np.random.default_rng(42)

    rows = []

    for metro in METROS:
        for zip_code in METRO_ZIPS[metro]:
            median_sale_price = round(rng.uniform(150_000, 900_000), 2)
            price_per_sqft    = round(median_sale_price / rng.uniform(400, 2500), 2)
            days_on_market    = int(rng.integers(5, 121))
            homes_sold        = int(rng.integers(5, 201))
            median_household_income = round(rng.uniform(35_000, 180_000), 2)
            fair_market_rent_2br    = round(rng.uniform(700, 3_500), 2)

            rows.append({
                "zip_code":                zip_code,
                "metro":                   metro,
                "median_sale_price":       median_sale_price,
                "price_per_sqft":          price_per_sqft,
                "days_on_market":          days_on_market,
                "homes_sold":              homes_sold,
                "median_household_income": median_household_income,
                "fair_market_rent_2br":    fair_market_rent_2br,
            })

    df = pd.DataFrame(rows)

    expected = sum(len(v) for v in METRO_ZIPS.values())
    assert df.shape[0] == expected, f"Expected {expected} rows, got {df.shape[0]}"
    assert df.isnull().sum().sum() == 0, "DataFrame contains NaN values"
    assert (df["median_sale_price"] > 0).all(), "Price column contains zeros"

    return df


if __name__ == "__main__":
    df = generate_synthetic_data()
    print("Shape:", df.shape)
    print(df.head())
