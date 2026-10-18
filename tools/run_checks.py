"""
run_checks.py - data-quality and reconciliation checks against OLIST.MARTS, for CI.

Connection comes from environment variables (GitHub secrets / variables):
  SNOWFLAKE_ACCOUNT       e.g. orgname-accountname
  SNOWFLAKE_USER          service user with key-pair auth and the BI_READER role
  SNOWFLAKE_PRIVATE_KEY   PEM contents of the private key (PKCS#8, unencrypted)
  SNOWFLAKE_WAREHOUSE / SNOWFLAKE_ROLE   optional (COMPUTE_WH / BI_READER)

Exit code 1 when any check fails. Mirrors sql/90_checks.sql for the MARTS layer.
"""
import os
import sys
import tempfile

import snowflake.connector

CHECKS = [
    ("fct_orders unique by order_id",
     "SELECT COUNT(*) = COUNT(DISTINCT order_id) FROM OLIST.MARTS.FCT_ORDERS"),
    ("fct_order_items unique by order_id + item",
     "SELECT COUNT(*) = COUNT(DISTINCT order_id || '-' || order_item_id) FROM OLIST.MARTS.FCT_ORDER_ITEMS"),
    ("dim_customer unique by customer_unique_id",
     "SELECT COUNT(*) = COUNT(DISTINCT customer_unique_id) FROM OLIST.MARTS.DIM_CUSTOMER"),
    ("GMV reconciles between the two facts",
     "SELECT (SELECT SUM(gmv) FROM OLIST.MARTS.FCT_ORDERS) = (SELECT SUM(price) FROM OLIST.MARTS.FCT_ORDER_ITEMS)"),
    ("every order finds its customer",
     "SELECT COUNT(*) = 0 FROM OLIST.MARTS.FCT_ORDERS f LEFT JOIN OLIST.MARTS.DIM_CUSTOMER c "
     "ON c.customer_unique_id = f.customer_unique_id WHERE c.customer_unique_id IS NULL"),
    ("every order finds its date",
     "SELECT COUNT(*) = 0 FROM OLIST.MARTS.FCT_ORDERS f LEFT JOIN OLIST.MARTS.DIM_DATE d "
     "ON d.date_key = f.purchase_date_key WHERE d.date_key IS NULL"),
    ("every item finds its product and seller",
     "SELECT COUNT(*) = 0 FROM OLIST.MARTS.FCT_ORDER_ITEMS i "
     "LEFT JOIN OLIST.MARTS.DIM_PRODUCT p ON p.product_id = i.product_id "
     "LEFT JOIN OLIST.MARTS.DIM_SELLER s ON s.seller_id = i.seller_id "
     "WHERE p.product_id IS NULL OR s.seller_id IS NULL"),
    ("late orders are a subset of delivered orders",
     "SELECT COUNT(*) = 0 FROM OLIST.MARTS.FCT_ORDERS WHERE is_late AND NOT is_delivered"),
    ("on-time % in the analysis window is between 90% and 96%",
     "SELECT 1 - SUM(IFF(is_late, 1, 0)) / NULLIF(SUM(IFF(is_delivered, 1, 0)), 0) BETWEEN 0.90 AND 0.96 "
     "FROM OLIST.MARTS.FCT_ORDERS f JOIN OLIST.MARTS.DIM_DATE d ON d.date_key = f.purchase_date_key "
     "WHERE d.in_analysis_window"),
    ("semantic view answers the region query",
     "SELECT COUNT(*) >= 5 FROM SEMANTIC_VIEW(OLIST.MARTS.SV_ORDERS "
     "DIMENSIONS customers.customer_region METRICS orders.order_count)"),
]


def main() -> int:
    missing = [k for k in ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PRIVATE_KEY") if not os.environ.get(k)]
    if missing:
        print(f"::error::missing environment variables: {', '.join(missing)}")
        return 1
    with tempfile.NamedTemporaryFile("w", suffix=".p8", delete=False) as f:
        f.write(os.environ["SNOWFLAKE_PRIVATE_KEY"].replace("\\n", "\n"))
        key_path = f.name
    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key_file=key_path,
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        role=os.environ.get("SNOWFLAKE_ROLE", "BI_READER"),
        database="OLIST",
        schema="MARTS",
    )
    failed = 0
    try:
        cur = conn.cursor()
        print(f"{'check':<58} result")
        for name, sql in CHECKS:
            try:
                cur.execute(sql)
                ok = bool(cur.fetchone()[0])
            except Exception as ex:  # report the failing check and keep going
                ok, name = False, f"{name} (error: {str(ex)[:60]})"
            failed += 0 if ok else 1
            print(f"{name:<58} {'PASS' if ok else 'FAIL'}")
            if not ok:
                print(f"::error title=Check failed::{name}")
    finally:
        conn.close()
        os.unlink(key_path)
    print(f"\n{len(CHECKS) - failed}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
