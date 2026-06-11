# Real Estate Investment Intelligence Platform

A web dashboard that scores **200 US zip codes** across **10 high-growth metro areas** and tells you — in plain English — whether each market is worth your investment dollars. Every zip receives an A-to-F investment grade based on six market signals: price appreciation, rental yield, market heat, neighbourhood quality, price velocity, and net yield.

No spreadsheets. No guesswork. Open the app, pick a market, and get a full investment thesis in seconds.

---

## What you can do with it

- **Rank** every zip code on a 0–100 Investment Score and filter by grade, metro, price range, score range, and market segment
- **Read** a plain-English investment narrative for any zip — written like a research note, not a data table
- **Forecast** where median sale prices are headed over the next 6 months
- **Compare** up to four zip codes side-by-side on the metrics that matter most
- **Export** a formatted investment report for any zip as a downloadable HTML file (print to PDF from any browser)
- **Watchlist** any zip codes you're tracking and monitor their aggregate metrics in one place
- **Discover** similar markets automatically — the Deep Dive surfaces the nearest zip codes by market profile within the same K-Means cluster
- **Export** any filtered table view to CSV with one click

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
├── report.py                     # Self-contained HTML investment report generator
├── watchlist.py                  # Watchlist persistence (load / save / add / remove zip codes)
├── _styles.py                    # Shared CSS, grade badge helper, table card helper, page loader
│
├── pages/
│   ├── 01_Command_Center.py      # Market overview: KPIs, grade donut, top 10, opportunity cards
│   ├── 02_Zip_Code_Explorer.py   # Filterable, sortable table of all 200 zip codes + CSV export
│   ├── 03_Zip_Code_Deep_Dive.py  # Full analysis, watchlist toggle, report export, similar markets
│   ├── 04_Market_Comparison.py   # Side-by-side comparison of up to 4 zip codes
│   ├── 05_Model_Intelligence.py  # Model performance, feature weights, methodology
│   └── 06_Watchlist.py           # Personal watchlist: KPIs, table, add/remove management
│
├── README.md
├── CLIENT_DEMO_GUIDE.md
├── requirements.txt
└── .gitignore
```

---

## The pages

### Market Overview (home)
The landing page. Five metric chips show the current grade distribution across all 200 zip codes. An interactive bubble map plots every zip — sized by investment score and coloured by letter grade — across the 10 metros.

### 1. Command Center
Your portfolio at a glance. Five KPI cards show portfolio-level stats: total zip codes analysed, average investment score, top appreciation metro, best rental yield metro, and the count of Grade A and B opportunities. A donut chart shows the grade distribution. A ranked top-10 table and three "Best Opportunities" cards with direct deep-dive links round out the view.

### 2. Zip Code Explorer
A filterable, sortable table of all 200 zip codes. Sidebar filters cover:
- Metro area (multi-select)
- Investment grade with full labels, e.g. "A — Strong Buy" (multi-select)
- Price range displayed in $K (e.g. $300K–$960K) for readable slider labels
- Investment Score range (0–100 slider)
- Market Segment (multi-select)
- Sort by: Investment Score, Appreciation, Yield, Price, or Days on Market

Appreciation and yield figures are colour-coded green (above median) or red (below). Numeric columns are right-aligned. Download the filtered results as a CSV with one click.

### 3. Zip Code Deep Dive
The full investment thesis for any single zip code. Features:
- **Watchlist toggle** — add or remove the zip from your watchlist with one click; button state reflects current status instantly
- Six key metric cards with vs-median comparisons (price, score, appreciation, yield, DOM, market segment)
- 24-month price history chart with a 6-month model forecast
- Weighted score breakdown across all six components, colour-coded above/below median
- Plain-English investment narrative and a "Should I Invest Here?" panel with grade badge, verdict, strengths, and watch points
- **Export Report** — downloads a self-contained HTML investment report; open in any browser and use File → Print → Save as PDF to produce a shareable PDF
- **Similar Markets** — surfaces the four nearest zip codes by Euclidean distance in K-Means feature space within the same market segment, each with a one-click link to their own Deep Dive

### 4. Market Comparison
Select up to four zip codes to compare side-by-side across eight metrics. The best value in each row is highlighted green. An overlaid price history chart shows all four markets on the same timeline.

### 5. Model Intelligence
A transparent look under the hood: Random Forest accuracy (RMSE and R²), feature importance ranking, a pie chart of the six investment score weights, and a plain-English methodology explanation.

### 6. Watchlist
A personal tracking dashboard. Add zip codes from the Deep Dive page or directly from the Watchlist's own search field. The page shows:
- Five aggregate KPI cards: zip count, average score, blended gross yield, average appreciation, top pick
- A full styled table of all watchlisted zips
- Remove via multi-select dropdown
- Add new zips by searching with score context

Watchlist entries persist to `.watchlist.json` in the project root and survive app restarts.

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
