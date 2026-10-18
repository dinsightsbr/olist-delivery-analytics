-- =============================================================================
-- 50_cortex.sql — Review-comment themes: Cortex (production) / rules (trial)
--
-- Sizes the "other 72%" of 1-2 star reviews that did not come from late
-- orders, using the Portuguese review comments.
--
-- RESULT ON 16/10/2026: both SNOWFLAKE.CORTEX.CLASSIFY_TEXT and AI_CLASSIFY
-- return "AI function ... is not available for trial accounts". Section B
-- below is the rule-based fallback that was actually run; it is transparent
-- and explainable, which is a fine answer when asked ("in production I
-- would swap the CASE for AI_CLASSIFY and keep the rules as a regression test").
-- Section A is kept as the production version.
-- =============================================================================
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COMPUTE_WH;
USE SCHEMA OLIST.MARTS;

-- 1. Sample run (~500 comments). Themes are deliberately few and distinct.
-- Sample first (random 500), classify after: keeps the LLM calls to 500 rows.
CREATE OR REPLACE TABLE REVIEW_THEMES_SAMPLE AS
WITH s AS (
  SELECT f.order_id, f.review_score, f.is_late, f.delivery_bucket, r.review_comment
  FROM FCT_ORDERS f
  JOIN OLIST.STG.STG_REVIEWS r ON r.order_id = f.order_id
  WHERE f.is_low_review AND r.review_comment IS NOT NULL
  ORDER BY RANDOM()
  LIMIT 500
)
SELECT order_id, review_score, is_late, delivery_bucket, review_comment,
  SNOWFLAKE.CORTEX.CLASSIFY_TEXT(
    review_comment,
    ['Late delivery', 'Product not received', 'Wrong or incomplete order',
     'Product quality or defect', 'Customer service or refund', 'Other']
  ):label::STRING AS theme
FROM s;

SELECT theme,
  COUNT(*)                                            AS reviews,
  ROUND(COUNT(*) / SUM(COUNT(*)) OVER () * 100, 1)    AS pct_of_sample,
  SUM(IFF(is_late = TRUE, 1, 0))                      AS from_late_orders,
  SUM(IFF(is_late = FALSE, 1, 0))                     AS from_on_time_orders,
  SUM(IFF(is_late IS NULL, 1, 0))                     AS from_undelivered_orders
FROM REVIEW_THEMES_SAMPLE
GROUP BY 1
ORDER BY 2 DESC;

-- 2. Full run on all low reviews with a comment (~10k rows). Only after step 1
--    looked right. Remove the LIMIT and materialize as REVIEW_THEMES.

-- =============================================================================
-- B. Rule-based fallback (what ran on the trial account)
-- Priority order matters: a comment that says "não recebi" and "atrasado" is
-- about not receiving; "chegou quebrado" and "atendimento" is about a defect.
-- =============================================================================
CREATE OR REPLACE TABLE REVIEW_THEMES_RULES
  COMMENT = 'Theme per low-review (1-2 stars) order with a comment, assigned by Portuguese keyword rules. Priority: not received > late > wrong/incomplete > defect > service > other.'
AS
WITH s AS (
  SELECT f.order_id, f.review_score, f.is_late, f.delivery_bucket, r.review_comment, LOWER(r.review_comment) AS c
  FROM FCT_ORDERS f
  JOIN OLIST.STG.STG_REVIEWS r ON r.order_id = f.order_id
  WHERE f.is_low_review AND r.review_comment IS NOT NULL
)
SELECT order_id, review_score, is_late, delivery_bucket, review_comment,
  CASE
    WHEN REGEXP_COUNT(c, 'n[aã]o (recebi|receber|chegou|foi entregue|entregaram|entregue|entregou)|ainda (estou |to |tô )?aguard|at[eé] (agora|hoje|o momento) (n[aã]o|nada)|sem receber|n[aã]o veio|cad[eê] ') > 0 THEN 'Product not received'
    WHEN REGEXP_COUNT(c, 'atras|demor|fora do prazo|prazo .{0,25}(n[aã]o|nao) (foi )?cumprid|al[eé]m do prazo|depois do prazo|passou do prazo|muito tempo') > 0 THEN 'Late delivery'
    WHEN REGEXP_COUNT(c, 'errad|diferente|faltando|faltou|incompleto|s[oó] (recebi |veio |chegou )?(um|uma|1 )|apenas (um|uma|1 )|outro produto|n[aã]o (era|[eé]) o (que|produto)|trocad|comprei (dois|duas|2).{0,40}(um|uma|1)') > 0 THEN 'Wrong or incomplete order'
    WHEN REGEXP_COUNT(c, 'defeito|quebrad|danific|estrag|n[aã]o funciona|p[eé]ssim[ao] qualidade|qualidade (ruim|p[eé]ssima|baixa|inferior)|rasgad|amassad|falsificad|n[aã]o (presta|serve)|fr[aá]gil|parou de funcionar|veio (quebrado|com defeito|danificado)|avariad|vencid') > 0 THEN 'Product quality or defect'
    WHEN REGEXP_COUNT(c, 'atendimento|reembols|estorn|devolu[cç]|troca|cancel|n[aã]o (respond|retorn)|sem resposta|\\bsac\\b|contato') > 0 THEN 'Customer service or refund'
    ELSE 'Other'
  END AS theme
FROM s;

SELECT theme,
  COUNT(*)                                            AS reviews,
  ROUND(COUNT(*) / SUM(COUNT(*)) OVER () * 100, 1)    AS pct_of_low_reviews_with_comment,
  SUM(IFF(is_late = TRUE, 1, 0))                      AS from_late_orders,
  SUM(IFF(is_late = FALSE, 1, 0))                     AS from_on_time_orders,
  SUM(IFF(is_late IS NULL, 1, 0))                     AS from_undelivered_orders,
  ROUND(AVG(review_score), 2)                         AS avg_score
FROM REVIEW_THEMES_RULES
GROUP BY 1
ORDER BY 2 DESC;

-- Spot check: read a few comments per theme before trusting the rules.
SELECT theme, review_score, is_late, LEFT(review_comment, 120) AS comment
FROM REVIEW_THEMES_RULES
QUALIFY ROW_NUMBER() OVER (PARTITION BY theme ORDER BY RANDOM()) <= 3
ORDER BY theme;

-- 3. Power BI: import REVIEW_THEMES_RULES and relate order_id (1:1) to FCT_ORDERS,
--    or add theme to FCT_ORDERS via LEFT JOIN in 30_marts.sql. Visual for
--    page 2: low reviews by theme, split on time vs late.
