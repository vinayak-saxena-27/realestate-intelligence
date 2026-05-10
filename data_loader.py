import numpy as np
import pandas as pd

from config import METROS

# 20 real zip codes per metro, drawn from core city + inner-ring suburbs
METRO_ZIPS: dict[str, list[str]] = {
    "Austin TX":    ["78701","78702","78703","78704","78705","78721","78722",
                     "78723","78724","78725","78726","78727","78728","78729",
                     "78730","78731","78732","78733","78734","78735"],
    "Phoenix AZ":   ["85003","85004","85006","85007","85008","85009","85012",
                     "85013","85014","85015","85016","85017","85018","85019",
                     "85020","85021","85022","85023","85024","85027"],
    "Nashville TN": ["37201","37203","37204","37205","37206","37207","37208",
                     "37209","37210","37211","37212","37213","37214","37215",
                     "37216","37217","37218","37219","37220","37221"],
    "Charlotte NC": ["28202","28203","28204","28205","28206","28207","28208",
                     "28209","28210","28211","28212","28213","28214","28215",
                     "28216","28217","28226","28227","28262","28269"],
    "Tampa FL":     ["33602","33603","33604","33605","33606","33607","33609",
                     "33610","33611","33612","33613","33614","33615","33616",
                     "33617","33618","33619","33624","33625","33629"],
    "Denver CO":    ["80202","80203","80204","80205","80206","80207","80209",
                     "80210","80211","80212","80214","80215","80216","80218",
                     "80219","80220","80221","80222","80223","80224"],
    "Raleigh NC":   ["27601","27603","27604","27605","27606","27607","27608",
                     "27609","27610","27612","27613","27614","27615","27616",
                     "27617","27502","27513","27519","27523","27526"],
    "Atlanta GA":   ["30303","30305","30306","30307","30308","30309","30310",
                     "30311","30312","30313","30314","30315","30316","30317",
                     "30318","30319","30324","30326","30327","30328"],
    "Dallas TX":    ["75201","75202","75203","75204","75205","75206","75207",
                     "75208","75209","75210","75211","75212","75214","75215",
                     "75216","75217","75218","75219","75220","75225"],
    "Seattle WA":   ["98101","98102","98103","98104","98105","98106","98107",
                     "98108","98109","98112","98115","98116","98117","98118",
                     "98119","98121","98122","98125","98126","98133"],
}


def generate_synthetic_data() -> pd.DataFrame:
    np.random.seed(42)

    rows = []

    for metro in METROS:
        for zip_code in METRO_ZIPS[metro]:

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

    expected = sum(len(v) for v in METRO_ZIPS.values())
    assert df.shape[0] == expected, f"Expected {expected} rows, got {df.shape[0]}"
    assert df.isnull().sum().sum() == 0, "DataFrame contains NaN values"
    assert (df["median_sale_price"] > 0).all(), "Price column contains zeros"

    return df


if __name__ == "__main__":
    df = generate_synthetic_data()
    print("Shape:", df.shape)
    print(df.head())
