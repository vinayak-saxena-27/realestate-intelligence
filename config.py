# ── Color Palette ────────────────────────────────────────────────────────────
NAVY       = "#1B2A4A"
GOLD       = "#C9A84C"
GREEN      = "#2E7D32"
RED        = "#C62828"
WHITE      = "#FFFFFF"
LIGHT_GRAY = "#F5F5F5"

# ── Metro → Zip Codes (single source of truth) ───────────────────────────────
# To add a metro: add one entry here. METROS is derived automatically.
# In production, replace synthetic generation in data_loader.py with a real
# feed (MLS, Zillow API, ATTOM, CoreLogic) keyed on these same zip codes.
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

METROS: list[str] = list(METRO_ZIPS.keys())

# ── Metro Anchors (approximate 2024 medians) ─────────────────────────────────
# Add an entry here whenever you add a metro to METRO_ZIPS.
METRO_ANCHORS: dict[str, dict[str, int]] = {
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
FALLBACK_ANCHOR: dict[str, int] = {"median_price": 400_000, "median_income": 70_000}

# ── Synthetic Data Generation Parameters ─────────────────────────────────────
SYNTH_PARAMS: dict[str, float] = {
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
    # rent (gross annual yield applied to price)
    "gross_yield_min":      0.04,
    "gross_yield_max":      0.09,
    "rent_floor":           600,
    # days on market  →  low = max(floor_low, base_low + (1-heat)*cold_spread_low)
    "dom_base_low":         5,
    "dom_cold_spread_low":  30,
    "dom_floor_low":        5,
    "dom_base_high":        20,
    "dom_cold_spread_high": 100,
    "dom_floor_high":       15,
    # homes sold  →  scaled by metro_price / norm_price
    "sold_norm_price":      400_000,
    "sold_base_low":        10,
    "sold_base_high":       150,
    "sold_floor_low":       2,
    "sold_floor_high":      10,
    # yoy appreciation  →  normal(heat * scale + offset, std)
    "appr_heat_scale":      0.12,
    "appr_heat_offset":     -0.01,
    "appr_std":             0.03,
}

# ── Data Generation ───────────────────────────────────────────────────────────
RNG_SEED: int       = 42
PRICE_ROUND_DP: int = 2   # decimal places for prices, income, and rent
APPR_ROUND_DP: int  = 4   # decimal places for yoy_appreciation

# ── Model Parameters ──────────────────────────────────────────────────────────
# Passed directly via **RF_PARAMS / **KMEANS_PARAMS in models.py
RF_PARAMS: dict = {
    "n_estimators": 100,
    "random_state": 42,
}

KMEANS_PARAMS: dict = {
    "n_clusters":   5,
    "random_state": 42,
}

# ── Investment Grade Thresholds ───────────────────────────────────────────────
# Ordered high → low; scoring.py iterates this to assign a letter grade.
GRADE_THRESHOLDS: dict[str, int] = {
    "A": 80,
    "B": 65,
    "C": 50,
    "D": 35,
    "F":  0,
}

# ── Scoring Weights ───────────────────────────────────────────────────────────
SCORING_WEIGHTS: dict[str, float] = {
    "appreciation": 0.25,
    "yield":        0.20,
    "heat":         0.15,
    "neighborhood": 0.20,
    "velocity":     0.10,
    "net_yield":    0.10,
}

assert abs(sum(SCORING_WEIGHTS.values()) - 1.0) < 1e-9, "Scoring weights must sum to 1.0"
assert METRO_ANCHORS.keys() == METRO_ZIPS.keys(), "METRO_ANCHORS keys must match METRO_ZIPS keys"
assert list(GRADE_THRESHOLDS.values()) == sorted(GRADE_THRESHOLDS.values(), reverse=True), \
    "GRADE_THRESHOLDS must be ordered high → low"
