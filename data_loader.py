import numpy as np
import pandas as pd

from config import METROS, METRO_ZIPS

# Approximate 2024 metro medians. Add an entry here whenever you add a metro to METRO_ZIPS.
# Fallback (400k / $70k) is used for any metro not listed.
_METRO_ANCHORS: dict[str, dict] = {
    "Seattle WA":   {"median_price": 800_000, "median_income": 110_000},
    "Denver CO":    {"median_price": 600_000, "median_income":  95_000},
    "Austin TX":    {"median_price": 550_000, "median_income":  90_000},
    "Nashville TN": {"median_price": 420_000, "median_income":  72_000},
    "Raleigh NC":   {"median_price": 400_000, "median_income":  75_000},
    "Dallas TX":    {"median_price": 390_000, "median_income":  70_000},
    "Phoenix AZ":   {"median_price": 380_000, "median_income":  68_000},
    "Charlotte NC": {"median_price": 375_000, "median_income":  68_000},
    "Atlanta GA":   {"median_price": 370_000, "median_income":  67_000},
    "Tampa FL":     {"median_price": 360_000, "median_income":  65_000},
}
_FALLBACK_ANCHOR = {"median_price": 400_000, "median_income": 70_000}


def generate_synthetic_data() -> pd.DataFrame:
    """Synthetic stand-in for production data. Replace with a real feed (MLS, Zillow API, ATTOM, CoreLogic) before going live."""
    rng = np.random.default_rng(42)

    rows = []

    for metro in METROS:
        anchor       = _METRO_ANCHORS.get(metro, _FALLBACK_ANCHOR)
        metro_price  = anchor["median_price"]
        metro_income = anchor["median_income"]

        for zip_code in METRO_ZIPS[metro]:
            # Single heat index drives all correlated market signals (0.2 = cold, 1.0 = hot)
            heat = float(rng.uniform(0.2, 1.0))

            # Income: metro-anchored with zip-level spread
            median_household_income = max(
                30_000,
                round(float(rng.normal(metro_income, metro_income * 0.15)), 2),
            )

            # Price: metro-anchored, nudged by local income deviation
            income_ratio      = median_household_income / metro_income
            median_sale_price = max(
                100_000,
                round(metro_price * income_ratio * float(rng.normal(1.0, 0.12)), 2),
            )

            # Sqft generated first; price_per_sqft derived from it (not backwards)
            sqft           = float(rng.uniform(900, 2_800))
            price_per_sqft = round(median_sale_price / sqft, 2)

            # Rent anchored to price via gross yield (4–9% annualised)
            fair_market_rent_2br = max(
                600,
                round((median_sale_price * float(rng.uniform(0.04, 0.09))) / 12, 2),
            )

            # Days on market: hotter market → faster sales
            dom_low        = max(5,  int(5  + (1 - heat) * 30))
            dom_high       = max(15, int(20 + (1 - heat) * 100))
            days_on_market = int(rng.integers(dom_low, dom_high + 1))

            # Homes sold: cheaper markets transact more frequently
            price_factor = metro_price / 400_000
            sold_low     = max(2,  int(10  / price_factor))
            sold_high    = max(10, int(150 / price_factor))
            homes_sold   = int(rng.integers(sold_low, sold_high + 1))

            # YoY appreciation: hotter markets appreciate faster (roughly −2% to +18%)
            yoy_appreciation = round(float(rng.normal(heat * 0.12 - 0.01, 0.03)), 4)

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
