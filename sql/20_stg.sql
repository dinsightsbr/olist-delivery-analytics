-- =============================================================================
-- 20_stg.sql — Staging views: typed, renamed, deduplicated
--
-- Rules applied here (and nowhere else):
--   * one row per business key (orders, reviews per order, payments per order)
--   * TRY_* casts so a bad value becomes NULL instead of failing the layer
--   * snake_case names in English; source typos fixed (lenght -> length)
--   * zip prefixes kept as text, left-padded to 5 (leading zeros matter)
-- =============================================================================
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COMPUTE_WH;
USE SCHEMA OLIST.STG;

-- Reference: Brazilian states and regions (used by dim_customer and dim_seller).
CREATE OR REPLACE TABLE REF_STATE (state_code VARCHAR(2), state_name VARCHAR, region VARCHAR) AS
SELECT * FROM VALUES
  ('AC','Acre','Norte'),            ('AP','Amapá','Norte'),             ('AM','Amazonas','Norte'),
  ('PA','Pará','Norte'),            ('RO','Rondônia','Norte'),          ('RR','Roraima','Norte'),
  ('TO','Tocantins','Norte'),
  ('AL','Alagoas','Nordeste'),      ('BA','Bahia','Nordeste'),          ('CE','Ceará','Nordeste'),
  ('MA','Maranhão','Nordeste'),     ('PB','Paraíba','Nordeste'),        ('PE','Pernambuco','Nordeste'),
  ('PI','Piauí','Nordeste'),        ('RN','Rio Grande do Norte','Nordeste'), ('SE','Sergipe','Nordeste'),
  ('DF','Distrito Federal','Centro-Oeste'), ('GO','Goiás','Centro-Oeste'),
  ('MT','Mato Grosso','Centro-Oeste'),      ('MS','Mato Grosso do Sul','Centro-Oeste'),
  ('ES','Espírito Santo','Sudeste'), ('MG','Minas Gerais','Sudeste'),   ('RJ','Rio de Janeiro','Sudeste'),
  ('SP','São Paulo','Sudeste'),
  ('PR','Paraná','Sul'),            ('RS','Rio Grande do Sul','Sul'),   ('SC','Santa Catarina','Sul');

-- ------------------------------------------------------------------ stg_orders
CREATE OR REPLACE VIEW STG_ORDERS
  COMMENT = 'One row per order. Timestamps typed; status normalized to lowercase.'
AS
SELECT
  order_id,
  customer_id,
  LOWER(TRIM(order_status))                            AS order_status,
  TRY_TO_TIMESTAMP_NTZ(order_purchase_timestamp)       AS purchased_at,
  TRY_TO_TIMESTAMP_NTZ(order_approved_at)              AS approved_at,
  TRY_TO_TIMESTAMP_NTZ(order_delivered_carrier_date)   AS delivered_to_carrier_at,
  TRY_TO_TIMESTAMP_NTZ(order_delivered_customer_date)  AS delivered_to_customer_at,
  TRY_TO_TIMESTAMP_NTZ(order_estimated_delivery_date)  AS estimated_delivery_at
FROM OLIST.RAW.ORDERS
QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY order_purchase_timestamp) = 1;

-- ------------------------------------------------------------- stg_order_items
CREATE OR REPLACE VIEW STG_ORDER_ITEMS
  COMMENT = 'One row per order item (order_id + order_item_id).'
AS
SELECT
  order_id,
  TRY_TO_NUMBER(order_item_id)                  AS order_item_id,
  product_id,
  seller_id,
  TRY_TO_TIMESTAMP_NTZ(shipping_limit_date)     AS shipping_limit_at,
  TRY_TO_NUMBER(price, 12, 2)                   AS price,
  TRY_TO_NUMBER(freight_value, 12, 2)           AS freight_value
FROM OLIST.RAW.ORDER_ITEMS
QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id, order_item_id ORDER BY price) = 1;

-- ---------------------------------------------------------------- stg_payments
-- Source has one row per payment leg (vouchers split payments). Aggregated to
-- order grain; "primary" type = the leg with the largest value.
CREATE OR REPLACE VIEW STG_PAYMENTS
  COMMENT = 'One row per order: total paid, number of legs, max installments, primary payment type.'
AS
SELECT
  order_id,
  SUM(TRY_TO_NUMBER(payment_value, 12, 2))                           AS payment_value,
  COUNT(*)                                                           AS payment_legs,
  MAX(TRY_TO_NUMBER(payment_installments))                           AS max_installments,
  MAX_BY(LOWER(TRIM(payment_type)), TRY_TO_NUMBER(payment_value, 12, 2)) AS primary_payment_type
FROM OLIST.RAW.ORDER_PAYMENTS
GROUP BY order_id;

-- ----------------------------------------------------------------- stg_reviews
-- Source has duplicated review_id values and a few orders with >1 review.
-- Keep the most recently answered review per order.
CREATE OR REPLACE VIEW STG_REVIEWS
  COMMENT = 'One row per order: latest review. Comment text kept for optional Cortex classification.'
AS
SELECT
  order_id,
  review_id,
  TRY_TO_NUMBER(review_score)                      AS review_score,
  NULLIF(TRIM(review_comment_title), '')           AS review_title,
  NULLIF(TRIM(review_comment_message), '')         AS review_comment,
  TRY_TO_TIMESTAMP_NTZ(review_creation_date)       AS review_created_at,
  TRY_TO_TIMESTAMP_NTZ(review_answer_timestamp)    AS review_answered_at,
  (NULLIF(TRIM(review_comment_message), '') IS NOT NULL) AS has_comment
FROM OLIST.RAW.ORDER_REVIEWS
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY order_id
  ORDER BY TRY_TO_TIMESTAMP_NTZ(review_answer_timestamp) DESC NULLS LAST,
           TRY_TO_TIMESTAMP_NTZ(review_creation_date)    DESC NULLS LAST
) = 1;

-- --------------------------------------------------------------- stg_customers
-- customer_id is per order; customer_unique_id is the actual person.
CREATE OR REPLACE VIEW STG_CUSTOMERS
  COMMENT = 'One row per customer_id (order-level key) with the real customer key customer_unique_id.'
AS
SELECT
  customer_id,
  customer_unique_id,
  LPAD(TRIM(customer_zip_code_prefix), 5, '0')  AS customer_zip_prefix,
  INITCAP(TRIM(customer_city))                  AS customer_city,
  UPPER(TRIM(customer_state))                   AS customer_state
FROM OLIST.RAW.CUSTOMERS
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY customer_unique_id) = 1;

-- ----------------------------------------------------------------- stg_sellers
CREATE OR REPLACE VIEW STG_SELLERS
  COMMENT = 'One row per seller.'
AS
SELECT
  seller_id,
  LPAD(TRIM(seller_zip_code_prefix), 5, '0')  AS seller_zip_prefix,
  INITCAP(TRIM(seller_city))                  AS seller_city,
  UPPER(TRIM(seller_state))                   AS seller_state
FROM OLIST.RAW.SELLERS
QUALIFY ROW_NUMBER() OVER (PARTITION BY seller_id ORDER BY seller_state) = 1;

-- ---------------------------------------------------------------- stg_products
CREATE OR REPLACE VIEW STG_PRODUCTS
  COMMENT = 'One row per product with English category (falls back to the Portuguese name when no translation exists).'
AS
SELECT
  p.product_id,
  p.product_category_name                                        AS category_pt,
  COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category_en,
  TRY_TO_NUMBER(p.product_name_lenght)                           AS name_length,
  TRY_TO_NUMBER(p.product_description_lenght)                    AS description_length,
  TRY_TO_NUMBER(p.product_photos_qty)                            AS photos_qty,
  TRY_TO_NUMBER(p.product_weight_g)                              AS weight_g,
  TRY_TO_NUMBER(p.product_length_cm)                             AS length_cm,
  TRY_TO_NUMBER(p.product_height_cm)                             AS height_cm,
  TRY_TO_NUMBER(p.product_width_cm)                              AS width_cm,
  TRY_TO_NUMBER(p.product_length_cm) * TRY_TO_NUMBER(p.product_height_cm) * TRY_TO_NUMBER(p.product_width_cm) AS volume_cm3
FROM OLIST.RAW.PRODUCTS p
LEFT JOIN OLIST.RAW.PRODUCT_CATEGORY_TRANSLATION t
  ON t.product_category_name = p.product_category_name
QUALIFY ROW_NUMBER() OVER (PARTITION BY p.product_id ORDER BY p.product_category_name) = 1;

-- ------------------------------------------------------------- stg_geolocation
-- ~1M points; many per zip prefix and some outside Brazil. Average per prefix
-- inside a Brazil bounding box.
CREATE OR REPLACE VIEW STG_GEOLOCATION
  COMMENT = 'One row per zip prefix: average lat/lng of points inside the Brazil bounding box.'
AS
SELECT
  LPAD(TRIM(geolocation_zip_code_prefix), 5, '0') AS zip_prefix,
  AVG(TRY_TO_DOUBLE(geolocation_lat))             AS lat,
  AVG(TRY_TO_DOUBLE(geolocation_lng))             AS lng,
  COUNT(*)                                        AS points
FROM OLIST.RAW.GEOLOCATION
WHERE TRY_TO_DOUBLE(geolocation_lat) BETWEEN -34.0 AND  5.5
  AND TRY_TO_DOUBLE(geolocation_lng) BETWEEN -74.0 AND -34.0
GROUP BY 1;

SHOW VIEWS IN SCHEMA OLIST.STG;
