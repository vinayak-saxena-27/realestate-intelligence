from __future__ import annotations

import datetime
from string import Template

import pandas as pd

from config import GRADE_COLORS, GRADE_LABEL_MAP

_VERDICTS: dict[str, str] = {
    "A": "Strong Buy — high conviction opportunity.",
    "B": "Buy — solid fundamentals with minor caveats.",
    "C": "Hold — monitor before committing capital.",
    "D": "Caution — significant risk factors present.",
    "F": "Avoid — does not meet investment criteria.",
}

# CSS is a plain string — no f-string escaping needed for curly braces
_CSS = """
*, *::before, *::after { box-sizing: border-box; }
body {
  font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #F4F7FA;
  color: #2D3748;
  margin: 0;
  padding: 32px 16px;
}
.page {
  max-width: 820px;
  margin: 0 auto;
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 24px rgba(27,58,92,0.10);
}
.header {
  background: #1B3A5C;
  padding: 28px 36px 24px;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}
.app-name {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255,255,255,0.5);
  text-transform: uppercase;
  letter-spacing: 1.2px;
  margin-bottom: 6px;
}
.zip-title {
  font-size: 36px;
  font-weight: 800;
  color: white;
  letter-spacing: -1px;
  line-height: 1;
}
.metro-line {
  font-size: 14px;
  color: rgba(255,255,255,0.6);
  margin-top: 5px;
  font-weight: 500;
}
.header-right { text-align: right; }
.report-date {
  font-size: 11.5px;
  color: rgba(255,255,255,0.45);
  margin-bottom: 8px;
}
.grade-pill {
  display: inline-block;
  padding: 5px 14px;
  border-radius: 100px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.3px;
  color: white;
}
.accent-bar {
  height: 4px;
  background: linear-gradient(90deg, #C9A84C 0%, #E8D09A 100%);
}
.body { padding: 32px 36px; }
.section-label {
  font-size: 10px;
  font-weight: 700;
  color: #8A9BB0;
  text-transform: uppercase;
  letter-spacing: 1px;
  border-bottom: 1px solid #EEF2F7;
  padding-bottom: 6px;
  margin: 0 0 14px;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 28px;
}
.kpi {
  border: 1px solid #DDE4EE;
  border-radius: 10px;
  padding: 14px 16px;
  position: relative;
  overflow: hidden;
}
.kpi::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, #1B3A5C, #C9A84C);
}
.kpi-label {
  font-size: 9px;
  font-weight: 600;
  color: #8A9BB0;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-bottom: 5px;
}
.kpi-value {
  font-size: 20px;
  font-weight: 800;
  color: #1B3A5C;
  letter-spacing: -0.5px;
  line-height: 1.2;
}
.kpi-vs {
  font-size: 10.5px;
  color: #8A9BB0;
  margin-top: 3px;
}
.verdict-box {
  border-radius: 0 10px 10px 0;
  padding: 16px 20px;
  margin-bottom: 24px;
  background: #F8FAFC;
}
.verdict-text {
  font-size: 14px;
  font-weight: 700;
  color: #2D3748;
  line-height: 1.4;
}
.narrative {
  font-size: 13.5px;
  line-height: 1.8;
  color: #2D3748;
  margin: 0 0 28px;
}
.pros-cons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 28px;
}
.pros-box, .cons-box {
  border: 1px solid #DDE4EE;
  border-radius: 10px;
  padding: 16px 18px;
}
.pros-box { border-top: 3px solid #1A7A4A; }
.cons-box { border-top: 3px solid #C0392B; }
.pc-title {
  font-size: 9.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin: 0 0 10px;
}
.pros-title { color: #1A7A4A; }
.cons-title { color: #C0392B; }
ul { margin: 0; padding: 0 0 0 16px; }
li { font-size: 12.5px; color: #2D3748; margin-bottom: 6px; line-height: 1.5; }
.detail-table { width: 100%; border-collapse: collapse; margin-bottom: 28px; }
.detail-table tr { border-bottom: 1px solid #EEF2F7; }
.detail-table tr:last-child { border-bottom: none; }
.detail-label {
  font-size: 10.5px;
  font-weight: 600;
  color: #8A9BB0;
  padding: 8px 0;
  width: 50%;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}
.detail-value { font-size: 13px; font-weight: 600; color: #2D3748; padding: 8px 0; }
.disclaimer {
  background: #F8FAFC;
  border-radius: 8px;
  padding: 14px 16px;
  font-size: 11px;
  color: #8A9BB0;
  line-height: 1.6;
}
.disclaimer strong { color: #6B7A8D; }
@media print {
  body { background: white; padding: 0; }
  .page { box-shadow: none; border-radius: 0; }
}
"""

_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>$title</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>$css</style>
</head>
<body>$body</body>
</html>""")


def generate_html_report(
    row: pd.Series,
    pop_stats: dict,
    pros: list[str],
    cons: list[str],
    narrative: str,
) -> str:
    """Return a self-contained HTML investment report for a single zip code.

    Open in any browser; use File → Print → Save as PDF to export as PDF.
    """
    grade       = row["investment_grade"]
    grade_color = GRADE_COLORS.get(grade, "#1B3A5C")
    grade_label = GRADE_LABEL_MAP.get(grade, grade)
    report_date = datetime.date.today().strftime("%B %d, %Y")

    # ── KPI helpers ───────────────────────────────────────────────────────────
    def _kpi(label: str, value: str, vs: str = "") -> str:
        vs_html = f'<div class="kpi-vs">{vs}</div>' if vs else ""
        return (
            f'<div class="kpi">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>'
            f'{vs_html}</div>'
        )

    price_vs_median = (row["median_sale_price"] - pop_stats["median_sale_price"]) / pop_stats["median_sale_price"] * 100
    forecast_chg    = (row["predicted_price_6m"] - row["median_sale_price"]) / row["median_sale_price"] * 100

    kpis_html = "".join([
        _kpi("Investment Score",   f"{row['investment_score']:.1f} / 100"),
        _kpi("Median Sale Price",  f"${row['median_sale_price']:,.0f}",
             f"{price_vs_median:+.1f}% vs portfolio median"),
        _kpi("YoY Appreciation",   f"{row['yoy_appreciation']:.1f}%",
             f"{row['yoy_appreciation'] - pop_stats['median_yoy_appreciation']:+.1f}pp vs median"),
        _kpi("Gross Rental Yield", f"{row['gross_rental_yield']:.1f}%",
             f"{row['gross_rental_yield'] - pop_stats['median_gross_rental_yield']:+.1f}pp vs median"),
        _kpi("Days on Market",     f"{int(row['days_on_market'])} days",
             f"{int(row['days_on_market'] - pop_stats['median_days_on_market']):+d} vs median"),
        _kpi("6-Month Forecast",   f"${row['predicted_price_6m']:,.0f}",
             f"{forecast_chg:+.1f}% from current price"),
    ])

    pros_li   = "".join(f"<li>{p}</li>" for p in pros)
    cons_li   = "".join(f"<li>{c}</li>" for c in cons)

    detail_rows = [
        ("Market Segment",      row.get("market_segment", "—")),
        ("Market Heat Index",   f"{row['market_heat_index']:.0f} / 100"),
        ("Neighbourhood Score", f"{row['neighborhood_score']:.0f} / 100"),
        ("Net Rental Yield",    f"{row['net_rental_yield']:.1f}%"),
        ("Price per Sqft",      f"${row.get('price_per_sqft', 0):,.0f}"),
        ("List-to-Sale Ratio",  f"{row.get('list_to_sale_ratio', 0):.2f}"),
        ("Inventory Level",     str(int(row.get("inventory_level", 0)))),
    ]
    detail_html = "".join(
        f'<tr><td class="detail-label">{k}</td><td class="detail-value">{v}</td></tr>'
        for k, v in detail_rows
    )

    body = f"""
  <div class="page">
    <div class="header">
      <div>
        <div class="app-name">Real Estate Investment Intelligence</div>
        <div class="zip-title">{row['zip_code']}</div>
        <div class="metro-line">{row['metro']}</div>
      </div>
      <div class="header-right">
        <div class="report-date">Report date: {report_date}</div>
        <div class="grade-pill" style="background:{grade_color}">{grade} — {grade_label}</div>
      </div>
    </div>
    <div class="accent-bar"></div>
    <div class="body">

      <div class="section-label">Key Metrics</div>
      <div class="kpi-grid">{kpis_html}</div>

      <div class="section-label">Investment Verdict</div>
      <div class="verdict-box" style="border-left: 4px solid {grade_color}">
        <div class="verdict-text">{_VERDICTS.get(grade, '')}</div>
      </div>

      <div class="section-label">Investment Analysis</div>
      <p class="narrative">{narrative}</p>

      <div class="section-label">Key Factors</div>
      <div class="pros-cons">
        <div class="pros-box">
          <div class="pc-title pros-title">Strengths</div>
          <ul>{pros_li}</ul>
        </div>
        <div class="cons-box">
          <div class="pc-title cons-title">Watch Points</div>
          <ul>{cons_li}</ul>
        </div>
      </div>

      <div class="section-label">Market Details</div>
      <table class="detail-table">{detail_html}</table>

      <div class="disclaimer">
        <strong>Disclaimer:</strong> This report is produced for research purposes only and does not
        constitute financial or investment advice. All figures are based on modelled data and should
        be verified against authoritative sources before making investment decisions.
      </div>

    </div>
  </div>"""

    return _TEMPLATE.substitute(
        title=f"Investment Report — {row['zip_code']}",
        css=_CSS,
        body=body,
    )
