# Power BI — model setup and measure dictionary

Every measure here mirrors a metric in `sql/40_semantic.sql` (same name, same formula). When a number in Power BI and a number from `V_KPI_MONTHLY` disagree, the SQL wins and the DAX gets fixed.

> The model and report described here are **generated** by [build_pbip.py](build_pbip.py) into the `Olist Delivery Experience/` PBIP folder (see [README.md](README.md)). This file is the human-readable reference; the script is the source of truth for the DAX.

## 1. Connection

| Field | Value |
| --- | --- |
| Connector | Snowflake (Power BI Desktop, implementation 2.0) |
| Server | `fpyndgp-mw62856.snowflakecomputing.com` |
| Warehouse | `COMPUTE_WH` |
| Role | `BI_READER` (read-only on `OLIST.MARTS`; nothing else is visible) |
| Database / schema | `OLIST` / `MARTS` |
| Mode | **Import**. ~100k orders / 113k items load in seconds and visuals stay instant. DirectQuery would make sense for data refreshed intra-day or too large to import; mention it, do not use it here. |
| Tables | `DIM_DATE`, `DIM_CUSTOMER`, `DIM_SELLER`, `DIM_PRODUCT`, `FCT_ORDERS`, `FCT_ORDER_ITEMS` |

Do not import RAW or STG. The BI role cannot see them anyway, which is the point.

## 2. Model

```
DIM_DATE[date_key]              1 ──< FCT_ORDERS[purchase_date_key]
DIM_CUSTOMER[customer_unique_id] 1 ──< FCT_ORDERS[customer_unique_id]
DIM_SELLER[seller_id]           1 ──< FCT_ORDERS[primary_seller_id]

DIM_DATE[date_key]              1 ──< FCT_ORDER_ITEMS[purchase_date_key]
DIM_CUSTOMER[customer_unique_id] 1 ──< FCT_ORDER_ITEMS[customer_unique_id]
DIM_SELLER[seller_id]           1 ──< FCT_ORDER_ITEMS[seller_id]
DIM_PRODUCT[product_id]         1 ──< FCT_ORDER_ITEMS[product_id]
```

- All relationships one-to-many, single direction, from dimension to fact. No fact-to-fact relationship: order-level context (`is_late`, `delivery_bucket`, `review_score`) is already copied onto `FCT_ORDER_ITEMS`.
- Mark `DIM_DATE` as the date table (`date` column). Hide `date_key` columns and all surrogate keys.
- Sort by column: `delivery_bucket` by `delivery_bucket_sort`; `month_short` by `month`; `day_short` by `day_of_week_iso`.
- Hide `FCT_ORDERS[review_score]` and `FCT_ORDER_ITEMS[review_score]` from report view (implicit averages are the wrong grain); expose them only through measures.
- Put every measure in `Key Measures`, a measure-only table with no columns (its Power Query source returns an empty table, which is how Desktop shows the calculator icon). The bare name `Measures` is reserved by Desktop, so the table cannot be called that. Measures are organised in the display folders below.
- Page-level filter on every page except the appendix: `DIM_DATE[in_analysis_window] = True` (Jan-2017 to Aug-2018). Documented in the appendix.

## 3. Measures

Formats: percentages `0.0%`, money `R$ #,##0` (`R$ #,##0.0,,"M"` for KPI cards), days `0.0`, scores `0.00`.

### Sales

```dax
GMV = SUM ( FCT_ORDERS[gmv] )

Orders = COUNTROWS ( FCT_ORDERS )

Avg Order Value = DIVIDE ( [GMV], [Orders] )

Customers = DISTINCTCOUNT ( FCT_ORDERS[customer_unique_id] )

Items Sold = COUNTROWS ( FCT_ORDER_ITEMS )

Items per Order = DIVIDE ( [Items Sold], [Orders] )

GMV (Items) = SUM ( FCT_ORDER_ITEMS[price] )
-- Use on category / product / seller visuals (item grain). Equals [GMV] in total.

GMV MoM % =
VAR _prev = CALCULATE ( [GMV], DATEADD ( DIM_DATE[date], -1, MONTH ) )
RETURN DIVIDE ( [GMV] - _prev, _prev )
```

### Delivery

```dax
Delivered Orders = CALCULATE ( [Orders], FCT_ORDERS[is_delivered] = TRUE () )

Late Orders = CALCULATE ( [Orders], FCT_ORDERS[is_late] = TRUE () )

On-time Delivery % = DIVIDE ( [Delivered Orders] - [Late Orders], [Delivered Orders] )
-- DIVIDE form on purpose: "1 - x" would return 100% for months or states with no deliveries
-- and drag empty categories into every chart.

Late Delivery % = DIVIDE ( [Late Orders], [Delivered Orders] )

Avg Delivery Days =
CALCULATE ( AVERAGE ( FCT_ORDERS[delivery_days] ), FCT_ORDERS[is_delivered] = TRUE () )

Avg Estimated Days =
CALCULATE ( AVERAGE ( FCT_ORDERS[estimated_days] ), FCT_ORDERS[is_delivered] = TRUE () )

Avg Delay Days (late only) =
CALCULATE ( AVERAGE ( FCT_ORDERS[delay_days] ), FCT_ORDERS[is_late] = TRUE () )

Interstate Orders % =
DIVIDE (
    CALCULATE ( [Orders], FCT_ORDERS[is_interstate] = TRUE () ),
    CALCULATE ( [Orders], NOT ISBLANK ( FCT_ORDERS[is_interstate] ) )
)
```

### Experience

```dax
Reviews = CALCULATE ( [Orders], FCT_ORDERS[has_review] = TRUE () )

Avg Review Score = AVERAGE ( FCT_ORDERS[review_score] )

Low Reviews (1-2) = CALCULATE ( [Orders], FCT_ORDERS[is_low_review] = TRUE () )

Low Review % = DIVIDE ( [Low Reviews (1-2)], [Reviews] )

5-star % =
DIVIDE ( CALCULATE ( [Orders], FCT_ORDERS[review_score] = 5 ), [Reviews] )

Avg Review Score (On time) =
CALCULATE ( [Avg Review Score], FCT_ORDERS[delivery_bucket] = "On time" )
-- Never filter with is_late = FALSE(): in DAX, BLANK() = FALSE() evaluates to TRUE, so canceled and
-- in-progress orders (is_late is NULL for them) would leak into the "on time" group. Same rule for
-- every "(On time)" measure and for the scenario measures; is_late = TRUE() is safe.

Avg Review Score (Late) =
CALCULATE ( [Avg Review Score], FCT_ORDERS[is_late] = TRUE () )

Review Gap (On time - Late) =
[Avg Review Score (On time)] - [Avg Review Score (Late)]

Share of on-time reviews =
DIVIDE (
    CALCULATE ( [Reviews], FCT_ORDERS[delivery_bucket] = "On time" ),
    CALCULATE ( [Reviews], FCT_ORDERS[delivery_bucket] = "On time", ALL ( FCT_ORDERS[review_score] ) )
)
-- With review_score on the axis: distribution of scores among on-time orders. Twin measure
-- "Share of late reviews" uses is_late = TRUE(). Plotting the two measures gives a clean legend.

On-time Delivery % (min 100 orders) = IF ( [Orders] >= 100, [On-time Delivery %] )
-- Blanks tiny states (RR, AP, AC) out of rankings without a visual-level filter.

Low Reviews from Late Orders % =
DIVIDE (
    CALCULATE ( [Orders], FCT_ORDERS[is_low_review] = TRUE (), FCT_ORDERS[is_late] = TRUE () ),
    [Low Reviews (1-2)]
)
-- "X% of all 1-2 star reviews come from orders that arrived late."

Repeat Customer % =
DIVIDE (
    CALCULATE ( DISTINCTCOUNT ( DIM_CUSTOMER[customer_unique_id] ), DIM_CUSTOMER[is_repeat_customer] = TRUE () ),
    DISTINCTCOUNT ( DIM_CUSTOMER[customer_unique_id] )
)
-- All-time figure (DIM_CUSTOMER is not filtered by date). Label the card accordingly.
```

### Freight

```dax
Freight Value = SUM ( FCT_ORDERS[freight_value] )

Freight % of GMV = DIVIDE ( [Freight Value], [GMV] )

Freight per Order = DIVIDE ( [Freight Value], [Orders] )
```

### Scenario (page 4, what-if)

Create a numeric range parameter **Late Reduction %** (0 to 100, step 5, default 50). Power BI generates the table `Late Reduction %` and the measure `[Late Reduction % Value]`.

Logic: if a share X of the late orders in the current filter context had been delivered on time, assume those orders would have received the on-time average score instead of the late average.

```dax
Scenario Avg Review Score =
VAR _x          = DIVIDE ( [Late Reduction % Value], 100 )
VAR _lateRev    = CALCULATE ( [Reviews], FCT_ORDERS[is_late] = TRUE () )
VAR _moved      = _lateRev * _x
VAR _totalScore = SUM ( FCT_ORDERS[review_score] )
VAR _newScore   = _totalScore + _moved * ( [Avg Review Score (On time)] - [Avg Review Score (Late)] )
RETURN DIVIDE ( _newScore, [Reviews] )

Scenario Uplift = [Scenario Avg Review Score] - [Avg Review Score]

Scenario Low Reviews Avoided =
VAR _x        = DIVIDE ( [Late Reduction % Value], 100 )
VAR _lateRev  = CALCULATE ( [Reviews], FCT_ORDERS[is_late] = TRUE () )
VAR _lowLate  = DIVIDE ( CALCULATE ( [Low Reviews (1-2)], FCT_ORDERS[is_late] = TRUE () ), _lateRev )
VAR _lowOnTm  = DIVIDE ( CALCULATE ( [Low Reviews (1-2)], FCT_ORDERS[is_late] = FALSE () ),
                         CALCULATE ( [Reviews], FCT_ORDERS[is_late] = FALSE () ) )
RETURN _lateRev * _x * ( _lowLate - _lowOnTm )
```

### Dynamic titles (insight headlines)

```dax
Title | Overview =
FORMAT ( [Orders], "#,0" ) & " orders and R$ " & FORMAT ( [GMV] / 1e6, "0.0" ) & "M in GMV — "
    & FORMAT ( [Late Delivery %], "0.0%" ) & " of deliveries arrived late and the average review is "
    & FORMAT ( [Avg Review Score], "0.00" )

Title | Delivery vs Experience =
"Late deliveries score " & FORMAT ( [Avg Review Score (Late)], "0.0" ) & " stars vs "
    & FORMAT ( [Avg Review Score (On time)], "0.0" ) & " when on time — "
    & FORMAT ( [Low Reviews from Late Orders %], "0%" ) & " of all 1-2 star reviews come from late orders"

Title | Where =
"Interstate routes: " & FORMAT ( CALCULATE ( [Late Delivery %], FCT_ORDERS[is_interstate] = TRUE () ), "0.0%" )
    & " late vs " & FORMAT ( CALCULATE ( [Late Delivery %], FCT_ORDERS[is_interstate] = FALSE () ), "0.0%" )
    & " within the same state"

Title | Scenario =
"Cutting late deliveries by " & FORMAT ( [Late Reduction % Value], "0" ) & "% lifts the average review from "
    & FORMAT ( [Avg Review Score], "0.00" ) & " to " & FORMAT ( [Scenario Avg Review Score], "0.00" )
```

## 4. Field parameter for page 3

**Breakdown** (Modeling > New parameter > Fields): `DIM_CUSTOMER[customer_state]`, `DIM_CUSTOMER[customer_region]`, `DIM_SELLER[seller_state]`, `DIM_PRODUCT[category_label]`, `DIM_PRODUCT[weight_band]`. One bar chart, one slicer, five views.

## 5. Reconciliation routine (before the interview)

1. In Snowsight run the last query of `sql/40_semantic.sql` (`V_KPI_MONTHLY` by month).
2. In Power BI build a hidden table visual: `year_month`, `[Orders]`, `[GMV]`, `[Late Delivery %]` with the analysis-window filter **off**.
3. The two must match to the cent. Screenshot both for the appendix page.

## 6. Added in v0.3 (loyalty, Pareto, time split, calendar)

Columns shown to users now carry display names (`Customer State`, `Delivery Outcome`, `Month`, `Weekday`...);
the generator rewrites every DAX reference, so the technical names below still work in `build_pbip.py`.

```dax
-- Where the pool is (page 3 Pareto)
Share of Late Orders = DIVIDE ( [Late Orders], CALCULATE ( [Late Orders], ALL ( DIM_CUSTOMER ) ) )

Cumulative Share of Late Orders =
VAR _cur = [Late Orders]
VAR _states = ALLSELECTED ( DIM_CUSTOMER[Customer State] )
VAR _total = CALCULATE ( [Late Orders], _states )
VAR _cum = SUMX ( FILTER ( _states, [Late Orders] >= _cur ), [Late Orders] )
RETURN DIVIDE ( _cum, _total )

-- Where the days go (page 2): calculated columns Seller Handling Days = approved -> carrier,
-- Carrier Transit Days = carrier -> customer, averaged over delivered orders
Avg Seller Handling Days = CALCULATE ( AVERAGE ( FCT_ORDERS[Seller Handling Days] ), FCT_ORDERS[is_delivered] = TRUE () )
Avg Carrier Transit Days = CALCULATE ( AVERAGE ( FCT_ORDERS[Carrier Transit Days] ), FCT_ORDERS[is_delivered] = TRUE () )

-- Loyalty (page 4): Is First Order = the customer's earliest order; repeat status is all-time
Repeat Rate after Late First Order =
VAR _c = CALCULATETABLE ( VALUES ( FCT_ORDERS[customer_unique_id] ),
                          FCT_ORDERS[Is First Order] = TRUE (), FCT_ORDERS[is_late] = TRUE () )
RETURN DIVIDE (
    CALCULATE ( COUNTROWS ( DIM_CUSTOMER ), DIM_CUSTOMER[Repeat Customer?] = TRUE (),
                TREATAS ( _c, DIM_CUSTOMER[customer_unique_id] ) ),
    COUNTROWS ( _c ) )
-- twin measures: after On-time First Order (Delivery Outcome = "On time"), after Low-review First Order
```

Calendar: a DAX table `Holidays` (Brazilian national holidays, Carnival and Black Friday 2017-2018) feeds
`DIM_DATE[Near Holiday?]` and `DIM_DATE[Purchase Period]` (±3 days). `Definitions` is a DAX table that
drives the Definitions page, reached from the ⓘ button on every page.
