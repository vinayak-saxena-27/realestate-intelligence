import numpy as np
import pandas as pd

from config import FALLBACK_ANCHOR, METRO_ANCHORS, METROS, METRO_ZIPS, SYNTH_PARAMS


def generate_synthetic_data() -> pd.DataFrame:
    """Synthetic stand-in for production data. Replace with a real feed (MLS, Zillow API, ATTOM, CoreLogic) before going live."""
    rng = np.random.default_rng(42)
    p   = SYNTH_PARAMS

    rows = []

    for metro in METROS:
        anchor       = METRO_ANCHORS.get(metro, FALLBACK_ANCHOR)
        metro_price  = anchor["median_price"]
        metro_income = anchor["median_income"]

        for zip_code in METRO_ZIPS[metro]:
            # Single heat index drives all correlated market signals
            heat = float(rng.uniform(p["heat_min"], p["heat_max"]))

            # Income: metro-anchored with zip-level spread
            median_household_income = max(
                p["income_floor"],
                round(float(rng.normal(metro_income, metro_income * p["income_spread_pct"])), 2),
            )

            # Price: metro-anchored, nudged by local income deviation
            income_ratio      = median_household_income / metro_income
            median_sale_price = max(
                p["price_floor"],
                round(metro_price * income_ratio * float(rng.normal(1.0, p["price_noise_std"])), 2),
            )

            # Sqft generated first; price_per_sqft derived from it (not backwards)
            sqft           = float(rng.uniform(p["sqft_min"], p["sqft_max"]))
            price_per_sqft = round(median_sale_price / sqft, 2)

            # Rent anchored to price via gross yield
            fair_market_rent_2br = max(
                p["rent_floor"],
                round((median_sale_price * float(rng.uniform(p["gross_yield_min"], p["gross_yield_max"]))) / 12, 2),
            )

            # Days on market: hotter market → faster sales
            dom_low        = max(p["dom_floor_low"],  int(p["dom_base_low"]  + (1 - heat) * p["dom_cold_spread_low"]))
            dom_high       = max(p["dom_floor_high"], int(p["dom_base_high"] + (1 - heat) * p["dom_cold_spread_high"]))
            days_on_market = int(rng.integers(dom_low, dom_high + 1))

            # Homes sold: cheaper markets transact more frequently
            price_factor = metro_price / p["sold_norm_price"]
            sold_low     = max(p["sold_floor_low"],  int(p["sold_base_low"]  / price_factor))
            sold_high    = max(p["sold_floor_high"], int(p["sold_base_high"] / price_factor))
            homes_sold   = int(rng.integers(sold_low, sold_high + 1))

            # YoY appreciation: hotter markets appreciate faster
            yoy_appreciation = round(
                float(rng.normal(heat * p["appr_heat_scale"] + p["appr_heat_offset"], p["appr_std"])), 4
            )

            rows.append({
                "zip_code":                zip_code,
                "metro":                   metro,
                "median_sale_price":       median_sale_price,
                "price_per_sqft":          price_per_sqft,
                "days_on_market":          days_on_market,
                "homes_sold":              homes_sold,
                "median_household_income": median_household_income,
                "fair_market_rent_2br":    fair_market_rent_2br,
                "yoy_appreciation":        yoy_appreciation,
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
