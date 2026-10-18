-- =============================================================================
-- 40_semantic.sql — Business metrics defined once, in the warehouse
--
-- Two artifacts with the same definitions:
--   1. SV_ORDERS   — Snowflake SEMANTIC VIEW (facts, dimensions, metrics).
--                    Queryable with SEMANTIC_VIEW(...) and usable by Cortex Analyst.
--   2. V_KPI_MONTHLY — plain view with the same KPIs by month and state, used to
--                    reconcile Power BI measures against the warehouse.
-- The DAX measures in powerbi/measures.md mirror these names and formulas.
-- =============================================================================
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COMPUTE_WH;
USE SCHEMA OLIST.MARTS;

CREATE OR REPLACE SEMANTIC VIEW SV_ORDERS
  TABLES (
    orders    AS OLIST.MARTS.FCT_ORDERS    PRIMARY KEY (order_id)           COMMENT = 'One row per order',
    customers AS OLIST.MARTS.DIM_CUSTOMER  PRIMARY KEY (customer_unique_id) COMMENT = 'One row per customer',
    sellers   AS OLIST.MARTS.DIM_SELLER    PRIMARY KEY (seller_id)          COMMENT = 'One row per seller',
    dates     AS OLIST.MARTS.DIM_DATE      PRIMARY KEY (date_key)           COMMENT = 'Calendar'
  )
  RELATIONSHIPS (
    orders (customer_unique_id) REFERENCES customers,
    orders (primary_seller_id)  REFERENCES sellers,
    orders (purchase_date_key)  REFERENCES dates
  )
  FACTS (
    orders.gmv              AS gmv,
    orders.freight_value    AS freight_value,
    orders.review_score     AS review_score,
    orders.delivery_days    AS delivery_days,
    orders.delay_days       AS delay_days,
    orders.is_delivered_int AS IFF(is_delivered, 1, 0),
    orders.is_late_int      AS IFF(is_late, 1, 0),
    orders.is_low_review_int AS IFF(is_low_review, 1, 0),
    orders.has_review_int   AS IFF(has_review, 1, 0)
  )
  DIMENSIONS (
    orders.order_status       AS order_status,
    orders.delivery_bucket    AS delivery_bucket,
    orders.is_interstate      AS is_interstate,
    customers.customer_state  AS customer_state,
    customers.customer_region AS customer_region,
    customers.is_repeat_customer AS is_repeat_customer,
    sellers.seller_state      AS seller_state,
    sellers.seller_region     AS seller_region,
    dates.year_month          AS year_month,
    dates.year                AS year,
    dates.in_analysis_window  AS in_analysis_window
  )
  METRICS (
    orders.order_count        AS COUNT(orders.order_id)                      COMMENT = 'Orders',
    orders.total_gmv          AS SUM(orders.gmv)                             COMMENT = 'GMV: sum of item prices (BRL)',
    orders.avg_order_value    AS SUM(orders.gmv) / NULLIF(COUNT(orders.order_id), 0),
    orders.total_freight      AS SUM(orders.freight_value),
    orders.freight_pct_of_gmv AS SUM(orders.freight_value) / NULLIF(SUM(orders.gmv), 0),
    orders.delivered_orders   AS SUM(orders.is_delivered_int),
    orders.late_orders        AS SUM(orders.is_late_int),
    orders.on_time_pct        AS 1 - SUM(orders.is_late_int) / NULLIF(SUM(orders.is_delivered_int), 0)
                                                                              COMMENT = 'Share of delivered orders delivered on or before the estimated date',
    orders.avg_delivery_days  AS AVG(orders.delivery_days),
    orders.avg_review_score   AS AVG(orders.review_score),
    orders.low_review_pct     AS SUM(orders.is_low_review_int) / NULLIF(SUM(orders.has_review_int), 0)
                                                                              COMMENT = 'Share of reviews with score 1 or 2'
  )
  COMMENT = 'Olist order semantics: single source of truth for GMV, delivery and review KPIs.';

-- Smoke test: KPIs by region.
SELECT * FROM SEMANTIC_VIEW(
  SV_ORDERS
  DIMENSIONS customers.customer_region
  METRICS    orders.order_count, orders.total_gmv, orders.on_time_pct, orders.avg_review_score, orders.low_review_pct
)
ORDER BY order_count DESC;

-- ------------------------------------------------------------- v_kpi_monthly
CREATE OR REPLACE VIEW V_KPI_MONTHLY
  COMMENT = 'Reconciliation view: same KPI formulas as SV_ORDERS, by month and customer state.'
AS
SELECT
  d.year_month,
  f.customer_state,
  COUNT(f.order_id)                                                   AS order_count,
  SUM(f.gmv)                                                          AS total_gmv,
  SUM(f.freight_value)                                                AS total_freight,
  SUM(IFF(f.is_delivered, 1, 0))                                      AS delivered_orders,
  SUM(IFF(f.is_late, 1, 0))                                           AS late_orders,
  1 - SUM(IFF(f.is_late, 1, 0)) / NULLIF(SUM(IFF(f.is_delivered, 1, 0)), 0) AS on_time_pct,
  AVG(f.delivery_days)                                                AS avg_delivery_days,
  AVG(f.review_score)                                                 AS avg_review_score,
  SUM(IFF(f.is_low_review, 1, 0)) / NULLIF(SUM(IFF(f.has_review, 1, 0)), 0) AS low_review_pct
FROM FCT_ORDERS f
JOIN DIM_DATE d ON d.date_key = f.purchase_date_key
GROUP BY 1, 2;

SELECT year_month, SUM(order_count) AS orders, SUM(total_gmv) AS gmv,
       SUM(late_orders) / NULLIF(SUM(delivered_orders), 0) AS late_pct
FROM V_KPI_MONTHLY
GROUP BY 1 ORDER BY 1;
