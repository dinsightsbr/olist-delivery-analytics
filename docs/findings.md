# Findings — numbers validated in Snowflake (16/10/2026)

Source: `OLIST.MARTS`, queried through `SV_ORDERS` and `90_checks.sql`. "Window" = orders purchased Jan-2017 to Aug-2018 (`DIM_DATE.in_analysis_window`), which drops the sparse edges of the dataset. Money in BRL.

## Data quality checks (all passed)

| Check | Result |
| --- | --- |
| `FCT_ORDERS` unique by order_id | true |
| `FCT_ORDER_ITEMS` unique by order_id + item | true |
| GMV reconciles RAW → MARTS (sum of item prices) | true — R$ 13,591,643.70 all time |
| Freight reconciles RAW → MARTS | true |
| Orders without customer / items without product / items without seller | 0 / 0 / 0 |
| Orders without items | 775 — all canceled/unavailable; kept and documented |
| Rows loaded vs Kaggle | identical: 99,441 orders · 112,650 items · 103,886 payments · 99,224 reviews · 96,096 unique customers · 3,095 sellers · 32,951 products |

## Headline numbers (window)

| Metric | Value |
| --- | --- |
| Orders | 99,092 |
| GMV | R$ 13.54M |
| Avg order value | R$ 136.66 |
| Delivered orders | 96,203 |
| Late orders (after estimated date) | 6,531 |
| **On-time delivery %** | **93.2%** (6.8% late) |
| Avg delivery time | 12.5 days (estimate shown to customer: 24.3 days) |
| Avg delay when late | 10.6 days |
| Reviews | 98,330 |
| **Avg review score** | **4.09** |
| Avg review — on-time orders | **4.29** |
| Avg review — late orders | **2.27** |
| Low reviews (1–2 stars) | 14,382 (14.6% of reviews) |
| Low-review rate — on time | 9.3% |
| Low-review rate — late | **62.4%** (6.7× higher) |
| Share of all low reviews that came from late orders | 27.7% |
| Freight as % of GMV | 16.6% |
| Interstate orders (seller state ≠ customer state) | 64.0% |
| On-time % — interstate vs same state | 91.9% vs 95.5% |
| Unique customers (all time) | 96,096 |
| **Repeat customers (all time)** | **3.1%** |

## By customer state (window, states with ≥ 100 orders, worst on-time first)

| State | Region | Orders | GMV (R$) | On-time | Avg days | Avg review | Low-review % | Freight % GMV |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AL | Nordeste | 410 | 80,232 | 78.5% | 24.5 | 3.76 | 23.8% | 19.8% |
| MA | Nordeste | 746 | 119,257 | 82.5% | 21.4 | 3.76 | 21.8% | 26.3% |
| SE | Nordeste | 348 | 58,811 | 84.7% | 21.3 | 3.80 | 22.0% | 24.0% |
| PI | Nordeste | 493 | 86,704 | 86.1% | 19.4 | 3.92 | 18.4% | 24.4% |
| CE | Nordeste | 1,331 | 225,797 | 86.2% | 21.2 | 3.86 | 19.7% | 21.3% |
| BA | Nordeste | 3,374 | 510,226 | 87.8% | 19.3 | 3.86 | 18.9% | 19.6% |
| **RJ** | Sudeste | **12,795** | 1,812,827 | **87.8%** | 15.2 | 3.88 | 20.6% | 16.8% |
| PA | Norte | 971 | 177,860 | 88.7% | 23.7 | 3.85 | 19.6% | 21.6% |
| ES | Sudeste | 2,030 | 274,209 | 89.3% | 15.7 | 4.04 | 14.9% | 18.1% |
| PB | Nordeste | 533 | 114,969 | 89.7% | 20.3 | 4.02 | 16.5% | 22.3% |
| TO | Norte | 280 | 49,622 | 90.1% | 17.6 | 4.10 | 13.6% | 23.6% |
| MS | Centro-Oeste | 714 | 116,643 | 90.3% | 15.5 | 4.11 | 14.6% | 16.4% |
| PE | Nordeste | 1,644 | 261,207 | 90.3% | 18.4 | 4.00 | 16.8% | 22.6% |
| RN | Nordeste | 481 | 82,306 | 90.6% | 19.2 | 4.10 | 14.3% | 22.7% |
| SC | Sul | 3,625 | 517,723 | 91.8% | 14.9 | 4.08 | 14.5% | 17.3% |
| GO | Centro-Oeste | 2,010 | 293,895 | 93.5% | 15.5 | 4.04 | 14.8% | 18.0% |
| MT | Centro-Oeste | 904 | 156,211 | 93.9% | 18.0 | 4.11 | 13.6% | 18.9% |
| RS | Sul | 5,441 | 746,242 | 93.9% | 15.2 | 4.14 | 13.3% | 18.1% |
| DF | Centro-Oeste | 2,131 | 300,760 | 94.4% | 12.9 | 4.07 | 15.0% | 16.7% |
| MG | Sudeste | 11,587 | 1,580,258 | 95.4% | 11.9 | 4.14 | 13.2% | 17.1% |
| **SP** | Sudeste | **41,626** | 5,190,049 | **95.5%** | 8.7 | 4.18 | 12.6% | 13.8% |
| PR | Sul | 5,023 | 680,113 | 95.9% | 11.9 | 4.18 | 12.5% | 17.2% |
| RO | Norte | 254 | 46,260 | 97.1% | 19.3 | 4.05 | 15.4% | 24.8% |
| AM | Norte | 148 | 22,357 | 97.2% | 26.4 | 4.21 | 14.4% | 24.5% |

## What the numbers say (the story)

1. **Growth without loyalty.** R$ 13.5M GMV and ~99k orders in 20 months, but only 3.1% of customers ever bought twice. Every bad first experience is probably the last one.
2. **Late delivery is the most toxic experience in the data.** A late order has a 62% chance of a 1–2 star review versus 9% when on time (6.7×). Average score drops from 4.29 to 2.27. Late orders are 6.8% of deliveries but produce 27.7% of all low reviews.
3. **It is not the whole story, and saying so builds credibility.** 72% of low reviews come from on-time orders, so product/seller problems matter too. That is the next investigation (review-comment themes with Snowflake Cortex), not this one.
4. **Two different "where" problems:**
   - **Rio de Janeiro** — the second-largest market (12.8k orders, R$ 1.8M) with an on-time rate of 87.8%, the same as Bahia, even though it sits next to São Paulo where most sellers are. RJ alone generates roughly 1,500 late orders, the largest absolute pool outside SP. This looks like a carrier/last-mile execution problem, not distance.
   - **Northeast** — every state in the bottom six is in the Nordeste: 78–88% on time, 19–25 days to deliver, freight eating 20–26% of GMV (vs 14% in SP). This is a structural network and promise-setting problem.
5. **The promise is padded.** Customers are told 24 days on average and receive in 12.5. The estimate is conservative everywhere, yet still missed 6.8% of the time — so the problem is variance, not the average. The right lever is reliability by lane, not a bigger buffer.
6. **Interstate matters, but less than geography.** Interstate orders are 64% of the volume and run 91.9% on time vs 95.5% within state; the state table shows the real spread.

## Review-comment themes (all time, 1–2 star reviews with a comment)

Cortex AI functions (`CLASSIFY_TEXT`, `AI_CLASSIFY`) are **not available on trial accounts**, so the classification is rule-based SQL over the Portuguese comments (`sql/50_cortex.sql`, table `MARTS.REVIEW_THEMES_RULES`). Spot-checked 3 random comments per theme: rules are right most of the time; "Other" holds the misses (defects and wrong items phrased in unusual ways), so the true shares of defect and wrong-item are somewhat higher than shown. In production the CASE becomes `AI_CLASSIFY` and the rules stay as a regression test.

| Theme | Reviews | Share | From late orders | From on-time orders | From undelivered | Avg score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Other (rules did not match) | 3,819 | 35.2% | 769 | 2,548 | 502 | 1.25 |
| **Product not received** | **3,428** | **31.6%** | 1,555 | **1,142** | 731 | 1.12 |
| Wrong or incomplete order | 1,488 | 13.7% | 54 | 1,403 | 31 | 1.21 |
| Product quality or defect | 752 | 6.9% | 21 | 719 | 12 | 1.23 |
| Customer service or refund | 745 | 6.9% | 104 | 414 | 227 | 1.14 |
| Late delivery (explicit) | 607 | 5.6% | 244 | 261 | 102 | 1.30 |
| Total | 10,839 | 100% | 2,747 | 6,487 | 1,605 | |

What this adds to the story:

- **"Delivered" is not "received".** 1,142 orders are marked delivered *on time* by the timestamps, yet the customer wrote that the product never arrived (10.5% of all commented low reviews; ~1.3% of on-time deliveries). The on-time KPI understates the delivery problem; there is a carrier confirmation / misdelivery issue the dashboard cannot see from timestamps alone.
- **Why late orders score 2.27:** of the 2,747 complaints from late orders, 1,799 (65%) say "not received" or "late". The review survey goes out when the estimated date passes, so a late customer is asked for a rating before the box arrives.
- **Split shipments:** "wrong or incomplete" is 13.7% and 94% of it comes from on-time orders — multi-item orders arriving in parts (different sellers). Operational, not product.
- **Product defects are small (6.9%).** The marketplace's problem is logistics and fulfilment, not what is being sold.
- Delivery in the broad sense (not received + late + part of service) explains at least 37% of commented low reviews, versus the 28% the timestamp-only view gives.

## Recommendations to present (page 4)

| # | Action | Target | Rationale | Effort |
| --- | --- | --- | --- | --- |
| 1 | Carrier/last-mile review for RJ lanes (SP→RJ) | On-time RJ from 87.8% to ≥ 93% (national avg) | Largest absolute late pool; short distance; execution issue | Medium |
| 2 | Re-set delivery promises by lane for the Northeast (and pick partners by lane reliability) | Late rate NE ≤ 10% | 19–25 day lead times with high variance; late rate 12–22% | Medium–High |
| 3 | Proactive communication on orders past the estimated date (status + apology + voucher) | Low-review rate on late orders from 62% toward the on-time 9% | Cheapest lever; addresses perception while logistics is fixed | Low |
| 4 | Delivery-confirmation audit: the ~1,100 "delivered on time" orders whose customers say nothing arrived (proof of delivery, misdelivery, carrier scans) | Close the gap between "delivered" and "received" | The on-time KPI is blind to it; found only in comments | Medium |
| 5 | Weekly "late orders" alert by seller and lane, from this same model | Keeps the fix visible | Operational follow-through | Low |
| 6 | Production: classify all review comments with Cortex (`AI_CLASSIFY`), keep the rule set as regression test; add a split-shipment flag for multi-seller orders | Size the remaining 35% "Other" and the 14% incomplete orders | Trial account could not run Cortex | Low |

What-if to show: with the Late Reduction parameter at 50% applied to the whole window, ~3,265 late orders move to on-time behaviour, lifting the average score by about +0.07 (from 4.09 to ~4.16) and avoiding ~1,700 one- and two-star reviews. Filter the scenario to RJ + Nordeste to show where it bites. (Power BI will compute the exact figures; these are back-of-envelope from the table above.)
