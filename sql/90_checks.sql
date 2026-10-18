-- =============================================================================
-- 90_checks.sql — Reconciliation and data-quality checks
-- Every query should return expected = TRUE (or zero rows where stated).
-- These are the numbers to quote when someone asks "how do you know
-- the dashboard is right?".
-- =============================================================================
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COMPUTE_WH;
USE DATABASE OLIST;

-- 1. Grain: no duplicate keys in STG / MARTS
SELECT 'stg_orders unique order_id' AS check, COUNT(*) = COUNT(DISTINCT order_id) AS passed FROM STG.STG_ORDERS
UNION ALL SELECT 'stg_reviews one per order',  COUNT(*) = COUNT(DISTINCT order_id) FROM STG.STG_REVIEWS
UNION ALL SELECT 'stg_payments one per order', COUNT(*) = COUNT(DISTINCT order_id) FROM STG.STG_PAYMENTS
UNION ALL SELECT 'dim_customer unique key',    COUNT(*) = COUNT(DISTINCT customer_unique_id) FROM MARTS.DIM_CUSTOMER
UNION ALL SELECT 'dim_seller unique key',      COUNT(*) = COUNT(DISTINCT seller_id) FROM MARTS.DIM_SELLER
UNION ALL SELECT 'dim_product unique key',     COUNT(*) = COUNT(DISTINCT product_id) FROM MARTS.DIM_PRODUCT
UNION ALL SELECT 'fct_orders unique order_id', COUNT(*) = COUNT(DISTINCT order_id) FROM MARTS.FCT_ORDERS
UNION ALL SELECT 'fct_order_items unique key', COUNT(*) = COUNT(DISTINCT order_id || '-' || order_item_id) FROM MARTS.FCT_ORDER_ITEMS;

-- 2. Row counts RAW -> STG -> MARTS (nothing lost, nothing invented)
SELECT 'orders'  AS entity, (SELECT COUNT(*) FROM RAW.ORDERS) AS raw_rows, (SELECT COUNT(*) FROM STG.STG_ORDERS) AS stg_rows, (SELECT COUNT(*) FROM MARTS.FCT_ORDERS) AS mart_rows
UNION ALL
SELECT 'items',  (SELECT COUNT(*) FROM RAW.ORDER_ITEMS), (SELECT COUNT(*) FROM STG.STG_ORDER_ITEMS), (SELECT COUNT(*) FROM MARTS.FCT_ORDER_ITEMS)
UNION ALL
SELECT 'sellers',(SELECT COUNT(*) FROM RAW.SELLERS), (SELECT COUNT(*) FROM STG.STG_SELLERS), (SELECT COUNT(*) FROM MARTS.DIM_SELLER)
UNION ALL
SELECT 'products',(SELECT COUNT(*) FROM RAW.PRODUCTS), (SELECT COUNT(*) FROM STG.STG_PRODUCTS), (SELECT COUNT(*) FROM MARTS.DIM_PRODUCT);

-- 3. Money reconciles: sum of raw item prices = GMV in both facts
SELECT
  (SELECT SUM(TRY_TO_NUMBER(price, 12, 2))         FROM RAW.ORDER_ITEMS)      AS raw_price_total,
  (SELECT SUM(gmv)                                 FROM MARTS.FCT_ORDERS)     AS fct_orders_gmv,
  (SELECT SUM(price)                               FROM MARTS.FCT_ORDER_ITEMS) AS fct_items_gmv,
  (SELECT SUM(TRY_TO_NUMBER(freight_value, 12, 2)) FROM RAW.ORDER_ITEMS)      AS raw_freight_total,
  (SELECT SUM(freight_value)                       FROM MARTS.FCT_ORDERS)     AS fct_orders_freight,
  raw_price_total = fct_orders_gmv AND fct_orders_gmv = fct_items_gmv AND raw_freight_total = fct_orders_freight AS passed;

-- 4. Referential integrity: every fact row finds its dimension
SELECT 'orders without customer' AS check, COUNT(*) AS offenders FROM MARTS.FCT_ORDERS LEFT JOIN MARTS.DIM_CUSTOMER c USING (customer_unique_id) WHERE c.customer_unique_id IS NULL
UNION ALL SELECT 'orders without date',   COUNT(*) FROM MARTS.FCT_ORDERS f LEFT JOIN MARTS.DIM_DATE d ON d.date_key = f.purchase_date_key WHERE d.date_key IS NULL
UNION ALL SELECT 'items without product', COUNT(*) FROM MARTS.FCT_ORDER_ITEMS LEFT JOIN MARTS.DIM_PRODUCT p USING (product_id) WHERE p.product_id IS NULL
UNION ALL SELECT 'items without seller',  COUNT(*) FROM MARTS.FCT_ORDER_ITEMS LEFT JOIN MARTS.DIM_SELLER s USING (seller_id) WHERE s.seller_id IS NULL
UNION ALL SELECT 'orders with no items',  COUNT(*) FROM MARTS.FCT_ORDERS WHERE items_count IS NULL;
-- "orders with no items" is expected to be > 0 (canceled/unavailable orders have no items). Document it, do not fix it.

-- 5. Status map and the delivery rules applied to it
SELECT order_status, delivery_bucket, COUNT(*) AS orders,
       MIN(delay_days) AS min_delay, MAX(delay_days) AS max_delay
FROM MARTS.FCT_ORDERS
GROUP BY 1, 2
ORDER BY 1, 2;

-- 6. Data window: orders per month (edges are sparse -> in_analysis_window)
SELECT d.year_month, d.in_analysis_window, COUNT(*) AS orders
FROM MARTS.FCT_ORDERS f JOIN MARTS.DIM_DATE d ON d.date_key = f.purchase_date_key
GROUP BY 1, 2 ORDER BY 1;

-- 7. Headline numbers for the story (analysis window only)
WITH w AS (
  SELECT f.*
  FROM MARTS.FCT_ORDERS f JOIN MARTS.DIM_DATE d ON d.date_key = f.purchase_date_key
  WHERE d.in_analysis_window
)
SELECT
  COUNT(*)                                                         AS orders,
  SUM(gmv)                                                         AS gmv,
  SUM(gmv) / COUNT(*)                                              AS avg_order_value,
  1 - SUM(IFF(is_late, 1, 0)) / NULLIF(SUM(IFF(is_delivered, 1, 0)), 0) AS on_time_pct,
  AVG(IFF(is_delivered, delivery_days, NULL))                      AS avg_delivery_days,
  AVG(review_score)                                                AS avg_review_score,
  AVG(IFF(is_late = FALSE, review_score, NULL))                    AS avg_review_on_time,
  AVG(IFF(is_late = TRUE,  review_score, NULL))                    AS avg_review_late,
  SUM(IFF(is_low_review, 1, 0)) / NULLIF(SUM(IFF(has_review, 1, 0)), 0) AS low_review_pct,
  SUM(IFF(is_low_review AND is_late, 1, 0)) / NULLIF(SUM(IFF(is_low_review, 1, 0)), 0) AS share_of_low_reviews_that_were_late,
  SUM(freight_value) / NULLIF(SUM(gmv), 0)                         AS freight_pct_of_gmv
FROM w;

-- 8. Repeat customers (retention argument)
SELECT
  COUNT(*)                                            AS customers,
  SUM(IFF(is_repeat_customer, 1, 0))                  AS repeat_customers,
  SUM(IFF(is_repeat_customer, 1, 0)) / COUNT(*)       AS repeat_customer_pct
FROM MARTS.DIM_CUSTOMER;

-- 9. Where it happens: late share and freight share by customer state
SELECT
  f.customer_state,
  c.customer_region,
  COUNT(*)                                                                   AS orders,
  1 - SUM(IFF(f.is_late, 1, 0)) / NULLIF(SUM(IFF(f.is_delivered, 1, 0)), 0) AS on_time_pct,
  AVG(IFF(f.is_delivered, f.delivery_days, NULL))                            AS avg_delivery_days,
  AVG(f.review_score)                                                        AS avg_review_score,
  SUM(f.freight_value) / NULLIF(SUM(f.gmv), 0)                               AS freight_pct_of_gmv
FROM MARTS.FCT_ORDERS f
JOIN MARTS.DIM_CUSTOMER c USING (customer_unique_id)
JOIN MARTS.DIM_DATE d ON d.date_key = f.purchase_date_key
WHERE d.in_analysis_window
GROUP BY f.customer_state, c.customer_region
HAVING COUNT(*) >= 100
ORDER BY on_time_pct;

-- 10. Interstate vs same-state routes
SELECT is_interstate,
       COUNT(*) AS orders,
       1 - SUM(IFF(is_late, 1, 0)) / NULLIF(SUM(IFF(is_delivered, 1, 0)), 0) AS on_time_pct,
       AVG(IFF(is_delivered, delivery_days, NULL)) AS avg_delivery_days,
       AVG(review_score) AS avg_review_score
FROM MARTS.FCT_ORDERS
WHERE is_interstate IS NOT NULL
GROUP BY 1;
