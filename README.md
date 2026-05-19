# Real Estate Investment Intelligence Platform

A data-driven Streamlit web application that empowers real estate investors with AI-grade market analysis. Combines predictive price forecasting, composite investment scoring, and unsupervised market segmentation across 200 zip codes and 10 US metros.

## Status

| Week | Focus | Status |
|------|-------|--------|
| Week 0 | Environment setup, GitHub repo | Complete |
| Week 1 | Project structure, config, synthetic data | Complete |
| Week 2 | Feature engineering pipeline | Complete |
| Week 3 | ML models (Random Forest, K-Means) | Not started |
| Week 4 | Plotly charts | Not started |
| Week 5 | Streamlit UI, narratives | Not started |

## Tech Stack

- **Python** 3.14.2
- **Streamlit** 1.57.0
- **pandas** 3.0.2
- **NumPy** 2.4.4
- **scikit-learn** 1.8.0
- **SciPy** 1.17.1
- **Plotly** 6.7.0
- **openpyxl** 3.1.5

## Project Structure

```
realestate-intelligence/
├── app.py                   # Streamlit entry point — load → engineer → display
├── config.py                # Single source of truth for all constants and weights
├── data_loader.py           # Synthetic data generation, schema validation, CSV ingestion
├── feature_engineering.py  # Six feature functions + engineer_features() pipeline
├── models.py                # Random Forest + K-Means models (Week 3)
├── scoring.py               # Investment score and grade assignment (Week 3)
├── charts.py                # Plotly chart factory functions (Week 4)
├── narrative.py             # Rule-based narrative text generator (Week 5)
├── pages/                   # Streamlit page modules (Week 5)
└── data/                    # Data files — not committed (except .gitkeep)
```

## Getting Started

```bash
pip install streamlit pandas numpy scikit-learn scipy plotly openpyxl
streamlit run app.py
```

## Data

All data is synthetic — no external APIs or downloads required. The dataset is generated on first run and cached by Streamlit.

- **200 zip codes** across 10 US metros (20 per metro, generated sequentially from `METRO_ZIP_BASE`)
- **24 months** of price history per zip (2023-01 → 2024-12)
- **4,800 rows** total (panel format: one row per zip per month)

Metros: Austin TX, Phoenix AZ, Nashville TN, Charlotte NC, Tampa FL, Denver CO, Raleigh NC, Atlanta GA, Dallas TX, Seattle WA

Fully reproducible — seeded with `np.random.default_rng(42)`. Price sampling uses a lognormal distribution (per-metro log-mean from `LOGNORMAL_BASE_PRICE`), which better models real home price distributions than a symmetric normal.

### Raw DataFrame columns (output of `get_data()`)

| Column | Type | Notes |
|---|---|---|
| `month` | str | YYYY-MM format, 2023-01 → 2024-12 |
| `zip_code` | str | Zero-padded 5-digit string |
| `metro` | str | One of the 10 metros |
| `median_sale_price` | float | Lognormal-sampled, price-floored |
| `price_per_sqft` | float | `median_sale_price / sqft` |
| `days_on_market` | int | Heat + income composite formula; seasonal overlay; clipped to (5, 120) |
| `homes_sold` | int | Seasonal + price-scaled, clipped to (5, 200) |
| `median_household_income` | float | Metro-anchored with zip-level noise |
| `fair_market_rent_2br` | float | `price × gross_yield / 12`, rent-floored |
| `median_sale_price_12m_ago` | float | 12-month lag; back-calculated for first 12 months per zip |
| `list_to_sale_ratio` | float | Heat-correlated per zip; clipped to (0.93, 1.05) |
| `bachelor_rate` | float | Income-correlated per zip; clipped to (0.10, 0.75) |
| `inventory_level` | int | Inverse-heat-correlated per zip; clipped to (10, 500) |
| `appreciation_rate` | float | Synthetic annual YoY appreciation rate in % (e.g. 8.0). Used by the 12m-lag back-calculation and `pop_stats`. Modified by market pattern injection. |
| `median_list_price` | float | `median_sale_price × list_to_sale_ratio` with monthly noise |
| `price_history` | list[float] | 24-element list of monthly `median_sale_price` values for the zip (same value repeated across all month rows for a given zip). Used by `get_price_history_df()`. |

### Engineered DataFrame columns (output of `engineer_features()`)

`engineer_features()` adds six columns to a copy of the raw DataFrame. All weights and thresholds are read from `config.py` — no literals in function bodies.

| Column | Range | Built by |
|---|---|---|
| `yoy_appreciation` | −5% to +25% | `compute_yoy_appreciation()` |
| `price_velocity` | −2% to +5% | `compute_price_velocity()` |
| `market_heat_index` | 0 to 100 | `compute_market_heat_index()` |
| `gross_rental_yield` | 2% to 12% | `compute_gross_rental_yield()` |
| `net_rental_yield` | 1.5% to 9% | `compute_net_rental_yield()` |
| `neighborhood_score` | 0 to 100 | `compute_neighborhood_score()` |

## Feature Engineering

```python
from data_loader import get_data
from feature_engineering import engineer_features, get_population_stats

raw_df, pop_stats = get_data()                        # cached raw panel + partial pop_stats
df, pop_stats     = engineer_features(raw_df, pop_stats)  # adds 6 feature columns; fills 2 pop_stats keys
pop               = get_population_stats(df)          # population-level medians for narrative context
```

`engineer_features(df, pop_stats)` accepts the `pop_stats` dict from `get_data()`, fills in `median_market_heat_index` and `median_neighborhood_score` with real computed medians (replacing the 50.0 placeholders), and returns `(df, pop_stats)`. It raises `ValueError` with a descriptive message if any required input column is missing. It always operates on a copy of the input — the cached raw DataFrame is never mutated.

`get_population_stats()` raises `ValueError` if called on a raw (non-engineered) DataFrame.

### Feature definitions

| Feature | Formula | Notes |
|---|---|---|
| `yoy_appreciation` | `(price − price_12m_ago) / price_12m_ago × 100` | Divide-by-zero guarded; first 12 months use back-calculated prior price |
| `price_velocity` | 3-month rolling mean of MoM % change, per zip | Window size from `SYNTH_PARAMS["velocity_window"]`; grouped by zip to avoid cross-zip boundary artefacts |
| `market_heat_index` | Weighted sum of four min-max normalised components | Components: DOM (inverted, 35%), homes_sold (30%), price_velocity (20%), list_to_sale (15%) |
| `gross_rental_yield` | `(rent × 12) / price × 100` | Divide-by-zero guarded |
| `net_rental_yield` | `gross_rental_yield × NET_YIELD_EXPENSE_RATIO` | Ratio (0.75) from config — no literals in function |
| `neighborhood_score` | Weighted sum of three min-max normalised components | Components: income (40%), bachelor_rate (30%), median_sale_price (30%); `bachelor_rate` is guaranteed present by `data_loader` — no fallback |

> **Normalization note:** `_minmax()` scales globally across all rows in the input DataFrame. Adding a metro with extreme values will silently shift every existing zip's `market_heat_index` and `neighborhood_score`. Per-metro normalization is the planned fix, gated behind a `NORMALIZATION_SCOPE` flag in `config.py`.

## Configuration

All constants live in `config.py`. Nothing is hardcoded in application logic.

### Metro configuration

| Constant | Purpose |
|---|---|
| `METROS` | 10 metros, each with `median_price_range`, `price_per_sqft_range`, `median_income`, `weight`. Weights sum to 1.0. |
| `METRO_ZIP_BASE` | Starting zip integer per metro; zips are `str(base + i).zfill(5)` for i in 0..19 |
| `ZIP_CODES_PER_METRO` | `20` — total rows = 10 × 20 × 24 = 4,800 |
| `LOGNORMAL_BASE_PRICE` | Log-mean `mu` per metro for lognormal price sampling |

### Schema & validation

| Constant | Purpose |
|---|---|
| `DATAFRAME_SCHEMA` | Column types + nullable flag for the raw output schema |
| `REQUIRED_CSV_COLUMNS` | 9 columns that must be present or `validate_csv()` raises — includes `month` (required for time-series features) |
| `OPTIONAL_CSV_COLUMNS` | 6 columns used if present; defaults applied if absent (`bachelor_rate`→0.35, `list_to_sale_ratio`→0.98, `inventory_level`→100, `appreciation_rate`→5.0, `median_list_price` back-calculated, `yoy_appreciation` from 12m lag) |
| `DAYS_ON_MARKET_RANGE` | `(5, 120)` — clip bounds and validation range |
| `HOMES_SOLD_RANGE` | `(5, 200)` |
| `LIST_TO_SALE_RATIO_RANGE` | `(0.93, 1.05)` |
| `INVENTORY_LEVEL_RANGE` | `(10, 500)` |
| `MEDIAN_INCOME_RANGE` | `(35_000, 180_000)` |
| `BACHELOR_RATE_RANGE` | `(0.10, 0.75)` |
| `FAIR_MARKET_RENT_2BR_RANGE` | `(700, 3_500)` |

`validate_csv()` additionally checks that the `month` column is parseable as a date and that no `(zip_code, month)` pair is duplicated — both are required for correct time-series feature computation.

### Scoring & feature weights

| Constant | Components | Sum |
|---|---|---|
| `INVESTMENT_SCORE_WEIGHTS` | appreciation 25%, yield 20%, neighborhood 20%, heat 15%, velocity 10%, net_yield 10% | 1.0 |
| `NEIGHBORHOOD_WEIGHTS` | income 40%, education 30%, home_value 30% | 1.0 |
| `HEAT_INDEX_COMPONENTS` | days_on_market 35%, homes_sold 30%, price_velocity 20%, list_to_sale 15% | 1.0 |
| `NET_YIELD_EXPENSE_RATIO` | `0.75` — 25% expense load applied to gross yield | — |

### Market pattern injection

Applied after base synthetic generation to create realistic market variation for demo purposes. All thresholds are constants — `_inject_market_patterns()` contains no literals.

| Constant | Value | Effect |
|---|---|---|
| `TOP_APPRECIATING_COUNT` | 15 | Top-15 zips by appreciation boosted to 1.4× their base rate |
| `DECLINING_COUNT` | 12 | 12 zips in `DECLINING_METROS` forced to −2% … −5% appreciation |
| `DECLINING_METROS` | `["Dallas TX", "Phoenix AZ"]` | Source metros for declining zip selection |
| `HOT_MARKET_COUNT` | 20 | Top-20 zips by heat forced DOM < `HOT_DOM_CEILING` |
| `HOT_DOM_CEILING` | 12 | Maximum DOM for hot-market zips |
| `SLOW_MARKET_COUNT` | 15 | Bottom-15 zips by heat forced DOM > `SLOW_DOM_FLOOR` |
| `SLOW_DOM_FLOOR` | 55 | Minimum DOM for slow-market zips; all other zips capped at this value so injection is the sole source of DOM > 55 |

### Population stats

| Constant | Purpose |
|---|---|
| `REQUIRED_POP_STAT_KEYS` | `frozenset` of 8 keys that `pop_stats` must contain before downstream modules consume it. Keys: `median_yoy_appreciation`, `median_gross_rental_yield`, `median_market_heat_index`, `median_neighborhood_score`, `median_days_on_market`, `median_investment_score`, `top_metro_appreciation`, `best_yield_metro`. `median_investment_score` stays 0.0 until the Week 3 scoring module fills it. |

### Model parameters

| Constant | Type | Purpose |
|---|---|---|
| `RF_PARAMS` | `dict[str, int]` | Passed as `**RF_PARAMS` to `RandomForestRegressor` |
| `KMEANS_PARAMS` | `dict[str, int]` | Passed as `**KMEANS_PARAMS` to `KMeans`; `n_clusters = 5` |

### Grades & UI

| Constant | Description |
|---|---|
| `GRADE_THRESHOLDS` | `list[dict[str, str | int]]` ordered A → F (Strong Buy → Avoid); `scoring.py` iterates and returns first match |
| `GRADE_COLORS` | Hex badge color per letter grade |
| `SEGMENT_LABELS` | 5 cluster names → one-sentence descriptions (count asserted equal to `KMEANS_PARAMS["n_clusters"]`) |
| `COLORS` | Brand palette (navy, gold, green, red, light_blue, gray) |
| `CHART_COLORS` | 6-color Plotly sequential series palette |
| `APP_TITLE` / `APP_ICON` / `PAGE_TITLES` | All UI strings centralised — no hardcoded display text in page files |

## Caching Architecture

| Function | Strategy |
|---|---|
| `get_data()` | `@st.cache_data` — raw panel + partial `pop_stats` computed once per session |
| `engineer_features(df, pop_stats)` | `@st.cache_data` — engineered DataFrame + completed `pop_stats` computed once from cached raw |
| `get_population_stats(df)` | No cache — fast dict from already-cached engineered DataFrame |
| Individual `compute_*()` functions | No cache — called only inside `engineer_features()` |

## Planned Output

A 5-page Streamlit dashboard:

1. **Market Overview** — metro-level price trends and heat map
2. **Investment Scoring** — per-zip composite score with letter grade
3. **Market Segments** — K-Means cluster explorer
4. **Neighborhood Analysis** — income, education, home value breakdown
5. **Data Explorer** — filterable raw + engineered data table
