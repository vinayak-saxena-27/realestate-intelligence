# ── Color Palette ────────────────────────────────────────────────────────────
NAVY  = "#1B2A4A"
GOLD  = "#C9A84C"
GREEN = "#2E7D32"
RED   = "#C62828"
WHITE = "#FFFFFF"
LIGHT_GRAY = "#F5F5F5"

# ── Metro List ───────────────────────────────────────────────────────────────
METROS = [
    "Austin TX",
    "Phoenix AZ",
    "Nashville TN",
    "Charlotte NC",
    "Tampa FL",
    "Denver CO",
    "Raleigh NC",
    "Atlanta GA",
    "Dallas TX",
    "Seattle WA",
]

# ── Model Parameters ─────────────────────────────────────────────────────────
N_ESTIMATORS  = 100
RANDOM_STATE  = 42
K_MEANS_K     = 5

# ── Investment Grade Thresholds ───────────────────────────────────────────────
GRADE_A = 80
GRADE_B = 65
GRADE_C = 50
GRADE_D = 35
# Scores below GRADE_D are grade F

# ── Scoring Weights ───────────────────────────────────────────────────────────
SCORING_WEIGHTS = {
    "appreciation":  0.25,
    "yield":         0.20,
    "heat":          0.15,
    "neighborhood":  0.20,
    "velocity":      0.10,
    "net_yield":     0.10,
}

assert abs(sum(SCORING_WEIGHTS.values()) - 1.0) < 1e-9, "Scoring weights must sum to 1.0"
