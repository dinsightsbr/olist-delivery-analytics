-- =============================================================================
-- 10_raw.sql — File format, internal stage, landing tables and COPY INTO
--
-- Load path:
--   1. Run the CREATE statements below.
--   2. In Snowsight: Data > Databases > OLIST > RAW > Stages > CSV_STAGE > "+ Files"
--      and upload the 9 Olist CSVs (max 250 MB each via UI; the largest is ~60 MB).
--   3. Run the COPY INTO statements.
--
-- Every column is VARCHAR on purpose: landing keeps the file as-is, and typing
-- happens once, in STG, where it can be tested. Column order = CSV header order.
-- =============================================================================
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COMPUTE_WH;
USE SCHEMA OLIST.RAW;

CREATE OR REPLACE FILE FORMAT CSV_FF
  TYPE                         = CSV
  FIELD_DELIMITER              = ','
  SKIP_HEADER                  = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  ESCAPE_UNENCLOSED_FIELD      = NONE
  TRIM_SPACE                   = TRUE
  EMPTY_FIELD_AS_NULL          = TRUE
  NULL_IF                      = ('', 'NULL', 'null')
  ENCODING                     = 'UTF8'
  COMMENT = 'Kaggle CSV export: quoted fields may contain commas and line breaks (review comments).';

CREATE STAGE IF NOT EXISTS CSV_STAGE
  FILE_FORMAT = CSV_FF
  COMMENT = 'Internal stage for the Olist CSV files uploaded through Snowsight.';

-- ---------------------------------------------------------------- landing tables
CREATE OR REPLACE TABLE ORDERS (
  order_id                      VARCHAR,
  customer_id                   VARCHAR,
  order_status                  VARCHAR,
  order_purchase_timestamp      VARCHAR,
  order_approved_at             VARCHAR,
  order_delivered_carrier_date  VARCHAR,
  order_delivered_customer_date VARCHAR,
  order_estimated_delivery_date VARCHAR
) COMMENT = 'olist_orders_dataset.csv';

CREATE OR REPLACE TABLE ORDER_ITEMS (
  order_id            VARCHAR,
  order_item_id       VARCHAR,
  product_id          VARCHAR,
  seller_id           VARCHAR,
  shipping_limit_date VARCHAR,
  price               VARCHAR,
  freight_value       VARCHAR
) COMMENT = 'olist_order_items_dataset.csv';

CREATE OR REPLACE TABLE ORDER_PAYMENTS (
  order_id             VARCHAR,
  payment_sequential   VARCHAR,
  payment_type         VARCHAR,
  payment_installments VARCHAR,
  payment_value        VARCHAR
) COMMENT = 'olist_order_payments_dataset.csv';

CREATE OR REPLACE TABLE ORDER_REVIEWS (
  review_id               VARCHAR,
  order_id                VARCHAR,
  review_score            VARCHAR,
  review_comment_title    VARCHAR,
  review_comment_message  VARCHAR,
  review_creation_date    VARCHAR,
  review_answer_timestamp VARCHAR
) COMMENT = 'olist_order_reviews_dataset.csv';

CREATE OR REPLACE TABLE CUSTOMERS (
  customer_id              VARCHAR,
  customer_unique_id       VARCHAR,
  customer_zip_code_prefix VARCHAR,
  customer_city            VARCHAR,
  customer_state           VARCHAR
) COMMENT = 'olist_customers_dataset.csv';

CREATE OR REPLACE TABLE SELLERS (
  seller_id              VARCHAR,
  seller_zip_code_prefix VARCHAR,
  seller_city            VARCHAR,
  seller_state           VARCHAR
) COMMENT = 'olist_sellers_dataset.csv';

CREATE OR REPLACE TABLE PRODUCTS (
  product_id                 VARCHAR,
  product_category_name      VARCHAR,
  product_name_lenght        VARCHAR,   -- typo is in the source header; fixed in STG
  product_description_lenght VARCHAR,
  product_photos_qty         VARCHAR,
  product_weight_g           VARCHAR,
  product_length_cm          VARCHAR,
  product_height_cm          VARCHAR,
  product_width_cm           VARCHAR
) COMMENT = 'olist_products_dataset.csv';

CREATE OR REPLACE TABLE GEOLOCATION (
  geolocation_zip_code_prefix VARCHAR,
  geolocation_lat             VARCHAR,
  geolocation_lng             VARCHAR,
  geolocation_city            VARCHAR,
  geolocation_state           VARCHAR
) COMMENT = 'olist_geolocation_dataset.csv (~1M rows, many points per zip prefix)';

CREATE OR REPLACE TABLE PRODUCT_CATEGORY_TRANSLATION (
  product_category_name         VARCHAR,
  product_category_name_english VARCHAR
) COMMENT = 'product_category_name_translation.csv';

-- ------------------------------------------------------------------- COPY INTO
-- Run after the files are in the stage. LIST @CSV_STAGE; shows what is there.
LIST @CSV_STAGE;

COPY INTO ORDERS                       FROM @CSV_STAGE/olist_orders_dataset.csv            FILE_FORMAT = (FORMAT_NAME = CSV_FF) ON_ERROR = ABORT_STATEMENT;
COPY INTO ORDER_ITEMS                  FROM @CSV_STAGE/olist_order_items_dataset.csv       FILE_FORMAT = (FORMAT_NAME = CSV_FF) ON_ERROR = ABORT_STATEMENT;
COPY INTO ORDER_PAYMENTS               FROM @CSV_STAGE/olist_order_payments_dataset.csv    FILE_FORMAT = (FORMAT_NAME = CSV_FF) ON_ERROR = ABORT_STATEMENT;
COPY INTO ORDER_REVIEWS                FROM @CSV_STAGE/olist_order_reviews_dataset.csv     FILE_FORMAT = (FORMAT_NAME = CSV_FF) ON_ERROR = ABORT_STATEMENT;
COPY INTO CUSTOMERS                    FROM @CSV_STAGE/olist_customers_dataset.csv         FILE_FORMAT = (FORMAT_NAME = CSV_FF) ON_ERROR = ABORT_STATEMENT;
COPY INTO SELLERS                      FROM @CSV_STAGE/olist_sellers_dataset.csv           FILE_FORMAT = (FORMAT_NAME = CSV_FF) ON_ERROR = ABORT_STATEMENT;
COPY INTO PRODUCTS                     FROM @CSV_STAGE/olist_products_dataset.csv          FILE_FORMAT = (FORMAT_NAME = CSV_FF) ON_ERROR = ABORT_STATEMENT;
COPY INTO GEOLOCATION                  FROM @CSV_STAGE/olist_geolocation_dataset.csv       FILE_FORMAT = (FORMAT_NAME = CSV_FF) ON_ERROR = ABORT_STATEMENT;
COPY INTO PRODUCT_CATEGORY_TRANSLATION FROM @CSV_STAGE/product_category_name_translation.csv FILE_FORMAT = (FORMAT_NAME = CSV_FF) ON_ERROR = ABORT_STATEMENT;

-- Row counts after load. Reference values from the Kaggle page (approximate
-- where marked): orders 99,441 · items 112,650 · payments ~103.9k ·
-- reviews ~99.2k · customers 99,441 · sellers ~3,095 · products ~32,951 ·
-- geolocation ~1,000k · translations 71.
SELECT 'ORDERS' AS tbl, COUNT(*) AS rows_loaded FROM ORDERS
UNION ALL SELECT 'ORDER_ITEMS',                  COUNT(*) FROM ORDER_ITEMS
UNION ALL SELECT 'ORDER_PAYMENTS',               COUNT(*) FROM ORDER_PAYMENTS
UNION ALL SELECT 'ORDER_REVIEWS',                COUNT(*) FROM ORDER_REVIEWS
UNION ALL SELECT 'CUSTOMERS',                    COUNT(*) FROM CUSTOMERS
UNION ALL SELECT 'SELLERS',                      COUNT(*) FROM SELLERS
UNION ALL SELECT 'PRODUCTS',                     COUNT(*) FROM PRODUCTS
UNION ALL SELECT 'GEOLOCATION',                  COUNT(*) FROM GEOLOCATION
UNION ALL SELECT 'PRODUCT_CATEGORY_TRANSLATION', COUNT(*) FROM PRODUCT_CATEGORY_TRANSLATION
ORDER BY 1;
