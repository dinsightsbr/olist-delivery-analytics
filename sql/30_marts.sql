-- =============================================================================
-- 30_marts.sql — Star schema for Power BI
--
--   DIM_DATE ─┐
--   DIM_CUSTOMER ─┼─< FCT_ORDERS (grain: order)
--   DIM_SELLER ───┼─< FCT_ORDER_ITEMS (grain: order item)
--   DIM_PRODUCT ──┘
--
-- Materialized as tables (CREATE OR REPLACE ... AS) so Power BI imports a
-- stable, pre-joined layer. Business rules live here once:
--   * delivered   = status 'delivered' with a customer delivery timestamp
--   * late        = delivered after the estimated date (calendar days)
--   * delay_days  = delivered date - estimated date (positive = late)
-- =============================================================================
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COMPUTE_WH;
USE SCHEMA OLIST.MARTS;

-- ------------------------------------------------------------------- dim_date
CREATE OR REPLACE TABLE DIM_DATE
  COMMENT = 'Calendar 2016-01-01..2018-12-31. in_analysis_window flags Jan-2017..Aug-2018 (edges of the dataset are sparse).'
AS
WITH days AS (
  SELECT DATEADD('day', ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1, '2016-01-01'::DATE) AS date_day
  FROM TABLE(GENERATOR(ROWCOUNT => 1096))
)
SELECT
  TO_NUMBER(TO_CHAR(date_day, 'YYYYMMDD'))        AS date_key,
  date_day                                         AS date,
  YEAR(date_day)                                   AS year,
  QUARTER(date_day)                                AS quarter,
  'Q' || QUARTER(date_day)                         AS quarter_label,
  MONTH(date_day)                                  AS month,
  MONTHNAME(date_day)                              AS month_short,
  TO_CHAR(date_day, 'YYYY-MM')                     AS year_month,
  DATE_TRUNC('month', date_day)::DATE              AS month_start,
  DAYOFWEEKISO(date_day)                           AS day_of_week_iso,
  DAYNAME(date_day)                                AS day_short,
  DAYOFWEEKISO(date_day) >= 6                      AS is_weekend,
  WEEKISO(date_day)                                AS iso_week,
  date_day BETWEEN '2017-01-01' AND '2018-08-31'   AS in_analysis_window
FROM days;

-- --------------------------------------------------------------- dim_customer
-- Grain: customer_unique_id (the person). Address taken from the latest order.
CREATE OR REPLACE TABLE DIM_CUSTOMER
  COMMENT = 'One row per customer_unique_id. orders_count / is_repeat_customer support the retention story.'
AS
WITH ranked AS (
  SELECT
    c.customer_unique_id,
    c.customer_zip_prefix,
    c.customer_city,
    c.customer_state,
    ROW_NUMBER() OVER (PARTITION BY c.customer_unique_id ORDER BY o.purchased_at DESC NULLS LAST) AS rn,
    COUNT(o.order_id)  OVER (PARTITION BY c.customer_unique_id) AS orders_count,
    MIN(o.purchased_at) OVER (PARTITION BY c.customer_unique_id) AS first_purchase_at
  FROM OLIST.STG.STG_CUSTOMERS c
  LEFT JOIN OLIST.STG.STG_ORDERS o ON o.customer_id = c.customer_id
)
SELECT
  r.customer_unique_id,
  r.customer_zip_prefix,
  r.customer_city,
  r.customer_state,
  s.state_name                      AS customer_state_name,
  s.region                          AS customer_region,
  g.lat                             AS customer_lat,
  g.lng                             AS customer_lng,
  r.orders_count,
  r.orders_count > 1                AS is_repeat_customer,
  r.first_purchase_at::DATE         AS first_purchase_date
FROM ranked r
LEFT JOIN OLIST.STG.REF_STATE       s ON s.state_code = r.customer_state
LEFT JOIN OLIST.STG.STG_GEOLOCATION g ON g.zip_prefix = r.customer_zip_prefix
WHERE r.rn = 1;

-- ----------------------------------------------------------------- dim_seller
CREATE OR REPLACE TABLE DIM_SELLER
  COMMENT = 'One row per seller with state, region and approximate location.'
AS
SELECT
  s.seller_id,
  s.seller_zip_prefix,
  s.seller_city,
  s.seller_state,
  r.state_name   AS seller_state_name,
  r.region       AS seller_region,
  g.lat          AS seller_lat,
  g.lng          AS seller_lng
FROM OLIST.STG.STG_SELLERS s
LEFT JOIN OLIST.STG.REF_STATE       r ON r.state_code = s.seller_state
LEFT JOIN OLIST.STG.STG_GEOLOCATION g ON g.zip_prefix = s.seller_zip_prefix;

-- ---------------------------------------------------------------- dim_product
CREATE OR REPLACE TABLE DIM_PRODUCT
  COMMENT = 'One row per product. category_en is the display category.'
AS
SELECT
  product_id,
  category_pt,
  category_en,
  INITCAP(REPLACE(category_en, '_', ' ')) AS category_label,
  name_length,
  description_length,
  photos_qty,
  weight_g,
  volume_cm3,
  CASE
    WHEN weight_g IS NULL      THEN 'Unknown'
    WHEN weight_g <  1000      THEN '1. < 1 kg'
    WHEN weight_g <  5000      THEN '2. 1-5 kg'
    WHEN weight_g < 15000      THEN '3. 5-15 kg'
    ELSE                            '4. 15 kg+'
  END AS weight_band
FROM OLIST.STG.STG_PRODUCTS;

-- ----------------------------------------------------------------- fct_orders
CREATE OR REPLACE TABLE FCT_ORDERS
  COMMENT = 'Grain: one row per order. Delivery, review and payment facts; GMV and freight aggregated from items.'
AS
WITH items AS (
  SELECT
    order_id,
    COUNT(*)                        AS items_count,
    COUNT(DISTINCT seller_id)       AS sellers_count,
    SUM(price)                      AS gmv,
    SUM(freight_value)              AS freight_value,
    MAX_BY(seller_id, price)        AS primary_seller_id
  FROM OLIST.STG.STG_ORDER_ITEMS
  GROUP BY order_id
),
base AS (
  SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    i.primary_seller_id,
    o.order_status,
    o.purchased_at,
    o.approved_at,
    o.delivered_to_carrier_at,
    o.delivered_to_customer_at,
    o.estimated_delivery_at,
    (o.order_status = 'delivered' AND o.delivered_to_customer_at IS NOT NULL)        AS is_delivered,
    DATEDIFF('day', o.purchased_at::DATE, o.delivered_to_customer_at::DATE)           AS delivery_days,
    DATEDIFF('day', o.purchased_at::DATE, o.estimated_delivery_at::DATE)              AS estimated_days,
    DATEDIFF('day', o.estimated_delivery_at::DATE, o.delivered_to_customer_at::DATE)  AS delay_days,
    r.review_id,
    r.review_score,
    r.has_comment,
    r.review_created_at,
    p.payment_value,
    p.payment_legs,
    p.max_installments,
    p.primary_payment_type,
    i.items_count,
    i.sellers_count,
    COALESCE(i.gmv, 0)            AS gmv,
    COALESCE(i.freight_value, 0)  AS freight_value,
    c.customer_state,
    s.seller_state                AS primary_seller_state
  FROM OLIST.STG.STG_ORDERS   o
  LEFT JOIN OLIST.STG.STG_CUSTOMERS c ON c.customer_id = o.customer_id
  LEFT JOIN items                   i ON i.order_id    = o.order_id
  LEFT JOIN OLIST.STG.STG_REVIEWS   r ON r.order_id    = o.order_id
  LEFT JOIN OLIST.STG.STG_PAYMENTS  p ON p.order_id    = o.order_id
  LEFT JOIN OLIST.STG.STG_SELLERS   s ON s.seller_id   = i.primary_seller_id
)
SELECT
  order_id,
  customer_id,
  customer_unique_id,
  primary_seller_id,
  order_status,
  purchased_at,
  TO_NUMBER(TO_CHAR(purchased_at, 'YYYYMMDD'))            AS purchase_date_key,
  approved_at,
  delivered_to_carrier_at,
  delivered_to_customer_at,
  TO_NUMBER(TO_CHAR(delivered_to_customer_at, 'YYYYMMDD')) AS delivered_date_key,
  estimated_delivery_at,
  TO_NUMBER(TO_CHAR(estimated_delivery_at, 'YYYYMMDD'))   AS estimated_delivery_date_key,
  is_delivered,
  delivery_days,
  estimated_days,
  delay_days,
  IFF(is_delivered, delay_days > 0, NULL)                  AS is_late,
  CASE
    WHEN order_status IN ('canceled', 'unavailable')  THEN 'Canceled / unavailable'
    WHEN is_delivered AND delay_days <= 0             THEN 'On time'
    WHEN is_delivered AND delay_days BETWEEN 1 AND 7  THEN 'Late 1-7 days'
    WHEN is_delivered AND delay_days > 7              THEN 'Late 8+ days'
    ELSE                                                   'In progress'
  END                                                      AS delivery_bucket,
  CASE
    WHEN order_status IN ('canceled', 'unavailable')  THEN 5
    WHEN is_delivered AND delay_days <= 0             THEN 1
    WHEN is_delivered AND delay_days BETWEEN 1 AND 7  THEN 2
    WHEN is_delivered AND delay_days > 7              THEN 3
    ELSE                                                   4
  END                                                      AS delivery_bucket_sort,
  review_id IS NOT NULL                                    AS has_review,
  review_score,
  IFF(review_score IS NULL, NULL, review_score <= 2)       AS is_low_review,
  has_comment,
  review_created_at,
  payment_value,
  payment_legs,
  max_installments,
  primary_payment_type,
  items_count,
  sellers_count,
  gmv,
  freight_value,
  freight_value / NULLIF(gmv, 0)                           AS freight_pct,
  customer_state,
  primary_seller_state,
  IFF(customer_state IS NULL OR primary_seller_state IS NULL, NULL,
      customer_state <> primary_seller_state)              AS is_interstate
FROM base;

-- ------------------------------------------------------------ fct_order_items
-- Order-level attributes (lateness, review) are repeated on each item so the
-- category and seller pages can slice them. Averages of review_score at item
-- grain are item-weighted by design; order-level KPIs come from FCT_ORDERS.
CREATE OR REPLACE TABLE FCT_ORDER_ITEMS
  COMMENT = 'Grain: one row per order item. Price and freight at item grain; delivery/review context copied from the order.'
AS
SELECT
  oi.order_id,
  oi.order_item_id,
  oi.product_id,
  oi.seller_id,
  f.customer_unique_id,
  f.purchase_date_key,
  f.order_status,
  f.is_delivered,
  f.is_late,
  f.delay_days,
  f.delivery_bucket,
  f.delivery_bucket_sort,
  f.review_score,
  oi.price,
  oi.freight_value,
  oi.freight_value / NULLIF(oi.price, 0)   AS freight_pct,
  oi.shipping_limit_at,
  s.seller_state,
  f.customer_state,
  IFF(f.customer_state IS NULL OR s.seller_state IS NULL, NULL,
      f.customer_state <> s.seller_state)  AS is_interstate
FROM OLIST.STG.STG_ORDER_ITEMS oi
JOIN FCT_ORDERS f               ON f.order_id  = oi.order_id
LEFT JOIN OLIST.STG.STG_SELLERS s ON s.seller_id = oi.seller_id;

-- ---------------------------------------------------------- fct_seller_monthly
-- Grain: one row per primary seller and purchase month. Feeds the seller page.
create or replace table fct_seller_monthly
  comment = 'Grain: one row per primary seller and purchase month. Orders, delivered, late, late rate, review and GMV.'
as
select
  f.primary_seller_id as seller_id,
  d.year_month,
  count(1) as orders,
  sum(iff(f.is_delivered, 1, 0)) as delivered_orders,
  sum(iff(f.is_late, 1, 0)) as late_orders,
  sum(iff(f.is_late, 1, 0)) / nullif(sum(iff(f.is_delivered, 1, 0)), 0) as late_rate,
  avg(f.review_score) as avg_review_score,
  sum(f.gmv) as gmv
from fct_orders f
join dim_date d on d.date_key = f.purchase_date_key
where f.primary_seller_id is not null
group by 1, 2

SHOW TABLES IN SCHEMA OLIST.MARTS;
