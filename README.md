# NOXVÉ Analytics

Data analytics project I built while going through the CodeWithHarry Data Analytics course. I run a D2C streetwear brand called NOXVÉ (Shopify + Qikink for print-on-demand), so instead of doing another Kaggle dataset project, I decided to build a project around my own brand.

**Important - read this before you use this anywhere:** NOXVÉ hasn't actually done this much business yet, this isn't real sales data. I generated a synthetic dataset myself using Python, but I built it to actually match how my brand really works - same products, same pricing, COD being the default payment option like most India D2C brands, festive season spikes around Diwali, the whole thing. So the patterns and the analysis are realistic even though the specific numbers are made up. I'm not going to pretend this is real revenue anywhere, on my resume or in an interview. If someone asks, I'll just tell them straight up that I built a synthetic dataset around my own brand's context because I don't have enough real orders yet to analyze. That's a normal thing to do for a portfolio project.

## What questions I was trying to answer

- How did revenue/orders move month to month, any patterns
- Which products actually make money vs which ones just sell
- Is COD actually hurting the business (higher return rate compared to prepaid)
- Which cities and which marketing channels are worth it
- Do discount codes actually help or do they just cut into margin
- How much revenue comes from repeat customers vs one-time buyers
- Who are my "best" customers vs the ones I'm about to lose (RFM)
- Are people actually coming back to buy again (retention/cohorts)

## What I found

Total delivered revenue came out to ₹15,17,671 across 646 delivered orders (out of 835 placed), avg order value ₹2,349.

The thing that actually surprised me (well, "surprised" - it's my synthetic data so I sort of expected it, but it's still a real problem in India D2C in general): COD orders have an 18.3% return-to-origin rate vs just 4.3% for prepaid. Ran a chi-square test to check if that's actually significant and not just noise - it is (p < 0.001). This is a genuinely useful insight even outside the project - probably worth giving people a small discount to pay online instead of COD.

Combos are doing better than individual items even though there's only 3 combo SKUs out of 12 products total. Makes sense honestly, bundling usually works.

Repeat customers are about 19.5% of everyone who's bought, but they're bringing in 18.7% of revenue, so roughly proportional right now, but retention drops off fast after the first month based on the cohort chart, that's probably the biggest thing to fix for "year 2."

Influencer marketing had the best ROAS at 3.47x, better than Instagram ads (2.79x) and Google ads (2.10x), despite getting the smallest budget of the three. Might be worth pushing more budget there.

Nagpur is the top city by revenue which tracks since that's my own network, but Mumbai and Nashik have the worst RTO rates (~22%), might be worth looking into why.

RFM-wise, about a quarter of customers are "Champions" (high value, recent, frequent), but almost half fall into "needs attention" - so there's a lot of people who bought once and never came back.

## What's actually in here

- `sql/` - schema + 12 SQL queries for all of the above questions, ran against a SQLite db
- `python/generate_data.py` - the script that builds the fake-but-realistic dataset
- `python/eda_and_segmentation.py` - cleaning, EDA, RFM scoring, cohort analysis, the chi-square test, generates all the charts
- `python/generate_excel.py` - builds the Excel file
- `excel/NOXVE_Sales_Report.xlsx` - fully formula based (SUMIFS, COUNTIFS, VLOOKUP etc, no hardcoded numbers) since Advanced Excel is a big chunk of the course
- `data/` - all the csvs plus two files (`bi_master_table.csv`, `customer_rfm_segments.csv`) that are ready to import into Power BI or Tableau once I get to those modules
- `charts/` - the 6 charts from the python script
- repo is already git init'd and committed, just need to push it to GitHub

## How to run it

```
pip install -r requirements.txt
cd python
python generate_data.py
python eda_and_segmentation.py
python generate_excel.py
```

Or just open the db directly: `sqlite3 noxve_analytics.db` and run stuff from `sql/analysis_queries.sql`.

## Power BI / Tableau - haven't gotten there yet in the course

Data's ready for it though. Once I get to that part of the course, plan is to build:
- an overview page - KPI cards + monthly revenue trend
- a products page - revenue by product, category breakdown
- a customers page - the RFM segments, the cohort retention as a heatmap
- a page just for the COD/RTO thing by city, since that's the most "real" insight here

## Resume bullets (need to say "simulated" every time, not just once in this file)

- Built a simulated 12-month sales dataset (800+ orders) modeled on my own D2C brand's actual product catalog and India-market constraints (COD-heavy, festive seasonality) to practice a full SQL/Python/Excel analytics workflow
- Used a chi-square test to show COD orders have a statistically significant higher return rate than prepaid orders (18.3% vs 4.3%, p<0.001) and turned that into an actual recommendation
- Did RFM segmentation + cohort retention analysis in Pandas to split customers into value tiers
- Built an Excel workbook that's 100% formula driven (SUMIFS/COUNTIFS/VLOOKUP), no hardcoded values, 2000+ formulas

If someone asks about it in an interview, just explain it straight: brand is real, data isn't, built it this way on purpose to practice before I had enough real orders to work with.

## Things I could add later

- swap in real Shopify export once there's actual order volume, schema's close enough to a real Shopify export that it shouldn't need a rewrite
- try KMeans on the RFM data instead of just quartile scoring, compare the two
- turn the chi-square test into something reusable, I'll probably want to run a similar test on the discount code data at some point
