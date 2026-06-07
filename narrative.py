import pandas as pd

# ── Sentence Templates ────────────────────────────────────────────────────────

OPENERS: dict[str, str] = {
    'a_growth': (
        "Zip code {zip} is a standout Growth Market opportunity, earning a Grade A score of "
        "{score:.1f}/100 on the back of {appr:.1f}% year-over-year appreciation — "
        "{appr_delta:+.1f}% above the portfolio median."
    ),
    'a_cashflow': (
        "Zip code {zip} is a high-conviction Cash Flow Market, posting a Grade A score of "
        "{score:.1f}/100 driven by a {yield_val:.1f}% gross rental yield — "
        "well above the {pop_yield:.1f}% portfolio average."
    ),
    'b_weak_yield': (
        "Zip code {zip} earns a Grade B score of {score:.1f}/100, presenting a solid "
        "buy opportunity with one caveat: its {yield_val:.1f}% gross yield sits "
        "{yield_delta:.1f}% below the portfolio median."
    ),
    'b_weak_appreciation': (
        "Zip code {zip} scores {score:.1f}/100 — a Grade B buy — though its "
        "{appr:.1f}% appreciation rate trails the {pop_appr:.1f}% portfolio median "
        "by {appr_delta_abs:.1f} percentage points."
    ),
    'b_weak_activity': (
        "Zip code {zip} holds a Grade B score of {score:.1f}/100 with solid fundamentals, "
        "though market activity lags the portfolio with a heat index of {heat:.0f}/100 "
        "against a {pop_heat:.0f}/100 median."
    ),
    'b_strong': (
        "Zip code {zip} earns a solid Grade B score of {score:.1f}/100, demonstrating "
        "above-average fundamentals across appreciation, yield, and market activity — "
        "a reliable buy opportunity in this portfolio."
    ),
    'c_improving': (
        "Zip code {zip} holds a Grade C score of {score:.1f}/100, but its "
        "{appr:.1f}% appreciation trend — above the {pop_appr:.1f}% median — "
        "signals improving fundamentals worth monitoring."
    ),
    'c_declining': (
        "Zip code {zip} carries a Grade C score of {score:.1f}/100 with appreciation "
        "of {appr:.1f}%, which is tracking below the {pop_appr:.1f}% portfolio median."
    ),
    'df_avoid': (
        "Zip code {zip} scores {score:.1f}/100 — a Grade {grade} rating that places "
        "it in the bottom tier of the portfolio across multiple dimensions."
    ),
}


# ── Branch Logic ──────────────────────────────────────────────────────────────

def _find_weakest_component(row: pd.Series, pop_stats: dict) -> str:
    """Return the component name (yield/appreciation/activity) most below its population median."""
    gaps = {
        'yield':        pop_stats['median_gross_rental_yield'] - row['gross_rental_yield'],
        'appreciation': pop_stats['median_yoy_appreciation']   - row['yoy_appreciation'],
        'activity':     pop_stats['median_market_heat_index']  - row['market_heat_index'],
    }
    return max(gaps, key=gaps.get)


def _select_branch(row: pd.Series, pop_stats: dict) -> str:
    """Return branch key used to select the opening sentence."""
    grade    = row['investment_grade']
    segment  = row['market_segment']
    appr     = row['yoy_appreciation']
    pop_appr = pop_stats['median_yoy_appreciation']

    if grade == 'A' and segment == 'Growth Market':   return 'a_growth'
    if grade == 'A' and segment == 'Cash Flow Market': return 'a_cashflow'
    if grade == 'A':                                   return 'a_growth'
    if grade == 'B':
        weak = _find_weakest_component(row, pop_stats)
        gaps = {
            'yield':        pop_stats['median_gross_rental_yield'] - row['gross_rental_yield'],
            'appreciation': pop_stats['median_yoy_appreciation']   - row['yoy_appreciation'],
            'activity':     pop_stats['median_market_heat_index']  - row['market_heat_index'],
        }
        return f'b_weak_{weak}' if gaps[weak] > 0 else 'b_strong'
    if grade == 'C' and appr > pop_appr:               return 'c_improving'
    if grade == 'C':                                   return 'c_declining'
    return 'df_avoid'


# ── Sentence Component Functions ──────────────────────────────────────────────

def _price_sentence(row: pd.Series, pop_stats: dict) -> str:
    price     = row['median_sale_price']
    pop_price = pop_stats.get('median_sale_price', price)
    pct_diff  = (price - pop_price) / pop_price * 100
    pred      = row['predicted_price_6m']
    direction  = 'up' if pred > price else 'down'
    change_pct = abs((pred - price) / price * 100)

    if pct_diff > 10:
        return (
            f"At ${price:,.0f}, this is a premium-priced market — {pct_diff:.0f}% above "
            f"the portfolio median — with prices forecast to move {direction} "
            f"{change_pct:.1f}% over the next 6 months."
        )
    if pct_diff < -10:
        return (
            f"Priced at ${price:,.0f} — {abs(pct_diff):.0f}% below the portfolio median — "
            f"this market offers accessible entry, with a 6-month forecast of "
            f"${pred:,.0f}."
        )
    return (
        f"Median sale price of ${price:,.0f} sits close to the portfolio average, "
        f"with a 6-month model forecast of ${pred:,.0f}."
    )


def _yield_sentence(row: pd.Series, pop_stats: dict) -> str:
    y     = row['gross_rental_yield']
    pop_y = pop_stats['median_gross_rental_yield']
    net_y = row['net_rental_yield']

    if y > pop_y * 1.1:
        return (
            f"The {y:.1f}% gross rental yield ({net_y:.1f}% estimated net) is "
            f"{y - pop_y:.1f}pp above the {pop_y:.1f}% portfolio median, "
            f"offering strong passive income potential."
        )
    if y < pop_y * 0.9:
        return (
            f"At {y:.1f}% gross yield ({net_y:.1f}% net), rental income is compressed "
            f"relative to the {pop_y:.1f}% portfolio median — "
            f"this market may suit appreciation-focused investors more than income seekers."
        )
    return (
        f"Rental yield of {y:.1f}% gross ({net_y:.1f}% estimated net) "
        f"is in line with the {pop_y:.1f}% portfolio median, "
        f"providing steady income alongside price appreciation."
    )


def _activity_sentence(row: pd.Series, pop_stats: dict) -> str:
    heat     = row['market_heat_index']
    pop_heat = pop_stats['median_market_heat_index']
    dom      = int(row['days_on_market'])
    pop_dom  = int(pop_stats['median_days_on_market'])

    if heat > pop_heat * 1.1:
        return (
            f"Market activity is elevated — a heat index of {heat:.0f}/100 and homes "
            f"selling in just {dom} days (vs. the {pop_dom}-day portfolio median) "
            f"signal strong buyer demand."
        )
    if heat < pop_heat * 0.9:
        return (
            f"The market moves at a slower pace: a {heat:.0f}/100 heat index and "
            f"{dom}-day average time on market (vs. {pop_dom} days median) give "
            f"buyers more negotiating room."
        )
    return (
        f"Market velocity is balanced, with a heat index of {heat:.0f}/100 and "
        f"homes averaging {dom} days on market, close to the {pop_dom}-day median."
    )


def _closing_sentence(row: pd.Series, pop_stats: dict) -> str:
    score     = row['investment_score']
    pred      = row['predicted_price_6m']
    price     = row['median_sale_price']
    pop_score = pop_stats.get('median_investment_score', 50.0)
    change_pct = (pred - price) / price * 100

    if score >= pop_score * 1.1 and change_pct > 0:
        return (
            f"With an investment score of {score:.1f}/100 — {score - pop_score:.1f} points "
            f"above the portfolio median — and a {change_pct:.1f}% price appreciation "
            f"forecast over 6 months, this zip presents a compelling bullish case."
        )
    if score < pop_score * 0.9 or change_pct < 0:
        return (
            f"Proceed with caution: the investment score of {score:.1f}/100 and a "
            f"6-month price forecast of ${pred:,.0f} ({change_pct:+.1f}%) "
            f"suggest the risk-reward balance warrants careful diligence."
        )
    return (
        f"An investment score of {score:.1f}/100 and a 6-month price target of "
        f"${pred:,.0f} ({change_pct:+.1f}%) position this market as a neutral "
        f"hold — worth watching for improving signals."
    )


# ── Public API ────────────────────────────────────────────────────────────────

def generate_investment_narrative(row: pd.Series, pop_stats: dict) -> str:
    """Assemble a 4-5 sentence investment narrative using template + component method.

    No API calls. All numbers interpolated from row and pop_stats.
    """
    branch = _select_branch(row, pop_stats)

    fmt = dict(
        zip=row['zip_code'],
        score=row['investment_score'],
        grade=row['investment_grade'],
        segment=row['market_segment'],
        appr=row['yoy_appreciation'],
        appr_delta=row['yoy_appreciation'] - pop_stats['median_yoy_appreciation'],
        appr_delta_abs=abs(row['yoy_appreciation'] - pop_stats['median_yoy_appreciation']),
        yield_val=row['gross_rental_yield'],
        pop_yield=pop_stats['median_gross_rental_yield'],
        yield_delta=abs(row['gross_rental_yield'] - pop_stats['median_gross_rental_yield']),
        pop_appr=pop_stats['median_yoy_appreciation'],
        heat=row['market_heat_index'],
        pop_heat=pop_stats['median_market_heat_index'],
    )

    opener   = OPENERS[branch].format(**fmt)
    price    = _price_sentence(row, pop_stats)
    yield_s  = _yield_sentence(row, pop_stats)
    activity = _activity_sentence(row, pop_stats)
    closing  = _closing_sentence(row, pop_stats)

    return ' '.join([opener, price, yield_s, activity, closing])


def get_key_pros_cons(row: pd.Series, pop_stats: dict) -> tuple[list, list]:
    """Return (pros, cons) — each a list of 3 strings with specific numbers."""
    dims = {
        'appreciation': (
            row['yoy_appreciation'], pop_stats['median_yoy_appreciation'],
            f"{row['yoy_appreciation']:.1f}% YoY appreciation",
            f"Appreciation of {row['yoy_appreciation']:.1f}% lags the "
            f"{pop_stats['median_yoy_appreciation']:.1f}% median",
        ),
        'yield': (
            row['gross_rental_yield'], pop_stats['median_gross_rental_yield'],
            f"{row['gross_rental_yield']:.1f}% gross rental yield",
            f"Yield of {row['gross_rental_yield']:.1f}% is below the "
            f"{pop_stats['median_gross_rental_yield']:.1f}% median",
        ),
        'heat': (
            row['market_heat_index'], pop_stats['median_market_heat_index'],
            f"Heat index of {row['market_heat_index']:.0f}/100 — strong demand",
            f"Heat index of {row['market_heat_index']:.0f}/100 signals a slow market",
        ),
        'neighborhood': (
            row['neighborhood_score'], pop_stats['median_neighborhood_score'],
            f"Neighbourhood score {row['neighborhood_score']:.0f}/100 — above average",
            f"Neighbourhood score of {row['neighborhood_score']:.0f}/100 is below median",
        ),
        'dom': (
            100 - row['days_on_market'], 100 - pop_stats['median_days_on_market'],
            f"Fast market — only {int(row['days_on_market'])} days on market",
            f"Slow market — {int(row['days_on_market'])} days on market vs "
            f"{int(pop_stats['median_days_on_market'])} median",
        ),
        'net_yield': (
            row['net_rental_yield'], pop_stats.get('median_net_yield', 0),
            f"{row['net_rental_yield']:.1f}% estimated net rental yield",
            f"Net yield of {row['net_rental_yield']:.1f}% after estimated expenses",
        ),
    }

    pros = [(k, v[2]) for k, v in dims.items() if v[0] >= v[1]]
    cons = [(k, v[3]) for k, v in dims.items() if v[0] < v[1]]

    pros = [t[1] for t in sorted(pros, key=lambda x: dims[x[0]][0] - dims[x[0]][1], reverse=True)][:3]
    cons = [t[1] for t in sorted(cons, key=lambda x: dims[x[0]][1] - dims[x[0]][0], reverse=True)][:3]

    while len(pros) < 3:
        pros.append('Meets portfolio median across remaining dimensions')
    while len(cons) < 3:
        cons.append('No significant underperformance identified')

    return pros, cons


# ── 10-Zip Test ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    from data_loader import generate_synthetic_data
    from feature_engineering import engineer_features
    from models import train_price_model, predict_prices, train_segment_model, label_segments
    from scoring import compute_investment_score

    print("Building pipeline...")
    raw, pop_stats = generate_synthetic_data()
    df, pop_stats  = engineer_features(raw, pop_stats)

    model, _              = train_price_model(df)
    df['predicted_price_6m'] = predict_prices(df, model)

    km_model, km_scaler   = train_segment_model(df)
    df['market_segment']  = label_segments(df, km_model, km_scaler)

    df             = compute_investment_score(df, pop_stats)
    pop_stats['median_investment_score'] = float(df['investment_score'].median())
    pop_stats['median_sale_price']       = float(df['median_sale_price'].median())
    pop_stats['median_net_yield']        = float(df['net_rental_yield'].median())

    latest = df[df['month'] == df['month'].max()]

    test_zips = pd.concat([
        latest[latest['investment_grade'] == g].nlargest(2, 'investment_score')
        for g in sorted(latest['investment_grade'].unique())
    ]).reset_index(drop=True).head(10)

    print(f"\nRunning 10-zip narrative test across {test_zips['investment_grade'].nunique()} grades "
          f"and {test_zips['market_segment'].nunique()} segments\n{'='*70}")

    openers_seen: set[str] = set()
    for _, row in test_zips.iterrows():
        print(f"\n--- {row['zip_code']} | Grade {row['investment_grade']} | {row['market_segment']} ---")
        narrative = generate_investment_narrative(row, pop_stats)
        print(narrative)
        opener = narrative.split('.')[0]
        assert opener not in openers_seen, f"Duplicate opener for {row['zip_code']}"
        openers_seen.add(opener)

        pros, cons = get_key_pros_cons(row, pop_stats)
        print(f"PROS: {pros}")
        print(f"CONS: {cons}")

        assert len(pros) == 3, f"Expected 3 pros, got {len(pros)} for {row['zip_code']}"
        assert len(cons) == 3, f"Expected 3 cons, got {len(cons)} for {row['zip_code']}"
        assert len(narrative.split('. ')) >= 4, f"Fewer than 4 sentences for {row['zip_code']}"

    print(f"\n{'='*70}")
    print(f"All {len(test_zips)} narratives generated. All assertions passed.")
    print(f"Unique openers: {len(openers_seen)} / {len(test_zips)}")
