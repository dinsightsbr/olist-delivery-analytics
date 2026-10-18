-- =============================================================================
-- 00_setup.sql — Database, schemas, warehouse and read-only role
-- Run as ACCOUNTADMIN in a Snowsight worksheet. Idempotent.
-- =============================================================================
USE ROLE ACCOUNTADMIN;

-- Trial accounts ship with COMPUTE_WH; keep it tiny and let it sleep fast.
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH
  WAREHOUSE_SIZE = XSMALL
  AUTO_SUSPEND   = 60
  AUTO_RESUME    = TRUE;
ALTER WAREHOUSE COMPUTE_WH SET WAREHOUSE_SIZE = XSMALL AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;

CREATE DATABASE IF NOT EXISTS OLIST
  COMMENT = 'Olist Brazilian e-commerce public dataset (Kaggle). Case study: delivery experience vs customer satisfaction.';

CREATE SCHEMA IF NOT EXISTS OLIST.RAW
  COMMENT = 'Landing zone. One table per CSV, all columns VARCHAR, no transformation.';
CREATE SCHEMA IF NOT EXISTS OLIST.STG
  COMMENT = 'Staging views: typed, renamed, deduplicated, one row per business key.';
CREATE SCHEMA IF NOT EXISTS OLIST.MARTS
  COMMENT = 'Star schema for BI: dim_* / fct_* tables plus the semantic view. Only layer exposed to Power BI.';

-- Read-only role for BI tools: the only thing Power BI should ever use.
CREATE ROLE IF NOT EXISTS BI_READER
  COMMENT = 'Read-only access to OLIST.MARTS for BI consumers (Power BI).';
GRANT USAGE ON WAREHOUSE COMPUTE_WH            TO ROLE BI_READER;
GRANT USAGE ON DATABASE  OLIST                 TO ROLE BI_READER;
GRANT USAGE ON SCHEMA    OLIST.MARTS           TO ROLE BI_READER;
GRANT SELECT ON ALL    TABLES IN SCHEMA OLIST.MARTS TO ROLE BI_READER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA OLIST.MARTS TO ROLE BI_READER;
GRANT SELECT ON ALL    VIEWS  IN SCHEMA OLIST.MARTS TO ROLE BI_READER;
GRANT SELECT ON FUTURE VIEWS  IN SCHEMA OLIST.MARTS TO ROLE BI_READER;

-- Give the role to the human user too. Quote the name if it contains dots or
-- lowercase letters (IDENTIFIER($var) fails on dotted names).
-- SELECT CURRENT_USER();  -- to find it
GRANT ROLE BI_READER TO USER "<your_user_name>";

-- Service user for Power BI with key pair auth. The human account signs in
-- with Google (no password), so Power BI uses a SERVICE user instead:
--   openssl genrsa -out tmp.pem 2048
--   openssl pkcs8 -topk8 -inform PEM -in tmp.pem -out pbi_service_rsa_key.p8 -nocrypt
--   openssl rsa -in pbi_service_rsa_key.p8 -pubout -out pbi_service_rsa_key.pub
-- Paste the .pub body (no header/footer lines) below. The .p8 private key stays
-- on the local machine (~/.snowflake/) and is never committed.
CREATE USER IF NOT EXISTS PBI_SERVICE
  TYPE = SERVICE
  DEFAULT_ROLE = BI_READER
  DEFAULT_WAREHOUSE = COMPUTE_WH
  COMMENT = 'Power BI read-only service user (key pair auth)';
ALTER USER PBI_SERVICE SET RSA_PUBLIC_KEY = '<public_key_body>';
GRANT ROLE BI_READER TO USER PBI_SERVICE;
DESC USER PBI_SERVICE;  -- RSA_PUBLIC_KEY_FP must be filled

USE WAREHOUSE COMPUTE_WH;
USE DATABASE OLIST;

SHOW SCHEMAS IN DATABASE OLIST;
