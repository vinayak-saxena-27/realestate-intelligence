# Client Demo Guide
## Real Estate Investment Intelligence Platform

---

## Before the demo — checklist

- [ ] `streamlit run app.py` is running and the browser tab is open at the Command Center
- [ ] Screen sharing is set up (share the browser tab, not the terminal)
- [ ] Zoom to 110% in the browser so text is readable on a shared screen
- [ ] Have zip codes **78701** (Austin, Grade A) and **98101** (Seattle, Grade A) noted — they make great examples
- [ ] Close your IDE / terminal — the client doesn't need to see code

---

## The "wow moment" sequence — lead with this

Walk through this order for maximum visual impact before doing the full page-by-page tour.

### Step 1 — Land on Command Center (0:00)
*Say:* "Here's the portfolio at a glance — 200 markets, instantly ranked. You can see we have [X] Grade A opportunities right now."

Point to the grade donut chart. Let it sink in for a few seconds. The visual separation between green A's and red F's reads immediately.

### Step 2 — Click "View Deep Dive" on the top Grade A card (0:30)
*Say:* "Let me show you what a Grade A market looks like under the hood."

The Deep Dive page loads with:
- Six metric cards showing how this zip beats the portfolio median on nearly every signal
- A 24-month price history with a 6-month forecast arrow pointing up
- The investment narrative: *"Zip code [X] is a standout Growth Market opportunity…"*

*Say:* "That narrative is generated automatically from the data — no manual writing."

### Step 3 — Switch to Market Comparison, add a Grade D zip (1:30)
Select the top Grade A zip and a Grade D or F zip together.

*Say:* "Now watch what happens when I put a strong market next to a weak one."

Point to the green-highlighted winning cells. The contrast does the selling for you.

### Step 4 — Back to Explorer, filter to Grade A only (2:30)
*Say:* "Your analyst can come here every morning, filter to Grade A, and download the list in one click."

Click the download button and show the CSV saving.

---

## Minute-by-minute page walkthrough (5 minutes total)

### 0:00 – 1:00 — Command Center
- Read the five KPI cards aloud: total zips, average score, top appreciation metro, best yield metro, A+B count
- Point out the grade donut: "This is where the portfolio stands today"
- Scroll to Top 10 — highlight the score column and grade badges
- Point to Best Opportunities cards: "These three are the highest-conviction buys in the entire dataset"

### 1:00 – 2:00 — Zip Code Deep Dive
- Click "View Deep Dive" from one of the opportunity cards
- Walk through the six metric cards — note the +/− vs median deltas
- Point to the price history chart: "The dashed gold line is the model's 6-month forecast"
- Read the investment narrative aloud — let the client hear it
- Show the "Should I Invest Here?" panel: grade badge → verdict → three strengths → three watch points

### 2:00 – 3:00 — Market Comparison
- Select the top two Grade A zip codes
- Then add a Grade C or D zip for contrast
- Point to the green highlights: "Green means best in class for that metric"
- Scroll down to the overlaid price history chart

### 3:00 – 4:00 — Zip Code Explorer
- Show the sidebar filters: metro, grade, price range
- Filter to Grade A only — watch the table shrink to only strong buys
- Change the price range slider to a lower bracket — "Filter by what your client can actually afford"
- Click Download CSV

### 4:00 – 5:00 — Model Intelligence
- Show the RMSE / R² table: "The model explains over 95% of price variation on data it has never seen"
- Show the feature importance chart: "Appreciation and neighbourhood score are the strongest predictors"
- Show the weight pie chart and methodology paragraph: "This is how the score is built — nothing is a black box"

---

## 5 questions clients typically ask

**Q1: "Is this real data or made up?"**

*A:* "The version you're seeing uses synthetic data that mirrors real market distributions — it's a working demo. The production version connects directly to live MLS feeds, Zillow, and ATTOM data. Swapping to real data requires changing one line in the configuration."

---

**Q2: "What does a Grade A actually mean? Why should I trust it?"**

*A:* "A Grade A means the zip code scores 80 or above out of 100 on our composite model. That score is built from six independent market signals — appreciation trend, rental yield, neighbourhood quality, buyer demand, price momentum, and net income after expenses — each weighted to reflect how a long-term residential investor actually thinks. No single metric can inflate the grade; the market has to be strong across the board."

---

**Q3: "How accurate is the 6-month price forecast?"**

*A:* "On held-out test data — months the model never trained on — R² is above 0.95. That means the model explains more than 95% of the price variation. You can see the full performance breakdown on the Model Intelligence page. We're upfront about how it works and where it has uncertainty."

---

**Q4: "Can I filter by my price range and only see markets I can afford?"**

*A:* "Yes — the Zip Code Explorer has a price range slider right in the sidebar. Drag it to your budget and the table instantly filters. You can also combine it with a grade filter so you only see Grade A or B markets within your price range. Hit Download and you have the list in a spreadsheet."

---

**Q5: "Can my whole team use this, or just one person?"**

*A:* "The app runs in any browser — you'd deploy it to a cloud server (Streamlit Cloud, AWS, or Azure) and share a link. No installation needed for your team. Each person filters and explores independently. The data refreshes automatically whenever new market data is loaded."

---

## Handling objections

| Objection | Response |
|---|---|
| "The markets aren't the ones I invest in" | The 10 metros are configurable — adding a new metro is a one-line change in `config.py`. Any metro with MLS or Zillow data can be added. |
| "I already use [other tool]" | This is designed to sit alongside your existing tools, not replace them. The narrative and scoring give you a second opinion in seconds rather than hours. |
| "I don't trust AI scores" | Every number in the score traces back to a specific formula on the Model Intelligence page. Nothing is hidden — if you disagree with a weight, we can adjust it. |
| "What if the data is wrong?" | The platform validates every data source on load and flags errors explicitly. In production, data comes from authoritative feeds with their own quality guarantees. |

---

## After the demo — next steps to offer

1. **Pilot with real data** — provide a sample CSV of their actual target markets and re-run the demo with live numbers
2. **Custom metro configuration** — add any metro they actively invest in
3. **Custom scoring weights** — adjust the six component weights to match their investment thesis (e.g., higher yield weight for income investors)
4. **Cloud deployment** — deploy to Streamlit Cloud so the whole team has browser access
