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

- **200 zip codes** across 10 US metros
- **24 months** of price history per zip (2023-01 → 2024-12)
- **4,800 rows** total (panel format: one row per zip per month)
- **10 columns:** `month`, `zip_code`, `metro`, `median_sale_price`, `price_per_sqft`, `days_on_market`, `homes_sold`, `median_household_income`, `fair_market_rent_2br`, `yoy_appreciation`

Metros: Austin TX, Phoenix AZ, Nashville TN, Charlotte NC, Tampa FL, Denver CO, Raleigh NC, Atlanta GA, Dallas TX, Seattle WA

Fully reproducible — seeded with `np.random.default_rng(42)`.

## Configuration

All constants live in `config.py`. Nothing is hardcoded in application logic.

| Constant group | Keys |
|---|---|
| Color palette | `NAVY`, `GOLD`, `GREEN`, `RED`, `WHITE`, `LIGHT_GRAY` |
| Model parameters | `RF_PARAMS` (n_estimators=100), `KMEANS_PARAMS` (k=5) |
| Grade thresholds | A≥80, B≥65, C≥50, D≥35, F<35 |
| Scoring weights | appreciation 25%, neighborhood 20%, yield 20%, heat 15%, velocity 10%, net_yield 10% |

## Planned Output

A 5-page Streamlit dashboard covering:
1. Market Overview
2. Price Forecast (Random Forest)
3. Investment Scores and Grades
4. Market Segments (K-Means)
5. Zip Code Deep Dive with AI narrative
