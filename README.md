# Real Estate Investment Intelligence Platform

A data-driven Streamlit web application that empowers real estate investors with AI-grade market analysis. Combines predictive price forecasting, composite investment scoring, and unsupervised market segmentation across 200 zip codes and 10 US metros.

## Status

| Week | Focus | Status |
|------|-------|--------|
| Week 0 | Environment setup, GitHub repo | Complete |
| Week 1 | Project structure, config, synthetic data | Complete |
| Week 2 | Feature engineering | Not started |
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
├── app.py                   # Streamlit entry point
├── config.py                # Single source of truth for all constants
├── data_loader.py           # Synthetic data generation and schema validation
├── feature_engineering.py  # Feature computation functions (Week 2)
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
- **10 core columns:** `month`, `zip_code`, `metro`, `median_sale_price`, `price_per_sqft`, `days_on_market`, `homes_sold`, `median_household_income`, `fair_market_rent_2br`, `yoy_appreciation`
- **3 optional columns** (present in real CSV feeds, absent in synthetic output): `bachelor_rate`, `list_to_sale_ratio`, `inventory_level`

Metros: Austin TX, Phoenix AZ, Nashville TN, Charlotte NC, Tampa FL, Denver CO, Raleigh NC, Atlanta GA, Dallas TX, Seattle WA

Fully reproducible — seeded with `np.random.default_rng(42)`. Price sampling uses a lognormal distribution (per-metro log-mean from `LOGNORMAL_BASE_PRICE`) which better models real home price distributions than a symmetric normal.

## Configuration

All constants live in `config.py`. Nothing is hardcoded in application logic.

### Metro configuration
| Constant | Purpose |
|---|---|
| `METROS` | Unified dict — 10 metros, each with `median_price_range`, `price_per_sqft_range`, `median_income`, `weight`. Weights sum to 1.0. |
| `METRO_ZIP_BASE` | Starting zip integer per metro; zips generated as `base + 0..19` |
| `ZIP_CODES_PER_METRO` | `20` — total rows = 10 × 20 × 24 = 4,800 |
| `LOGNORMAL_BASE_PRICE` | Log-mean `mu` per metro for lognormal price sampling |
| `FALLBACK_ANCHOR` | Safety-net anchor for any metro not found in `METROS` |

### Schema & validation
| Constant | Purpose |
|---|---|
| `DATAFRAME_SCHEMA` | Column types + nullable flag for the full output schema |
| `REQUIRED_CSV_COLUMNS` | 8 columns that must be present or CSV validation raises |
| `OPTIONAL_CSV_COLUMNS` | 4 columns used if present; logged as warning if absent |
| `DAYS_ON_MARKET_RANGE` | `(5, 120)` — clip bounds and validation range |
| `HOMES_SOLD_RANGE` | `(5, 200)` |
| `LIST_TO_SALE_RATIO_RANGE` | `(0.93, 1.05)` |
| `INVENTORY_LEVEL_RANGE` | `(10, 500)` |
| `MEDIAN_INCOME_RANGE` | `(35_000, 180_000)` |
| `BACHELOR_RATE_RANGE` | `(0.10, 0.75)` |
| `FAIR_MARKET_RENT_2BR_RANGE` | `(700, 3_500)` |

### Scoring & feature weights
| Constant | Components | Sum |
|---|---|---|
| `INVESTMENT_SCORE_WEIGHTS` | appreciation 25%, yield 20%, neighborhood 20%, heat 15%, velocity 10%, net_yield 10% | 1.0 |
| `NEIGHBORHOOD_WEIGHTS` | income 40%, education 30%, home_value 30% | 1.0 |
| `HEAT_INDEX_COMPONENTS` | days_on_market 35%, homes_sold 30%, price_velocity 20%, list_to_sale 15% | 1.0 |

### Grades & UI
| Constant | Description |
|---|---|
| `GRADE_THRESHOLDS` | List of `{letter, min_score, label}` dicts ordered A → F (Strong Buy → Avoid) |
| `GRADE_COLORS` | Hex badge color per letter grade |
| `SEGMENT_LABELS` | 5 K-Means cluster names → one-sentence descriptions |
| `COLORS` | Brand palette (navy, gold, green, red, light_blue, gray) |
| `CHART_COLORS` | 6-color Plotly sequential series palette |
| `APP_TITLE` / `APP_ICON` / `PAGE_TITLES` | All UI strings centralised — no hardcoded display text in page files |

## Planned Output

A 5-page Streamlit dashboard covering:
1. Market Overview
2. Investment Scoring
3. Market Segments (K-Means)
4. Neighborhood Analysis
5. Data Explorer
