import numpy as np
import pandas as pd

from config import METROS


def generate_synthetic_data() -> pd.DataFrame:
    np.random.seed(42)

    n_zips = 200
    zips_per_metro = n_zips // len(METROS)  # 20 per metro

    rows = []
    zip_counter = 10001

    for metro in METROS:
        for _ in range(zips_per_metro):
            zip_code = str(zip_counter).zfill(5)
            zip_counter += 1

            median_sale_price = round(np.random.uniform(150_000, 900_000), 2)
            price_per_sqft    = round(median_sale_price / np.random.uniform(400, 2500), 2)
            days_on_market    = int(np.random.randint(5, 121))
            homes_sold        = int(np.random.randint(5, 201))
            median_household_income = round(np.random.uniform(35_000, 180_000), 2)
            fair_market_rent_2br    = round(np.random.uniform(700, 3_500), 2)

            rows.append({
                "zip_code":               zip_code,
                "metro":                  metro,
                "median_sale_price":      median_sale_price,
                "price_per_sqft":         price_per_sqft,
                "days_on_market":         days_on_market,
                "homes_sold":             homes_sold,
                "median_household_income": median_household_income,
                "fair_market_rent_2br":   fair_market_rent_2br,
            })

    df = pd.DataFrame(rows)

    assert df.shape[0] == 200, f"Expected 200 rows, got {df.shape[0]}"
    assert df.isnull().sum().sum() == 0, "DataFrame contains NaN values"
    assert (df["median_sale_price"] > 0).all(), "Price column contains zeros"

    return df


if __name__ == "__main__":
    df = generate_synthetic_data()
    print("Shape:", df.shape)
    print(df.head())
