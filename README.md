# Real Estate Investment Intelligence Platform

A data-driven Streamlit web application that empowers real estate investors with AI-grade market analysis. Combines predictive price forecasting, composite investment scoring, and unsupervised market segmentation across 200 zip codes and 10 US metros.

## Status

| Week | Focus | Status |
|------|-------|--------|
| Week 0 | Environment setup, GitHub repo | Complete |
| Week 1 | Project structure, config, synthetic data | Complete |
| Week 2 | Feature engineering pipeline | Complete |
| Week 3 | ML models (Random Forest, K-Means, scoring) | Complete |
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
├── app.py                   # Streamlit entry point — load → engineer → model → score → segment
├── config.py                # Single source of truth for all constants and weights
├── data_loader.py           # Synthetic data generation, schema validation, CSV ingestion
├── feature_engineering.py  # Seven feature functions + engineer_features() pipeline
├── models.py                # Random Forest price forecasting + K-Means segmentation
├── scoring.py               # Investment score composite + letter grade assignment
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

These are the columns present after `generate_synthetic_data()` or `load_csv_data()`.
`median_sale_price_12m_ago` is added after schema validation during generation.

| Column | Type | Notes |
|---|---|---|
| `month` | str | YYYY-MM format, 2023-01 → 2024-12 |
| `zip_code` | str | Zero-padded 5-digit string |
| `metro` | str | One of the 10 metros |
| `median_sale_price` | float | Lognormal-sampled, price-floored at `SYNTH_PARAMS["price_floor"]` |
| `price_per_sqft` | float | `median_sale_price / sqft` |
| `days_on_market` | int | Vectorized heat + income composite (`_compute_dom()`); lognormal noise; seasonal overlay; clipped to `DAYS_ON_MARKET_RANGE` |
| `homes_sold` | int | Seasonal + price-scaled, clipped to `HOMES_SOLD_RANGE` |
| `median_household_income` | float | Metro-anchored with zip-level normal noise |
| `fair_market_rent_2br` | float | `price × gross_yield / 12`, floored at `SYNTH_PARAMS["rent_floor"]` |
| `median_sale_price_12m_ago` | float | 12-month lag; back-calculated for the first 12 months of each zip using `appreciation_rate` |
| `list_to_sale_ratio` | float | Heat-correlated per zip; clipped to `LIST_TO_SALE_RATIO_RANGE` |
| `bachelor_rate` | float | Income-correlated per zip; clipped to `BACHELOR_RATE_RANGE` |
| `inventory_level` | int | Inverse-heat-correlated per zip; clipped to `INVENTORY_LEVEL_RANGE` |
| `appreciation_rate` | float | Synthetic annual YoY appreciation rate in % (e.g. 8.0). Seed for 12m-lag back-calculation and `pop_stats`. Modified by `_inject_market_patterns()`. |
| `median_list_price` | float | `median_sale_price × list_to_sale_ratio` with monthly noise |

### Derived data helpers

| Function | Returns | Notes |
|---|---|---|
| `get_price_history_df(df, zip_code)` | `DataFrame` | Long-format price history for one zip: `month`, `median_sale_price`, `zip_code`. Sorted oldest → newest. Raises `ValueError` if zip not found. Used by chart factory functions. |

### Engineered DataFrame columns (output of `engineer_features()`)

`engineer_features()` adds seven columns to a copy of the raw DataFrame. All weights and thresholds are read from `config.py` — no literals in function bodies.

| Column | Range | Built by |
|---|---|---|
| `yoy_appreciation` | −5% to +25% | `compute_yoy_appreciation()` |
| `price_velocity` | −2% to +5% | `compute_price_velocity()` |
| `volume_trend` | −20% to +25% | `compute_volume_trend()` |
| `market_heat_index` | 0 to 100 | `compute_market_heat_index()` |
| `gross_rental_yield` | 2% to 12% | `compute_gross_rental_yield()` |
| `net_rental_yield` | 1.5% to 9% | `compute_net_rental_yield()` |
| `neighborhood_score` | 0 to 100 | `compute_neighborhood_score()` |

## Feature Engineering

```python
from data_loader import get_data
from feature_engineering import engineer_features

raw_df, pop_stats = get_data()                            # cached raw panel + partial pop_stats
df, pop_stats     = engineer_features(raw_df, pop_stats)  # adds 7 feature columns; fills pop_stats medians
```

`engineer_features(df, pop_stats)` accepts the `pop_stats` dict from `get_data()`, fills in `median_market_heat_index` and `median_neighborhood_score` with real computed medians (replacing the 50.0 placeholders from `_compute_pop_stats`), and returns `(df, pop_stats)`. It raises `ValueError` with a descriptive message if any required input column is missing. It sorts by `(zip_code, month)` before computing time-series features to guarantee correct ordering. It always operates on a copy of the input — the cached raw DataFrame is never mutated.

### Feature definitions

| Feature | Formula | Notes |
|---|---|---|
| `yoy_appreciation` | `(price − price_12m_ago) / price_12m_ago × 100` | Divide-by-zero guarded; first 12 months use back-calculated prior price |
| `price_velocity` | 3-month rolling mean of MoM % change in `median_sale_price`, per zip | Window size from `SYNTH_PARAMS["velocity_window"]`; grouped by zip to avoid cross-zip boundary artefacts |
| `volume_trend` | 3-month rolling mean of MoM % change in `homes_sold`, per zip | Same window and groupby pattern as `price_velocity`; positive = accelerating volume, negative = contracting |
| `market_heat_index` | Weighted sum of four min-max normalised components | Components: DOM (inverted, 35%), homes_sold (30%), price_velocity (20%), list_to_sale (15%) |
| `gross_rental_yield` | `(rent × 12) / price × 100` | Divide-by-zero guarded |
| `net_rental_yield` | `gross_rental_yield × NET_YIELD_EXPENSE_RATIO` | Ratio (0.75) from config — no literals in function |
| `neighborhood_score` | Weighted sum of three min-max normalised components | Components: income (40%), bachelor_rate (30%), median_sale_price (30%) |

> **Normalization scope:** `_minmax()` scales globally across all rows by default. Per-metro normalization is also supported, gated behind the `NORMALIZATION_SCOPE` flag in `config.py` (`"global"` or `"per_metro"`).

## Models

All model parameters are imported from `config.py` — no literals in `models.py`.

### Price Forecasting — `train_price_model()` / `predict_prices()`

Random Forest Regressor trained to predict `median_sale_price` 6 months ahead per zip code.

| Detail | Value |
|---|---|
| Target | `median_sale_price.shift(-6)` per zip — last 6 rows per zip dropped (NaN) |
| Split | Time-ordered 80/20: `sort_values(["month","zip_code"])` → first 80% = train, last 20% = test. No shuffle. |
| Features | `RF_FEATURES` from config — see Configuration section |
| Parameters | `RF_N_ESTIMATORS=100`, `RF_MAX_DEPTH=None`, `RF_N_JOBS=-1`, `random_state=RNG_SEED` |
| Output | `predicted_price_6m` column on full df; metrics dict (`rmse`, `r2`, `train_rows`, `test_rows`) |
| session_state | `price_model`, `price_metrics`, `price_importances` (feature importance dict) |

Observed metrics on synthetic data: RMSE ≈ $30k (within $15k–$60k target), R² ≈ 0.97 (above 0.92 ceiling — see leakage audit).

### Market Segmentation — `train_segment_model()` / `label_segments()`

K-Means clustering (k=5) assigns each row to a named market segment. Labels are derived programmatically from centroid values — never hardcoded to cluster indices, which change between runs.

| Detail | Value |
|---|---|
| Features | `KMEANS_FEATURES` from config (6 columns) — see Configuration section |
| Scaling | `StandardScaler` fitted on full df (acceptable for unsupervised — no target to leak) |
| Parameters | `KMEANS_K=5`, `KMEANS_N_INIT=10`, `KMEANS_MAX_ITER=300`, `random_state=RNG_SEED` |
| Label logic | Premium → highest nbhd+price_per_sqft; Growth → highest appr−DOM; Cash Flow → highest yield; Declining → lowest appr; Stable → remainder |
| Output | `market_segment` column on full df |
| session_state | `kmeans_model`, `kmeans_scaler` |

## Scoring

`compute_investment_score(df, pop_stats)` returns a copy of `df` with 8 new columns: 6 weighted component scores, `investment_score` (0–100), and `investment_grade` (A–F). It calls `assert_pop_stats_finalized(pop_stats)` at entry — `ValueError` is raised if `engineer_features()` has not yet been called.

### Investment score components

| Component | Weight | Source column |
|---|---|---|
| Appreciation | 25% | `yoy_appreciation` |
| Yield | 20% | `gross_rental_yield` |
| Neighbourhood | 20% | `neighborhood_score` |
| Heat | 15% | `market_heat_index` |
| Velocity | 10% | `price_velocity` |
| Net Yield | 10% | `net_rental_yield` |

Each component is independently min-max scaled to 0–100 before weighting. The weighted sum is then rescaled to 0–100 via a final `_minmax` pass so the full grade range is reachable.

### Grade thresholds

| Grade | Label | Min score |
|---|---|---|
| A | Strong Buy | 80 |
| B | Buy | 65 |
| C | Hold | 50 |
| D | Caution | 35 |
| F | Avoid | 0 |

`assign_grade(score)` iterates `GRADE_THRESHOLDS` from config — no hardcoded cutoffs in the function.

## Leakage Audit

A full data-leakage audit was conducted across the pipeline. See the module-level comment block in `models.py` for the complete 8-finding table. Summary:

| # | Finding | Severity | Resolution |
|---|---|---|---|
| 1 | `market_heat_index` + `neighborhood_score` computed with `_minmax` over full df before RF split | **Critical** | Fixed — `_refit_rf_features()` refits both using train rows only |
| 2 | `neighborhood_score` includes `median_sale_price` (30%) — strong price-level proxy | Warn | Accepted — autoregressive (price_t → price_t+6), not future leakage |
| 3 | `gross_rental_yield = rent/price × 100` — model can invert to recover price_t | Warn | Accepted — no future values used; main driver of R² > 0.92 |
| 4 | First 12 months per zip: `yoy_appreciation ≈ appreciation_rate` due to back-calculation | Warn | Accepted — synthetic data constraint, no real-world leakage risk |
| 5 | NaN drop before split | OK | Verified |
| 6 | Time-ordered split | OK | Verified |
| 7 | `compute_investment_score` uses `_minmax` on full df | Note | Fine for dashboard; refit on train if used for held-out eval |
| 8 | `train_segment_model` fits `StandardScaler` on full df | Note | Acceptable for unsupervised clustering |

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
| `OPTIONAL_CSV_COLUMNS` | 6 columns used if present; defaults applied if absent (`bachelor_rate`→0.30, `list_to_sale_ratio`→0.97, `inventory_level`→100, `appreciation_rate`→0.0, `median_list_price` back-calculated) |
| `DAYS_ON_MARKET_RANGE` | `(5, 120)` — clip bounds enforced in synthetic generation and `validate_schema()` |
| `HOMES_SOLD_RANGE` | `(5, 200)` |
| `LIST_TO_SALE_RATIO_RANGE` | `(0.93, 1.05)` |
| `INVENTORY_LEVEL_RANGE` | `(10, 500)` |
| `BACHELOR_RATE_RANGE` | `(0.10, 0.75)` |

`validate_csv()` additionally checks that the `month` column is parseable as a date and that no `(zip_code, month)` pair is duplicated — both are required for correct time-series feature computation.

### Scoring & feature weights

| Constant | Components | Sum |
|---|---|---|
| `INVESTMENT_SCORE_WEIGHTS` | appreciation 25%, yield 20%, neighborhood 20%, heat 15%, velocity 10%, net_yield 10% | 1.0 |
| `NEIGHBORHOOD_WEIGHTS` | income 40%, education 30%, home_value 30% | 1.0 |
| `HEAT_INDEX_COMPONENTS` | days_on_market 35%, homes_sold 30%, price_velocity 20%, list_to_sale 15% | 1.0 |
| `NET_YIELD_EXPENSE_RATIO` | `0.75` — 25% expense load applied to gross yield | — |

### Model parameters

| Constant | Value | Notes |
|---|---|---|
| `RF_N_ESTIMATORS` | 100 | Number of trees |
| `RF_N_JOBS` | −1 | Use all CPU cores |
| `RF_MAX_DEPTH` | None | Fully grown trees; set to 10 if overfitting |
| `RF_FEATURES` | list[str] | 5 feature columns used in both `train_price_model` and `predict_prices` |
| `KMEANS_K` | 5 | Number of clusters — must equal `len(SEGMENT_LABELS)` |
| `KMEANS_N_INIT` | 10 | Centroid initialisations per run |
| `KMEANS_MAX_ITER` | 300 | Max EM iterations per init |
| `KMEANS_FEATURES` | list[str] | 6 feature columns used in `train_segment_model` and `label_segments` |

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

### Grades & UI

| Constant | Description |
|---|---|
| `GRADE_THRESHOLDS` | `list[dict]` ordered A → F (Strong Buy → Avoid); `scoring.py` iterates and returns first match |
| `GRADE_COLORS` | Hex badge color per letter grade |
| `SEGMENT_LABELS` | 5 cluster names → one-sentence descriptions; count asserted equal to `KMEANS_K` |
| `COLORS` | Brand palette (navy, gold, green, red, light_blue, gray) |
| `CHART_COLORS` | 6-color Plotly sequential series palette |
| `APP_TITLE` / `APP_ICON` / `PAGE_TITLES` | All UI strings centralised — no hardcoded display text in page files |

### Population stats

`REQUIRED_POP_STAT_KEYS` is a `frozenset` of 10 keys that `pop_stats` must contain. Keys: `median_yoy_appreciation`, `median_gross_rental_yield`, `median_market_heat_index`, `median_neighborhood_score`, `median_days_on_market`, `median_investment_score`, `top_metro_appreciation`, `best_yield_metro`, `is_finalized`, `loaded_metros`. `median_investment_score` is 0.0 until `compute_investment_score()` fills it; `is_finalized` is False until `engineer_features()` runs.

## Caching Architecture

| Function | Strategy |
|---|---|
| `_get_data_cached(file_path, mtime, size, sha256)` | `@st.cache_data` — keyed on path + mtime + size + first-64KB hash so any file change invalidates the cache |
| `get_data(source)` | Thin wrapper — reads `os.stat()` for cache keys, then calls `_get_data_cached`. Accepts `None` (synthetic), file path string, or `st.UploadedFile`. |
| `engineer_features(df, pop_stats)` | `@st.cache_data` — engineered DataFrame + completed `pop_stats` computed once from cached raw |
| `train_price_model(df)` | Not cached — runs on every app start; fast enough (~10s) for a demo |
| `train_segment_model(df)` | Not cached — same rationale |

## Planned Output

A 5-page Streamlit dashboard:

1. **Market Overview** — metro-level price trends and heat map
2. **Investment Scoring** — per-zip composite score with letter grade
3. **Market Segments** — K-Means cluster explorer
4. **Neighborhood Analysis** — income, education, home value breakdown
5. **Data Explorer** — filterable raw + engineered data table
