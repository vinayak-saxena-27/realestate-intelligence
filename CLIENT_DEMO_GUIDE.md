# Client Demo Guide
## Real Estate Investment Intelligence Platform

---

## Before the demo — checklist

- [ ] `streamlit run app.py` is running and the browser tab is open at the Market Overview page
- [ ] Screen sharing is set up (share the browser tab, not the terminal)
- [ ] Zoom to 110% in the browser so text is readable on a shared screen
- [ ] Have zip codes **78701** (Austin, Grade A) and **98101** (Seattle, Grade A) noted — they make great examples
- [ ] Add **78701** to your watchlist in advance so the Watchlist page already has data in it
- [ ] Close your IDE / terminal — the client doesn't need to see code

---

## The "wow moment" sequence — lead with this

Walk through this order for maximum visual impact before doing the full page-by-page tour.

### Step 1 — Land on Command Center (0:00)
*Say:* "Here's the portfolio at a glance — 200 markets, instantly ranked. You can see we have [X] Grade A opportunities right now."

Point to the grade donut chart. Let it sink in for a few seconds. The visual separation between green A's and red F's reads immediately.

### Step 2 — Click "View Full Analysis" on the top Grade A card (0:30)
*Say:* "Let me show you what a Grade A market looks like under the hood."

The Deep Dive page loads with:
- Six metric cards showing how this zip beats the portfolio median on nearly every signal
- A 24-month price history with a 6-month forecast
- The investment narrative: *"Zip code [X] is a standout Growth Market opportunity…"*

*Say:* "That narrative is generated automatically from the data — no manual writing."

### Step 3 — Download the report (1:15)
Scroll down to the Export Report section and click **Download Report**.

*Say:* "Every zip code can be exported as a formatted investment report in one click. Open it in any browser and it's ready to share or print as a PDF."

### Step 4 — Switch to Market Comparison, add a Grade D zip (2:00)
Select the top Grade A zip and a Grade D or F zip together.

*Say:* "Now watch what happens when I put a strong market next to a weak one."

Point to the green-highlighted winning cells. The contrast does the selling for you.

### Step 5 — Back to Explorer, show the filters (3:00)
*Say:* "Your analyst can come here every morning, filter to Grade A, set a price range, and download the list in one click."

Show the grade filter with full labels ("A — Strong Buy"), the $K price slider, and the Score range slider. Click the download button.

---

## Minute-by-minute page walkthrough (6 minutes total)

### 0:00 – 0:30 — Market Overview (home)
- Point to the grade distribution chips at the top
- Pan around the map — "Every bubble is a zip code; size = investment score, colour = grade"
- Hover over a Grade A bubble to show the tooltip

### 0:30 – 1:30 — Command Center
- Read the five KPI cards aloud: total zips, average score, top appreciation metro, best yield metro, A+B count
- Point out the grade donut: "This is where the portfolio stands today"
- Scroll to Top 10 — highlight the score column and grade badges
- Point to Best Opportunities cards: "These three are the highest-conviction buys in the entire dataset"

### 1:30 – 3:00 — Zip Code Deep Dive
- Click "View Full Analysis" from one of the opportunity cards
- Walk through the six metric cards — note the +/− vs median deltas
- Point to the price history chart: "The dashed gold line is the model's 6-month forecast"
- Point to the score breakdown bars: "Green means above the portfolio median, red means below"
- Read the investment narrative aloud — let the client hear it
- Show the "Should I Invest Here?" panel: grade badge → verdict → three strengths → three watch points
- **Show Export Report:** click Download Report — "A formatted report, ready to share or print as PDF"
- **Show Similar Markets:** scroll to the bottom — "The platform automatically finds the four most comparable zip codes in the same market cluster"
- **Show Add to Watchlist:** click the button — "You can pin markets you're tracking"

### 3:00 – 4:00 — Market Comparison
- Select the top two Grade A zip codes
- Then add a Grade C or D zip for contrast
- Point to the green highlights: "Green means best in class for that metric"
- Scroll down to the overlaid price history chart

### 4:00 – 5:00 — Zip Code Explorer
- Show the sidebar filters: "Grade A — Strong Buy" label, price range in $K, score range slider, segment filter
- Filter to Grade A only — watch the table shrink
- Change the sort to "YoY Appreciation ↓" — "You can re-sort the entire table instantly"
- Click Download CSV

### 5:00 – 6:00 — Watchlist + Model Intelligence
- Navigate to Watchlist — show the aggregate KPI cards across the pinned zips
- *Say:* "If you're tracking a shortlist of markets, this page shows your blended yield and average score at a glance"
- Quick visit to Model Intelligence — show RMSE / R² and feature importance: "Nothing is a black box — every weight is documented"

---

## 6 questions clients typically ask

**Q1: "Is this real data or made up?"**

*A:* "The version you're seeing uses synthetic data that mirrors real market distributions — it's a working demo. The production version connects directly to live MLS feeds, Zillow, and ATTOM data. Swapping to real data requires changing one line in the configuration."

---

**Q2: "What does a Grade A actually mean? Why should I trust it?"**

*A:* "A Grade A means the zip code scores 80 or above out of 100 on our composite model. That score is built from six independent market signals — appreciation trend, rental yield, neighbourhood quality, buyer demand, price momentum, and net income after expenses — each weighted to reflect how a long-term residential investor actually thinks. No single metric can inflate the grade; the market has to be strong across the board. You can see exactly how the score is built on the Model Intelligence page."

---

**Q3: "How accurate is the 6-month price forecast?"**

*A:* "On held-out test data — months the model never trained on — R² is above 0.95. That means the model explains more than 95% of the price variation. You can see the full performance breakdown on the Model Intelligence page. We're upfront about how it works and where it has uncertainty."

---

**Q4: "Can I filter by my price range and only see markets I can afford?"**

*A:* "Yes — the Zip Code Explorer has a price range slider right in the sidebar, plus a score range filter and a market segment filter. Drag them to match your criteria and the table instantly updates. You can combine any filters — for example, Grade A or B markets, under $500K, in the Growth Market segment. Hit Download and you have the list in a spreadsheet."

---

**Q5: "Can I save the markets I'm interested in?"**

*A:* "Yes — that's the Watchlist. On any Deep Dive page, one click adds the zip to your watchlist. The Watchlist page shows aggregate metrics across all your pinned markets — blended yield, average score, appreciation — so you can track a shortlist over time. It persists between sessions."

---

**Q6: "Can my whole team use this, or just one person?"**

*A:* "The app runs in any browser — you'd deploy it to a cloud server (Streamlit Cloud, AWS, or Azure) and share a link. No installation needed for your team. Each person filters and explores independently. The data refreshes automatically whenever new market data is loaded."

---

## Handling objections

| Objection | Response |
|---|---|
| "The markets aren't the ones I invest in" | The 10 metros are configurable — adding a new metro is a one-line change in `config.py`. Any metro with MLS or Zillow data can be added. |
| "I already use [other tool]" | This is designed to sit alongside your existing tools, not replace them. The narrative, scoring, and one-click report give you a second opinion in seconds rather than hours. |
| "I don't trust AI scores" | Every number in the score traces back to a specific formula on the Model Intelligence page. Nothing is hidden — if you disagree with a weight, we can adjust it. |
| "What if the data is wrong?" | The platform validates every data source on load and flags errors explicitly. In production, data comes from authoritative feeds with their own quality guarantees. |
| "Can I share the analysis with my partners?" | Yes — use the Export Report button on any Deep Dive page to download a formatted report. Open it in a browser and print to PDF. No special software required. |

---

## After the demo — next steps to offer

1. **Pilot with real data** — provide a sample CSV of their actual target markets and re-run the demo with live numbers
2. **Custom metro configuration** — add any metro they actively invest in
3. **Custom scoring weights** — adjust the six component weights to match their investment thesis (e.g., higher yield weight for income investors)
4. **Cloud deployment** — deploy to Streamlit Cloud so the whole team has browser access with a shared watchlist
