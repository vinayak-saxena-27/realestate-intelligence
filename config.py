# ── Color Palette ────────────────────────────────────────────────────────────
COLORS: dict[str, str] = {
    "navy":       "#1B3A5C",
    "gold":       "#C9A84C",
    "green":      "#1A7A4A",
    "red":        "#C0392B",
    "light_blue": "#EAF2FB",
    "gray":       "#F5F5F5",
}

CHART_COLORS: list[str] = [
    "#1B3A5C",
    "#2E86AB",
    "#1A7A4A",
    "#C9A84C",
    "#E76F51",
    "#C0392B",
]

GRADE_COLORS: dict[str, str] = {
    "A": "#1A7A4A",
    "B": "#2E86AB",
    "C": "#F4A261",
    "D": "#E76F51",
    "F": "#C0392B",
}

# ── Metro Configuration (single source of truth) ─────────────────────────────
# To add a metro: add one entry here + a base in METRO_ZIP_BASE.
# In production, replace synthetic generation in data_loader.py with a real
# feed (MLS, Zillow API, ATTOM, CoreLogic) keyed on these same zip codes.
METROS: dict[str, dict] = {
    "Austin TX": {
        "median_price_range":   (440_000, 660_000),
        "price_per_sqft_range": (220, 400),
        "median_income":         90_000,
        "weight":                0.10,
    },
    "Phoenix AZ": {
        "median_price_range":   (300_000, 460_000),
        "price_per_sqft_range": (140, 280),
        "median_income":         68_000,
        "weight":                0.12,
    },
    "Nashville TN": {
        "median_price_range":   (340_000, 500_000),
        "price_per_sqft_range": (160, 310),
        "median_income":         72_000,
        "weight":                0.08,
    },
    "Charlotte NC": {
        "median_price_range":   (300_000, 450_000),
        "price_per_sqft_range": (140, 275),
        "median_income":         68_000,
        "weight":                0.10,
    },
    "Tampa FL": {
        "median_price_range":   (288_000, 432_000),
        "price_per_sqft_range": (130, 265),
        "median_income":         65_000,
        "weight":                0.09,
    },
    "Denver CO": {
        "median_price_range":   (480_000, 720_000),
        "price_per_sqft_range": (250, 450),
        "median_income":         95_000,
        "weight":                0.10,
    },
    "Raleigh NC": {
        "median_price_range":   (320_000, 480_000),
        "price_per_sqft_range": (155, 300),
        "median_income":         75_000,
        "weight":                0.05,
    },
    "Atlanta GA": {
        "median_price_range":   (295_000, 445_000),
        "price_per_sqft_range": (135, 270),
        "median_income":         67_000,
        "weight":                0.12,
    },
    "Dallas TX": {
        "median_price_range":   (310_000, 470_000),
        "price_per_sqft_range": (150, 290),
        "median_income":         70_000,
        "weight":                0.13,
    },
    "Seattle WA": {
        "median_price_range":   (640_000, 960_000),
        "price_per_sqft_range": (350, 600),
        "median_income":        110_000,
        "weight":                0.11,
    },
}

if abs(sum(m["weight"] for m in METROS.values()) - 1.0) >= 1e-9:
    raise ValueError("Metro weights must sum to 1.0")

METRO_ZIP_BASE: dict[str, int] = {
    "Austin TX":    78700,
    "Phoenix AZ":   85000,
    "Nashville TN": 37200,
    "Charlotte NC": 28200,
    "Tampa FL":     33600,
    "Denver CO":    80200,
    "Raleigh NC":   27600,
    "Atlanta GA":   30300,
    "Dallas TX":    75200,
    "Seattle WA":   98100,
}

ZIP_CODES_PER_METRO: int = 20

# log-mean (mu) for lognormal price sampling; median of LogNormal(mu, sigma) = exp(mu)
# values = log(midpoint of each metro's median_price_range)
LOGNORMAL_BASE_PRICE: dict[str, float] = {
    "Austin TX":    13.2176,
    "Phoenix AZ":   12.8480,
    "Nashville TN": 12.9481,
    "Charlotte NC": 12.8347,
    "Tampa FL":     12.7938,
    "Denver CO":    13.3046,
    "Raleigh NC":   12.8993,
    "Atlanta GA":   12.8212,
    "Dallas TX":    12.8740,
    "Seattle WA":   13.5929,
}

# ── Synthetic Data Generation Parameters ─────────────────────────────────────
SYNTH_PARAMS: dict[str, int | float] = {
    # heat index (0 = cold market, 1 = hot market)
    "heat_min":             0.2,
    "heat_max":             1.0,
    # income
    "income_spread_pct":    0.15,   # std dev as fraction of metro median
    "income_floor":         30_000,
    # price
    "price_noise_std":      0.12,
    "price_floor":          100_000,
    # sqft
    "sqft_min":             900,
    "sqft_max":             2_800,
    # rent → yield compression: yield_mid = base*(yield_norm_price/metro_price)^exponent
    #         result clamped to [gross_yield_min, gross_yield_max] before per-zip noise
    "gross_yield_min":       0.04,
    "gross_yield_max":       0.09,
    "gross_yield_base":      0.065,  # gross yield at yield_norm_price
    "yield_norm_price":      400_000,
    "yield_price_exponent":  0.5,    # sublinear: pricier metros yield less, but not proportionally
    "yield_noise_std":       0.008,
    "rent_floor":            600,
    # days on market → market_speed = heat_weight*heat + income_weight*clip(income/norm, 0, 1.5)
    #                  dom_low = max(floor_low, base_low + (1-speed)*cold_spread_low)
    "dom_base_low":          5,
    "dom_cold_spread_low":   30,
    "dom_floor_low":         5,
    "dom_base_high":         20,
    "dom_cold_spread_high":  100,
    "dom_floor_high":        15,
    "dom_heat_weight":       0.7,
    "dom_income_weight":     0.3,
    "dom_norm_income":       80_000,
    # homes sold  →  scaled by metro_price / norm_price
    "sold_norm_price":       400_000,
    "sold_base_low":         10,
    "sold_base_high":        150,
    "sold_floor_low":        2,
    "sold_floor_high":       10,
    # yoy appreciation → metro_trend = N(metro_heat*scale + offset, metro_std)
    #                    zip_appr    = metro_trend + N(0, zip_residual_std)
    "appr_heat_scale":       0.12,
    "appr_heat_offset":      -0.01,
    "appr_metro_std":        0.02,   # controls how much metros diverge from each other
    "appr_zip_residual_std": 0.015,  # controls zip scatter within a metro
    # price_velocity rolling window (months)
    "velocity_window":           3,
    # time-series monthly variation (applied on top of cross-sectional base values)
    "monthly_price_noise_std":  0.008,  # multiplicative: price_t ~ trend_t × N(1, std)
    "monthly_dom_noise_std":    3.0,    # additive noise on DOM per month (days)
    "monthly_sold_noise_std":   0.08,   # multiplicative noise on homes_sold per month
    "seasonal_dom_amplitude":   5.0,    # DOM peak-to-trough swing (days); peak in Jan
    "seasonal_sold_amplitude":  0.20,   # homes-sold fractional swing; peak in Apr
}

# ── Validation Range Constants ───────────────────────────────────────────────
DAYS_ON_MARKET_RANGE:       tuple[int,   int]   = (5,       120)
HOMES_SOLD_RANGE:           tuple[int,   int]   = (5,       200)
LIST_TO_SALE_RATIO_RANGE:   tuple[float, float] = (0.93,  1.05)
INVENTORY_LEVEL_RANGE:      tuple[int,   int]   = (10,     500)
BACHELOR_RATE_RANGE:        tuple[float, float] = (0.10,  0.75)

# ── Data Generation ───────────────────────────────────────────────────────────
RNG_SEED: int       = 42
PRICE_ROUND_DP: int = 2   # decimal places for prices, income, and rent
APPR_ROUND_DP: int  = 4   # decimal places for yoy_appreciation
N_MONTHS: int       = 24          # months of history per zip code
DATA_END_MONTH: str = "2024-12"   # latest month in the dataset (YYYY-MM)

# ── DataFrame Schema ──────────────────────────────────────────────────────────
# Contract between the data layer and the rest of the app.
# nullable=True columns may be absent in CSV feeds; all are present in synthetic output.
# validate_schema() enforces required columns; validate_csv() enforces CSV-specific rules.
# price_history is not stored in the panel — get_price_history_df() builds it on demand
# from the (zip_code, month, median_sale_price) rows that are already present.
DATAFRAME_SCHEMA: dict[str, dict] = {
    "month":                   {"type": str,   "nullable": False},
    "zip_code":                {"type": str,   "nullable": False},
    "metro":                   {"type": str,   "nullable": False},
    "median_sale_price":       {"type": float, "nullable": False},
    "price_per_sqft":          {"type": float, "nullable": False},
    "days_on_market":          {"type": int,   "nullable": False},
    "homes_sold":              {"type": int,   "nullable": False},
    "median_household_income": {"type": float, "nullable": False},
    "fair_market_rent_2br":    {"type": float, "nullable": False},
    # appreciation_rate: annual YoY rate in percentage points (e.g. 8.0 for 8%).
    # engineer_features() produces yoy_appreciation from median_sale_price_12m_ago;
    # this column is the raw synthetic seed value used in pop_stats and filtering.
    "appreciation_rate":       {"type": float, "nullable": False},
    "bachelor_rate":           {"type": float, "nullable": False},
    "list_to_sale_ratio":      {"type": float, "nullable": False},
    "inventory_level":         {"type": int,   "nullable": False},
    "median_list_price":       {"type": float, "nullable": False},
}

# ── CSV Column Schema ─────────────────────────────────────────────────────────
REQUIRED_CSV_COLUMNS: list[str] = [
    "month",        # required for time-series features (price_velocity, yoy lag)
    "zip_code",
    "metro",
    "median_sale_price",
    "price_per_sqft",
    "days_on_market",
    "homes_sold",
    "median_household_income",
    "fair_market_rent_2br",
]

OPTIONAL_CSV_COLUMNS: list[str] = [
    "bachelor_rate",
    "list_to_sale_ratio",
    "inventory_level",
    "appreciation_rate",
    "median_list_price",
    "yoy_appreciation",
]

# ── Model Parameters ──────────────────────────────────────────────────────────
# Passed directly via **RF_PARAMS / **KMEANS_PARAMS in models.py
RF_PARAMS: dict[str, int] = {
    "n_estimators": 100,
    "random_state": 42,
}

KMEANS_PARAMS: dict[str, int] = {
    "n_clusters":   5,
    "random_state": 42,
}

# ── Investment Grade Thresholds ───────────────────────────────────────────────
# Ordered high → low; scoring.py iterates and returns the first match.
GRADE_THRESHOLDS: list[dict[str, str | int]] = [
    {"letter": "A", "min_score": 80, "label": "Strong Buy"},
    {"letter": "B", "min_score": 65, "label": "Buy"},
    {"letter": "C", "min_score": 50, "label": "Hold"},
    {"letter": "D", "min_score": 35, "label": "Caution"},
    {"letter": "F", "min_score":  0, "label": "Avoid"},
]

# ── Segment Labels ────────────────────────────────────────────────────────────
SEGMENT_LABELS: dict[str, str] = {
    "Growth Market":   "High appreciation and fast sales — ideal for capital gains investors.",
    "Cash Flow Market": "Strong rental yields with moderate price growth — best for income investors.",
    "Premium Market":  "Top-tier metrics across the board — low supply, high demand, high entry cost.",
    "Declining Market": "Below-average scores across all indicators — approach with caution.",
    "Stable Market":   "Balanced metrics with steady, predictable performance — low risk, low volatility.",
}

# ── Market Pattern Injection ─────────────────────────────────────────────────
# Deliberate market patterns injected after base generation to create visually
# compelling demo data. All thresholds live here so _inject_market_patterns()
# contains no literals.
# Note: PRD references 'Houston TX' which is not in METROS — Dallas TX substituted.
TOP_APPRECIATING_COUNT: int   = 15
DECLINING_COUNT:        int   = 12
DECLINING_METROS:       list  = ["Dallas TX", "Phoenix AZ"]
HOT_MARKET_COUNT:       int   = 20
HOT_DOM_CEILING:        int   = 12
SLOW_MARKET_COUNT:      int   = 15
SLOW_DOM_FLOOR:         int   = 55

# ── Population Stats Keys ────────────────────────────────────────────────────
REQUIRED_POP_STAT_KEYS: frozenset[str] = frozenset({
    "median_yoy_appreciation",
    "median_gross_rental_yield",
    "median_market_heat_index",
    "median_neighborhood_score",
    "median_days_on_market",
    "median_investment_score",
    "top_metro_appreciation",
    "best_yield_metro",
    "is_finalized",
    "loaded_metros",
})

# ── CSV Ingestion Limits ──────────────────────────────────────────────────────
MAX_CSV_SIZE_MB: int = 50   # reject files larger than this before reading into memory

# ── App Settings ──────────────────────────────────────────────────────────────
APP_TITLE: str  = "Real Estate Investment Intelligence"
APP_ICON:  str  = "🏠"
PAGE_TITLES: dict[str, str] = {
    "overview":     "Market Overview",
    "scoring":      "Investment Scoring",
    "segments":     "Market Segments",
    "neighborhood": "Neighborhood Analysis",
    "data":         "Data Explorer",
}

# ── Normalization Scope ───────────────────────────────────────────────────────
# 'global'    — min/max spans all metros (original behaviour, default)
# 'per_metro' — min/max computed within each metro before combining
NORMALIZATION_SCOPE: str = "global"

# ── Feature Engineering & Scoring Weights ────────────────────────────────────
NET_YIELD_EXPENSE_RATIO: float = 0.75  # 25% expense load assumption

NEIGHBORHOOD_WEIGHTS: dict[str, float] = {
    "income":      0.40,
    "education":   0.30,
    "home_value":  0.30,
}

INVESTMENT_SCORE_WEIGHTS: dict[str, float] = {
    "appreciation": 0.25,
    "yield":        0.20,
    "heat":         0.15,
    "neighborhood": 0.20,
    "velocity":     0.10,
    "net_yield":    0.10,
}

HEAT_INDEX_COMPONENTS: dict[str, float] = {
    "days_on_market": 0.35,
    "homes_sold":     0.30,
    "price_velocity": 0.20,
    "list_to_sale":   0.15,
}

if abs(sum(NEIGHBORHOOD_WEIGHTS.values())     - 1.0) >= 1e-9:
    raise ValueError("NEIGHBORHOOD_WEIGHTS must sum to 1.0")
if abs(sum(INVESTMENT_SCORE_WEIGHTS.values()) - 1.0) >= 1e-9:
    raise ValueError("INVESTMENT_SCORE_WEIGHTS must sum to 1.0")
if abs(sum(HEAT_INDEX_COMPONENTS.values())    - 1.0) >= 1e-9:
    raise ValueError("HEAT_INDEX_COMPONENTS must sum to 1.0")
if NORMALIZATION_SCOPE not in {"global", "per_metro"}:
    raise ValueError(
        f"NORMALIZATION_SCOPE must be 'global' or 'per_metro', got {NORMALIZATION_SCOPE!r}"
    )
if METRO_ZIP_BASE.keys() != METROS.keys():
    raise ValueError("METRO_ZIP_BASE keys must match METROS keys")
if LOGNORMAL_BASE_PRICE.keys() != METROS.keys():
    raise ValueError("LOGNORMAL_BASE_PRICE keys must match METROS keys")
if len(CHART_COLORS) != 6:
    raise ValueError("CHART_COLORS must contain exactly 6 hex strings")
if len(SEGMENT_LABELS) != KMEANS_PARAMS["n_clusters"]:
    raise ValueError(
        f"SEGMENT_LABELS must have one entry per cluster (n_clusters={KMEANS_PARAMS['n_clusters']})"
    )
_scores = [g["min_score"] for g in GRADE_THRESHOLDS]
if _scores != sorted(_scores, reverse=True):
    raise ValueError("GRADE_THRESHOLDS must be ordered high → low")
