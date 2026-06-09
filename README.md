# Real Estate Investment Intelligence Platform

A web dashboard that scores **200 US zip codes** across **10 high-growth metro areas** and tells you — in plain English — whether each market is worth your investment dollars. Every zip receives an A-to-F investment grade based on six market signals: price appreciation, rental yield, market heat, neighbourhood quality, price velocity, and net yield.

No spreadsheets. No guesswork. Open the app, pick a market, and get a full investment thesis in seconds.

---

## What you can do with it

- **Rank** every zip code on a 0–100 Investment Score and filter by grade, metro, or price range
- **Read** an AI-generated investment narrative for any zip — written like a research note, not a data table
- **Forecast** where median sale prices are headed over the next 6 months
- **Compare** up to four zip codes side-by-side on the metrics that matter most
- **Export** any filtered view to CSV with one click

---

## Prerequisites

| Requirement | Minimum version |
|---|---|
| Python | 3.10 |
| pip | latest recommended |

---

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-username/realestate-intelligence.git
cd realestate-intelligence

# 2. Create a virtual environment
python -m venv venv

# Activate on macOS / Linux:
source venv/bin/activate

# Activate on Windows:
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the app
streamlit run app.py
```

The app opens automatically in your browser at `http://localhost:8501`.
The first load takes ~15 seconds while the models train — subsequent page switches are instant.

---

## Project structure

```
realestate-intelligence/
│
├── app.py                        # Entry point — loads data, runs models, stores session state
├── config.py                     # All constants: metros, weights, grade thresholds, model params
├── data_loader.py                # Synthetic data generation and CSV ingestion
├── feature_engineering.py        # Derived market features (appreciation, yield, heat, etc.)
├── models.py                     # Random Forest price forecast + K-Means market segmentation
├── scoring.py                    # Weighted investment score → A-to-F letter grade
├── charts.py                     # Plotly chart factory (donut, price history, score bars, table)
├── narrative.py                  # Plain-English investment narrative generator
├── _styles.py                    # Shared CSS, grade badge helper, page data loader
│
├── pages/
│   ├── 01_Command_Center.py      # Market overview: KPIs, grade donut, top 10, opportunity cards
│   ├── 02_Zip_Code_Explorer.py   # Filterable table of all 200 zip codes with CSV export
│   ├── 03_Zip_Code_Deep_Dive.py  # Full analysis of a single zip code
│   ├── 04_Market_Comparison.py   # Side-by-side comparison of up to 4 zip codes
│   └── 05_Model_Intelligence.py  # Model performance, feature weights, methodology
│
├── README.md
├── CLIENT_DEMO_GUIDE.md
├── requirements.txt
└── .gitignore
```

---

## The 5 pages

### 1. Command Center
Your market overview at a glance. Five KPI cards show portfolio-level stats (total zip codes analysed, average investment score, top appreciation metro, best rental yield metro, number of Grade A and B opportunities). A donut chart shows the A-to-F grade distribution across all 200 zip codes. A ranked table highlights the top 10 opportunities, and three "Best Opportunities" cards surface the highest-conviction buys with a direct link to their full analysis.

### 2. Zip Code Explorer
A filterable, sortable table of all 200 zip codes. Use the sidebar to narrow by metro area, investment grade, and price range. Appreciation and yield figures are colour-coded green (beats the portfolio median) or red (falls below it). Download the filtered results as a CSV with one click.

### 3. Zip Code Deep Dive
The full investment thesis for any single zip code. Select a market from the dropdown — sorted best to worst — to see six key metric cards with vs-median comparisons, a 24-month price history chart with a 6-month forecast, a weighted score breakdown, a plain-English investment narrative, and a "Should I Invest Here?" panel with a grade badge, a one-line verdict, three key strengths, and three watch points.

### 4. Market Comparison
Select up to four zip codes to compare side-by-side across eight metrics. The best value in each row is highlighted green, so the winner is instantly obvious. An overlaid price history chart shows all four markets on the same timeline.

### 5. Model Intelligence
A transparent look under the hood: the Random Forest model's accuracy (RMSE and R²), a feature importance ranking showing which signals drive the price forecast, a pie chart of the six investment score weights, and a plain-English explanation of the methodology.

---

## Using your own data

Swap out the synthetic data for real market data by pointing the app to a CSV:

```python
# In app.py, change:
FILE_PATH = None                      # synthetic data (default)

# To:
FILE_PATH = 'data/my_market_data.csv' # your real feed
```

**Required columns:** `month` (YYYY-MM), `zip_code`, `metro`, `median_sale_price`, `price_per_sqft`, `days_on_market`, `homes_sold`, `median_household_income`, `fair_market_rent_2br`

Metro names in your CSV must match exactly: `Austin TX`, `Phoenix AZ`, `Nashville TN`, `Charlotte NC`, `Tampa FL`, `Denver CO`, `Raleigh NC`, `Atlanta GA`, `Dallas TX`, `Seattle WA`.

See `config.py → REQUIRED_CSV_COLUMNS` for the full validated schema.

---

## Investment score weights

| Signal | Weight | What it measures |
|---|---|---|
| Price Appreciation | 25% | Year-over-year price growth |
| Rental Yield | 20% | Gross rental income as % of purchase price |
| Neighbourhood | 20% | Income level, education, home values |
| Market Heat | 15% | Demand intensity (DOM, sales volume, list/sale ratio) |
| Price Velocity | 10% | Recent momentum in price movement |
| Net Yield | 10% | Rental income after estimated expenses |

**Grade thresholds:** A ≥ 80 · B ≥ 65 · C ≥ 50 · D ≥ 35 · F < 35

---

*For research and demonstration purposes only. Not financial advice.*
