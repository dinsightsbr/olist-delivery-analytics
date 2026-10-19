"""
build_pbip.py — generates the Power BI Project (PBIP) for the Olist case.

Output: ./Olist Delivery Experience/
  Olist Delivery Experience.pbip
  Olist Delivery Experience.SemanticModel/   (TMDL: Snowflake import model + measures)
  Olist Delivery Experience.Report/          (PBIR: 7 pages, visuals as JSON)

Open the .pbip in Power BI Desktop, Refresh, sign in to Snowflake (service user, key pair),
and the dashboard renders. Measures mirror sql/40_semantic.sql; the report is the
storyboard in docs/roteiro-apresentacao.md.

Run:  python build_pbip.py
"""
import json
import re
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = "Olist Delivery Experience"
OUT = ROOT / NAME
SM = OUT / f"{NAME}.SemanticModel"
RP = OUT / f"{NAME}.Report"

SERVER = "fpyndgp-mw62856.snowflakecomputing.com"
WAREHOUSE = "COMPUTE_WH"
ROLE = "BI_READER"
DATABASE = "OLIST"
SCHEMA = "MARTS"
WINDOW = (20170101, 20180831)  # Jan-2017 .. Aug-2018, see DIM_DATE.in_analysis_window

MEAS = "Measures"  # measure-only table (no columns), shows with the calculator icon in Desktop

NS = uuid.UUID("6f1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d")
_auto = 0


def guid(key: str | None = None) -> str:
    """Deterministic ids (uuid5): regenerating the project yields stable, reviewable diffs."""
    global _auto
    if key is None:
        _auto += 1
        key = f"auto:{_auto}"
    return str(uuid.uuid5(NS, key))


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, obj) -> None:
    write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


# =============================================================================
# 1. Semantic model
# =============================================================================
# (technical column name, Snowflake column, dataType, format)
# dataType: string | int64 | double | boolean | dateTime | date
T_DIM_DATE = [
    ("date_key", "DATE_KEY", "int64", "0"),
    ("date", "DATE", "date", None),
    ("year", "YEAR", "int64", "0"),
    ("quarter", "QUARTER", "int64", "0"),
    ("quarter_label", "QUARTER_LABEL", "string", None),
    ("month", "MONTH", "int64", "0"),
    ("month_short", "MONTH_SHORT", "string", None),
    ("year_month", "YEAR_MONTH", "string", None),
    ("month_start", "MONTH_START", "date", None),
    ("day_of_week_iso", "DAY_OF_WEEK_ISO", "int64", "0"),
    ("day_short", "DAY_SHORT", "string", None),
    ("is_weekend", "IS_WEEKEND", "boolean", None),
    ("iso_week", "ISO_WEEK", "int64", "0"),
    ("in_analysis_window", "IN_ANALYSIS_WINDOW", "boolean", None),
]
T_DIM_CUSTOMER = [
    ("customer_unique_id", "CUSTOMER_UNIQUE_ID", "string", None),
    ("customer_zip_prefix", "CUSTOMER_ZIP_PREFIX", "string", None),
    ("customer_city", "CUSTOMER_CITY", "string", None),
    ("customer_state", "CUSTOMER_STATE", "string", None),
    ("customer_state_name", "CUSTOMER_STATE_NAME", "string", None),
    ("customer_region", "CUSTOMER_REGION", "string", None),
    ("customer_lat", "CUSTOMER_LAT", "double", "0.0000"),
    ("customer_lng", "CUSTOMER_LNG", "double", "0.0000"),
    ("orders_count", "ORDERS_COUNT", "int64", "0"),
    ("is_repeat_customer", "IS_REPEAT_CUSTOMER", "boolean", None),
    ("first_purchase_date", "FIRST_PURCHASE_DATE", "date", None),
]
T_DIM_SELLER = [
    ("seller_id", "SELLER_ID", "string", None),
    ("seller_zip_prefix", "SELLER_ZIP_PREFIX", "string", None),
    ("seller_city", "SELLER_CITY", "string", None),
    ("seller_state", "SELLER_STATE", "string", None),
    ("seller_state_name", "SELLER_STATE_NAME", "string", None),
    ("seller_region", "SELLER_REGION", "string", None),
    ("seller_lat", "SELLER_LAT", "double", "0.0000"),
    ("seller_lng", "SELLER_LNG", "double", "0.0000"),
]
T_DIM_PRODUCT = [
    ("product_id", "PRODUCT_ID", "string", None),
    ("category_pt", "CATEGORY_PT", "string", None),
    ("category_en", "CATEGORY_EN", "string", None),
    ("category_label", "CATEGORY_LABEL", "string", None),
    ("name_length", "NAME_LENGTH", "int64", "0"),
    ("description_length", "DESCRIPTION_LENGTH", "int64", "0"),
    ("photos_qty", "PHOTOS_QTY", "int64", "0"),
    ("weight_g", "WEIGHT_G", "int64", "#,0"),
    ("volume_cm3", "VOLUME_CM3", "int64", "#,0"),
    ("weight_band", "WEIGHT_BAND", "string", None),
]
T_FCT_ORDERS = [
    ("order_id", "ORDER_ID", "string", None),
    ("customer_id", "CUSTOMER_ID", "string", None),
    ("customer_unique_id", "CUSTOMER_UNIQUE_ID", "string", None),
    ("primary_seller_id", "PRIMARY_SELLER_ID", "string", None),
    ("order_status", "ORDER_STATUS", "string", None),
    ("purchased_at", "PURCHASED_AT", "dateTime", None),
    ("purchase_date_key", "PURCHASE_DATE_KEY", "int64", "0"),
    ("approved_at", "APPROVED_AT", "dateTime", None),
    ("delivered_to_carrier_at", "DELIVERED_TO_CARRIER_AT", "dateTime", None),
    ("delivered_to_customer_at", "DELIVERED_TO_CUSTOMER_AT", "dateTime", None),
    ("delivered_date_key", "DELIVERED_DATE_KEY", "int64", "0"),
    ("estimated_delivery_at", "ESTIMATED_DELIVERY_AT", "dateTime", None),
    ("estimated_delivery_date_key", "ESTIMATED_DELIVERY_DATE_KEY", "int64", "0"),
    ("is_delivered", "IS_DELIVERED", "boolean", None),
    ("delivery_days", "DELIVERY_DAYS", "int64", "0"),
    ("estimated_days", "ESTIMATED_DAYS", "int64", "0"),
    ("delay_days", "DELAY_DAYS", "int64", "0"),
    ("is_late", "IS_LATE", "boolean", None),
    ("delivery_bucket", "DELIVERY_BUCKET", "string", None),
    ("delivery_bucket_sort", "DELIVERY_BUCKET_SORT", "int64", "0"),
    ("has_review", "HAS_REVIEW", "boolean", None),
    ("review_score", "REVIEW_SCORE", "int64", "0"),
    ("is_low_review", "IS_LOW_REVIEW", "boolean", None),
    ("has_comment", "HAS_COMMENT", "boolean", None),
    ("review_created_at", "REVIEW_CREATED_AT", "dateTime", None),
    ("payment_value", "PAYMENT_VALUE", "double", "#,0.00"),
    ("payment_legs", "PAYMENT_LEGS", "int64", "0"),
    ("max_installments", "MAX_INSTALLMENTS", "int64", "0"),
    ("primary_payment_type", "PRIMARY_PAYMENT_TYPE", "string", None),
    ("items_count", "ITEMS_COUNT", "int64", "0"),
    ("sellers_count", "SELLERS_COUNT", "int64", "0"),
    ("gmv", "GMV", "double", "#,0.00"),
    ("freight_value", "FREIGHT_VALUE", "double", "#,0.00"),
    ("freight_pct", "FREIGHT_PCT", "double", "0.0%"),
    ("customer_state", "CUSTOMER_STATE", "string", None),
    ("primary_seller_state", "PRIMARY_SELLER_STATE", "string", None),
    ("is_interstate", "IS_INTERSTATE", "boolean", None),
]
T_FCT_ORDER_ITEMS = [
    ("order_id", "ORDER_ID", "string", None),
    ("order_item_id", "ORDER_ITEM_ID", "int64", "0"),
    ("product_id", "PRODUCT_ID", "string", None),
    ("seller_id", "SELLER_ID", "string", None),
    ("customer_unique_id", "CUSTOMER_UNIQUE_ID", "string", None),
    ("purchase_date_key", "PURCHASE_DATE_KEY", "int64", "0"),
    ("order_status", "ORDER_STATUS", "string", None),
    ("is_delivered", "IS_DELIVERED", "boolean", None),
    ("is_late", "IS_LATE", "boolean", None),
    ("delay_days", "DELAY_DAYS", "int64", "0"),
    ("delivery_bucket", "DELIVERY_BUCKET", "string", None),
    ("delivery_bucket_sort", "DELIVERY_BUCKET_SORT", "int64", "0"),
    ("review_score", "REVIEW_SCORE", "int64", "0"),
    ("price", "PRICE", "double", "#,0.00"),
    ("freight_value", "FREIGHT_VALUE", "double", "#,0.00"),
    ("freight_pct", "FREIGHT_PCT", "double", "0.0%"),
    ("shipping_limit_at", "SHIPPING_LIMIT_AT", "dateTime", None),
    ("seller_state", "SELLER_STATE", "string", None),
    ("customer_state", "CUSTOMER_STATE", "string", None),
    ("is_interstate", "IS_INTERSTATE", "boolean", None),
]
T_REVIEW_THEMES = [
    ("order_id", "ORDER_ID", "string", None),
    ("review_score", "REVIEW_SCORE", "int64", "0"),
    ("is_late", "IS_LATE", "boolean", None),
    ("delivery_bucket", "DELIVERY_BUCKET", "string", None),
    ("review_comment", "REVIEW_COMMENT", "string", None),
    ("theme", "THEME", "string", None),
]

# Display names for the columns business users see on axes, slicers, tooltips and headers.
# Technical names stay in the Snowflake source; the generator renames on the way in and
# rewrites every DAX reference, so measures keep using the technical names below.
DISPLAY = {
    "date": "Date", "year": "Year", "quarter_label": "Quarter", "month_short": "Month (short)",
    "year_month": "Month", "day_short": "Weekday", "is_weekend": "Weekend?", "in_analysis_window": "In Analysis Window",
    "customer_city": "Customer City", "customer_state": "Customer State", "customer_state_name": "Customer State Name",
    "customer_region": "Customer Region", "orders_count": "Orders per Customer", "is_repeat_customer": "Repeat Customer?",
    "first_purchase_date": "First Purchase Date",
    "seller_city": "Seller City", "seller_state": "Seller State", "seller_state_name": "Seller State Name",
    "seller_region": "Seller Region",
    "category_label": "Category", "weight_band": "Weight Band", "weight_g": "Weight (g)",
    "order_status": "Order Status", "delivery_bucket": "Delivery Outcome", "primary_payment_type": "Payment Type",
    "items_count": "Items in Order", "is_interstate": "Interstate?", "is_late": "Late?",
    "theme": "Complaint Theme", "review_comment": "Comment",
}

# Calculated columns (DAX) per table: (display name, dax, dataType, format)
CALC_COLUMNS = {
    "FCT_ORDERS": [
        ("Is First Order",
         "FCT_ORDERS[purchased_at] = CALCULATE ( MIN ( FCT_ORDERS[purchased_at] ), ALLEXCEPT ( FCT_ORDERS, FCT_ORDERS[customer_unique_id] ) )",
         "boolean", None),
        ("Seller Handling Days",
         "IF ( ISBLANK ( FCT_ORDERS[approved_at] ) || ISBLANK ( FCT_ORDERS[delivered_to_carrier_at] ), BLANK (), DATEDIFF ( FCT_ORDERS[approved_at], FCT_ORDERS[delivered_to_carrier_at], DAY ) )",
         "int64", "0"),
        ("Carrier Transit Days",
         "IF ( ISBLANK ( FCT_ORDERS[delivered_to_carrier_at] ) || ISBLANK ( FCT_ORDERS[delivered_to_customer_at] ), BLANK (), DATEDIFF ( FCT_ORDERS[delivered_to_carrier_at], FCT_ORDERS[delivered_to_customer_at], DAY ) )",
         "int64", "0"),
        ("Cart Size",
         'SWITCH ( TRUE (), ISBLANK ( FCT_ORDERS[items_count] ), "No items", FCT_ORDERS[items_count] = 1, "1 item", FCT_ORDERS[items_count] = 2, "2 items", "3+ items" )',
         "string", None),
    ],
    "DIM_DATE": [
        ("Holiday", "LOOKUPVALUE ( Holidays[Holiday], Holidays[Date], DIM_DATE[date] )", "string", None),
        ("Near Holiday?",
         "VAR _d = DIM_DATE[date] RETURN COUNTROWS ( FILTER ( Holidays, ABS ( DATEDIFF ( Holidays[Date], _d, DAY ) ) <= 3 ) ) > 0",
         "boolean", None),
        ("Purchase Period",
         'VAR _d = DIM_DATE[date] VAR _near = COUNTROWS ( FILTER ( Holidays, ABS ( DATEDIFF ( Holidays[Date], _d, DAY ) ) <= 3 ) ) > 0 RETURN IF ( _near, "Holiday week (±3 days)", "Regular week" )',
         "string", None),
    ],
    "DIM_CUSTOMER": [
        ("First Purchase Month", 'FORMAT ( DIM_CUSTOMER[first_purchase_date], "yyyy-MM" )', "string", None),
    ],
}

# name -> (columns, snowflake table, filter_window, sortBy {col: by}, hidden cols, key col)
SNOWFLAKE_TABLES = {
    "DIM_DATE": dict(cols=T_DIM_DATE, src="DIM_DATE", window=False,
                     sort={"month_short": "month", "day_short": "day_of_week_iso"},
                     hidden={"date_key", "month", "day_of_week_iso", "iso_week", "month_start", "quarter"},
                     key="date", is_date_table=True),
    "DIM_CUSTOMER": dict(cols=T_DIM_CUSTOMER, src="DIM_CUSTOMER", window=False, sort={},
                         hidden={"customer_unique_id", "customer_zip_prefix", "customer_lat", "customer_lng"}, key=None),
    "DIM_SELLER": dict(cols=T_DIM_SELLER, src="DIM_SELLER", window=False, sort={},
                       hidden={"seller_zip_prefix", "seller_lat", "seller_lng"}, key=None),
    "DIM_PRODUCT": dict(cols=T_DIM_PRODUCT, src="DIM_PRODUCT", window=False, sort={},
                        hidden={"category_pt", "category_en", "name_length", "description_length"}, key=None),
    "FCT_ORDERS": dict(cols=T_FCT_ORDERS, src="FCT_ORDERS", window=True,
                       sort={"delivery_bucket": "delivery_bucket_sort"},
                       hidden={"purchase_date_key", "delivered_date_key", "estimated_delivery_date_key",
                               "customer_id", "customer_unique_id", "primary_seller_id", "review_score",
                               "delivery_bucket_sort", "customer_state", "primary_seller_state", "freight_pct"},
                       key=None),
    "FCT_ORDER_ITEMS": dict(cols=T_FCT_ORDER_ITEMS, src="FCT_ORDER_ITEMS", window=True,
                            sort={"delivery_bucket": "delivery_bucket_sort"},
                            hidden={"purchase_date_key", "customer_unique_id", "product_id", "seller_id",
                                    "review_score", "delivery_bucket_sort", "seller_state", "customer_state",
                                    "order_id", "order_item_id"}, key=None),
    "REVIEW_THEMES_RULES": dict(cols=T_REVIEW_THEMES, src="REVIEW_THEMES_RULES", window=False, sort={},
                                hidden={"review_score", "order_id"}, key=None),
}

M_TYPES = {
    "string": "type text",
    "int64": "Int64.Type",
    "double": "type number",
    "boolean": "type logical",
    "dateTime": "type datetime",
    "date": "type date",
}
TMDL_TYPES = {"string": "string", "int64": "int64", "double": "double", "boolean": "boolean",
              "dateTime": "dateTime", "date": "dateTime"}
DEFAULT_FORMAT = {"date": "Short Date", "dateTime": "General Date"}
_TABLE_RE = "|".join(SNOWFLAKE_TABLES)


def disp(name: str) -> str:
    return DISPLAY.get(name, name)


def dax(expr: str) -> str:
    """Rewrite TABLE[technical] references to the display names used in the model."""
    for tech, shown in DISPLAY.items():
        expr = re.sub(rf"\b({_TABLE_RE})\[{re.escape(tech)}\]", lambda m: f"{m.group(1)}[{shown}]", expr)
    return expr


def q(name: str) -> str:
    """Quote a TMDL object name when needed."""
    ok = all(ch.isalnum() or ch == "_" for ch in name)
    return name if ok else f"'{name}'"


def m_partition(table: str, spec: dict) -> str:
    types = ", ".join(f'{{"{src}", {M_TYPES[dt]}}}' for _, src, dt, _ in spec["cols"])
    renames = ", ".join(f'{{"{src}", "{disp(name)}"}}' for name, src, _, _ in spec["cols"])
    lines = [
        "let",
        "    Source = Snowflake.Databases(SnowflakeServer, SnowflakeWarehouse, [Role = SnowflakeRole]),",
        f'    Database = Source{{[Name = "{DATABASE}", Kind = "Database"]}}[Data],',
        f'    Schema = Database{{[Name = "{SCHEMA}", Kind = "Schema"]}}[Data],',
        f'    Data = Schema{{[Name = "{spec["src"]}", Kind = "Table"]}}[Data],',
    ]
    last = "Data"
    if spec["window"]:
        lines.append(
            f"    Windowed = Table.SelectRows(Data, each [PURCHASE_DATE_KEY] >= {WINDOW[0]} and [PURCHASE_DATE_KEY] <= {WINDOW[1]}),")
        last = "Windowed"
    lines.append(f"    Typed = Table.TransformColumnTypes({last}, {{{types}}}),")
    lines.append(f"    Renamed = Table.RenameColumns(Typed, {{{renames}}})")
    lines.append("in")
    lines.append("    Renamed")
    return "\n".join("\t\t\t\t" + ln for ln in lines)


PARAMETERS = [("SnowflakeServer", SERVER), ("SnowflakeWarehouse", WAREHOUSE), ("SnowflakeRole", ROLE)]


def tmdl_expressions() -> str:
    """Power Query parameters: one place to point the model at another account or environment."""
    out = []
    for name, value in PARAMETERS:
        out += [
            f'expression {name} = "{value}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
            f"\tlineageTag: {guid()}",
            "",
            "\tannotation PBI_ResultType = Text",
            "",
        ]
    return "\n".join(out) + "\n"


def tmdl_table(table: str, spec: dict) -> str:
    out = [f"table {q(table)}", f"\tlineageTag: {guid()}"]
    if spec.get("is_date_table"):
        out.append("\tdataCategory: Time")
    out.append("")
    for name, src, dt, fmt in spec["cols"]:
        shown = disp(name)
        out.append(f"\tcolumn {q(shown)}")
        out.append(f"\t\tdataType: {TMDL_TYPES[dt]}")
        if spec.get("key") == name:
            out.append("\t\tisKey")
        if name in spec["hidden"]:
            out.append("\t\tisHidden")
        f = fmt or DEFAULT_FORMAT.get(dt)
        if f:
            out.append(f"\t\tformatString: {f}")
        out.append(f"\t\tlineageTag: {guid()}")
        out.append("\t\tsummarizeBy: none")
        out.append(f"\t\tsourceColumn: {shown}")
        if name in spec["sort"]:
            out.append(f"\t\tsortByColumn: {q(disp(spec['sort'][name]))}")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = User")
        out.append("")
    for shown, expr, dt, fmt in CALC_COLUMNS.get(table, []):
        out.append(f"\tcolumn {q(shown)} = {dax(expr)}")
        out.append(f"\t\tdataType: {TMDL_TYPES[dt]}")
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        out.append("\t\tisDataTypeInferred")
        out.append(f"\t\tlineageTag: {guid()}")
        out.append("\t\tsummarizeBy: none")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = User")
        out.append("")
    out.append(f"\tpartition {q(table)} = m")
    out.append("\t\tmode: import")
    out.append("\t\tsource =")
    out.append(m_partition(table, spec))
    out.append("")
    return "\n".join(out) + "\n"


# ---- measures: (name, dax with technical column names, format, folder) -------
MEASURES = [
    # Sales
    ("GMV", "SUM ( FCT_ORDERS[gmv] )", r"\R\$ #,0", "Sales"),
    ("GMV (M)", "DIVIDE ( [GMV], 1000000 )", r"\R\$ #,0.0\M", "Sales"),
    ("Orders", "COUNTROWS ( FCT_ORDERS )", "#,0", "Sales"),
    ("Avg Order Value", "DIVIDE ( [GMV], [Orders] )", r"\R\$ #,0.00", "Sales"),
    ("Customers", "DISTINCTCOUNT ( FCT_ORDERS[customer_unique_id] )", "#,0", "Sales"),
    ("Customers (all time)", "COUNTROWS ( DIM_CUSTOMER )", "#,0", "Sales"),
    ("Items Sold", "COUNTROWS ( FCT_ORDER_ITEMS )", "#,0", "Sales"),
    ("Items per Order", "DIVIDE ( [Items Sold], [Orders] )", "0.00", "Sales"),
    ("GMV (Items)", "SUM ( FCT_ORDER_ITEMS[price] )", r"\R\$ #,0", "Sales"),
    ("GMV MoM %",
     "VAR _prev = CALCULATE ( [GMV], DATEADD ( DIM_DATE[date], -1, MONTH ) )\nRETURN DIVIDE ( [GMV] - _prev, _prev )",
     "0.0%", "Sales"),
    # Delivery
    ("Delivered Orders", "CALCULATE ( [Orders], FCT_ORDERS[is_delivered] = TRUE () )", "#,0", "Delivery"),
    ("Late Orders", "CALCULATE ( [Orders], FCT_ORDERS[is_late] = TRUE () )", "#,0", "Delivery"),
    # DIVIDE form (not 1 - x) so months/states with no deliveries stay BLANK instead of showing 100%
    ("On-time Delivery %", "DIVIDE ( [Delivered Orders] - [Late Orders], [Delivered Orders] )", "0.0%", "Delivery"),
    ("Late Delivery %", "DIVIDE ( [Late Orders], [Delivered Orders] )", "0.0%", "Delivery"),
    ("Avg Delivery Days",
     "CALCULATE ( AVERAGE ( FCT_ORDERS[delivery_days] ), FCT_ORDERS[is_delivered] = TRUE () )", "0.0", "Delivery"),
    ("Avg Estimated Days",
     "CALCULATE ( AVERAGE ( FCT_ORDERS[estimated_days] ), FCT_ORDERS[is_delivered] = TRUE () )", "0.0", "Delivery"),
    ("Avg Delay Days (late only)",
     "CALCULATE ( AVERAGE ( FCT_ORDERS[delay_days] ), FCT_ORDERS[is_late] = TRUE () )", "0.0", "Delivery"),
    ("Avg Seller Handling Days",
     "CALCULATE ( AVERAGE ( FCT_ORDERS[Seller Handling Days] ), FCT_ORDERS[is_delivered] = TRUE () )", "0.0", "Delivery"),
    ("Avg Carrier Transit Days",
     "CALCULATE ( AVERAGE ( FCT_ORDERS[Carrier Transit Days] ), FCT_ORDERS[is_delivered] = TRUE () )", "0.0", "Delivery"),
    ("Interstate Orders %",
     "DIVIDE (\n    CALCULATE ( [Orders], FCT_ORDERS[is_interstate] = TRUE () ),\n    CALCULATE ( [Orders], NOT ISBLANK ( FCT_ORDERS[is_interstate] ) )\n)",
     "0.0%", "Delivery"),
    ("Late Delivery % (Items)",
     "DIVIDE (\n    CALCULATE ( [Items Sold], FCT_ORDER_ITEMS[is_late] = TRUE () ),\n    CALCULATE ( [Items Sold], FCT_ORDER_ITEMS[is_delivered] = TRUE () )\n)",
     "0.0%", "Delivery"),
    ("Late Delivery % (Items, min 500)", "IF ( [Items Sold] >= 500, [Late Delivery % (Items)] )", "0.0%", "Delivery"),
    ("On-time Delivery % (min 100 orders)", "IF ( [Orders] >= 100, [On-time Delivery %] )", "0.0%", "Delivery"),
    ("Late Delivery % (min 100 orders)", "IF ( [Orders] >= 100, [Late Delivery %] )", "0.0%", "Delivery"),
    ("Share of Late Orders",
     "DIVIDE ( [Late Orders], CALCULATE ( [Late Orders], ALL ( DIM_CUSTOMER ) ) )", "0.0%", "Delivery"),
    ("Cumulative Share of Late Orders",
     "VAR _cur = [Late Orders]\n"
     "VAR _states = ALLSELECTED ( DIM_CUSTOMER[customer_state] )\n"
     "VAR _total = CALCULATE ( [Late Orders], _states )\n"
     "VAR _cum = SUMX ( FILTER ( _states, [Late Orders] >= _cur ), [Late Orders] )\n"
     "RETURN DIVIDE ( _cum, _total )",
     "0%", "Delivery"),
    ("States for 80% of Late Orders",
     "COUNTROWS (\n    FILTER (\n        ALLSELECTED ( DIM_CUSTOMER[customer_state] ),\n"
     "        [Cumulative Share of Late Orders] - [Share of Late Orders] < 0.8 && [Late Orders] > 0\n    )\n)",
     "0", "Delivery"),
    # Experience
    ("Reviews", "CALCULATE ( [Orders], FCT_ORDERS[has_review] = TRUE () )", "#,0", "Experience"),
    ("Avg Review Score", "AVERAGE ( FCT_ORDERS[review_score] )", "0.00", "Experience"),
    ("Avg Review Score (Items)", "AVERAGE ( FCT_ORDER_ITEMS[review_score] )", "0.00", "Experience"),
    ("Low Reviews (1-2)", "CALCULATE ( [Orders], FCT_ORDERS[is_low_review] = TRUE () )", "#,0", "Experience"),
    ("Low Review %", "DIVIDE ( [Low Reviews (1-2)], [Reviews] )", "0.0%", "Experience"),
    ("5-star %", "DIVIDE ( CALCULATE ( [Orders], FCT_ORDERS[review_score] = 5 ), [Reviews] )", "0.0%", "Experience"),
    # "On time" filters use delivery_bucket, never is_late = FALSE(): in DAX BLANK() = FALSE() is TRUE,
    # so is_late = FALSE() would also pick up canceled / in-progress orders (is_late is NULL for them).
    ("Avg Review Score (On time)", 'CALCULATE ( [Avg Review Score], FCT_ORDERS[delivery_bucket] = "On time" )', "0.00", "Experience"),
    ("Avg Review Score (Late)", "CALCULATE ( [Avg Review Score], FCT_ORDERS[is_late] = TRUE () )", "0.00", "Experience"),
    ("Review Gap (On time - Late)", "[Avg Review Score (On time)] - [Avg Review Score (Late)]", "0.00", "Experience"),
    ("Low Review % (On time)", 'CALCULATE ( [Low Review %], FCT_ORDERS[delivery_bucket] = "On time" )', "0.0%", "Experience"),
    ("Low Review % (Late)", "CALCULATE ( [Low Review %], FCT_ORDERS[is_late] = TRUE () )", "0.0%", "Experience"),
    ("Low Reviews from Late Orders %",
     "DIVIDE (\n    CALCULATE ( [Orders], FCT_ORDERS[is_low_review] = TRUE (), FCT_ORDERS[is_late] = TRUE () ),\n    [Low Reviews (1-2)]\n)",
     "0.0%", "Experience"),
    ("Share of on-time reviews",
     'DIVIDE (\n    CALCULATE ( [Reviews], FCT_ORDERS[delivery_bucket] = "On time" ),\n'
     '    CALCULATE ( [Reviews], FCT_ORDERS[delivery_bucket] = "On time", ALL ( FCT_ORDERS[review_score] ) )\n)',
     "0.0%", "Experience"),
    ("Share of late reviews",
     "DIVIDE (\n    CALCULATE ( [Reviews], FCT_ORDERS[is_late] = TRUE () ),\n"
     "    CALCULATE ( [Reviews], FCT_ORDERS[is_late] = TRUE (), ALL ( FCT_ORDERS[review_score] ) )\n)",
     "0.0%", "Experience"),
    ("Low Review Comments", "COUNTROWS ( REVIEW_THEMES_RULES )", "#,0", "Experience"),
    # Loyalty
    ("Repeat Customer %",
     "DIVIDE (\n    CALCULATE ( COUNTROWS ( DIM_CUSTOMER ), DIM_CUSTOMER[is_repeat_customer] = TRUE () ),\n    COUNTROWS ( DIM_CUSTOMER )\n)",
     "0.0%", "Loyalty"),
    ("Repeat Customers", "CALCULATE ( COUNTROWS ( DIM_CUSTOMER ), DIM_CUSTOMER[is_repeat_customer] = TRUE () )", "#,0", "Loyalty"),
    ("First Orders", "CALCULATE ( [Orders], FCT_ORDERS[Is First Order] = TRUE () )", "#,0", "Loyalty"),
    ("Avg Review Score (First Orders)", "CALCULATE ( [Avg Review Score], FCT_ORDERS[Is First Order] = TRUE () )", "0.00", "Loyalty"),
    ("Repeat Rate after On-time First Order",
     'VAR _c =\n    CALCULATETABLE (\n        VALUES ( FCT_ORDERS[customer_unique_id] ),\n'
     '        FCT_ORDERS[Is First Order] = TRUE (), FCT_ORDERS[delivery_bucket] = "On time"\n    )\n'
     "RETURN\n    DIVIDE (\n        CALCULATE ( COUNTROWS ( DIM_CUSTOMER ), DIM_CUSTOMER[is_repeat_customer] = TRUE (), TREATAS ( _c, DIM_CUSTOMER[customer_unique_id] ) ),\n"
     "        COUNTROWS ( _c )\n    )",
     "0.0%", "Loyalty"),
    ("Repeat Rate after Late First Order",
     "VAR _c =\n    CALCULATETABLE (\n        VALUES ( FCT_ORDERS[customer_unique_id] ),\n"
     "        FCT_ORDERS[Is First Order] = TRUE (), FCT_ORDERS[is_late] = TRUE ()\n    )\n"
     "RETURN\n    DIVIDE (\n        CALCULATE ( COUNTROWS ( DIM_CUSTOMER ), DIM_CUSTOMER[is_repeat_customer] = TRUE (), TREATAS ( _c, DIM_CUSTOMER[customer_unique_id] ) ),\n"
     "        COUNTROWS ( _c )\n    )",
     "0.0%", "Loyalty"),
    ("Repeat Rate after Low-review First Order",
     "VAR _c =\n    CALCULATETABLE (\n        VALUES ( FCT_ORDERS[customer_unique_id] ),\n"
     "        FCT_ORDERS[Is First Order] = TRUE (), FCT_ORDERS[is_low_review] = TRUE ()\n    )\n"
     "RETURN\n    DIVIDE (\n        CALCULATE ( COUNTROWS ( DIM_CUSTOMER ), DIM_CUSTOMER[is_repeat_customer] = TRUE (), TREATAS ( _c, DIM_CUSTOMER[customer_unique_id] ) ),\n"
     "        COUNTROWS ( _c )\n    )",
     "0.0%", "Loyalty"),
    # Freight
    ("Freight Value", "SUM ( FCT_ORDERS[freight_value] )", r"\R\$ #,0", "Freight"),
    ("Freight % of GMV", "DIVIDE ( [Freight Value], [GMV] )", "0.0%", "Freight"),
    ("Freight per Order", "DIVIDE ( [Freight Value], [Orders] )", r"\R\$ #,0.00", "Freight"),
    ("Freight % of GMV (Items)", "DIVIDE ( SUM ( FCT_ORDER_ITEMS[freight_value] ), SUM ( FCT_ORDER_ITEMS[price] ) )",
     "0.0%", "Freight"),
    # Scenario
    ("Late Reduction % Value", "SELECTEDVALUE ( 'Late Reduction %'[Late Reduction %], 50 )", "0", "Scenario"),
    ("Scenario Avg Review Score",
     "VAR _x = DIVIDE ( [Late Reduction % Value], 100 )\n"
     "VAR _lateRev = CALCULATE ( [Reviews], FCT_ORDERS[is_late] = TRUE () )\n"
     "VAR _moved = _lateRev * _x\n"
     "VAR _totalScore = SUM ( FCT_ORDERS[review_score] )\n"
     "VAR _newScore = _totalScore + _moved * ( [Avg Review Score (On time)] - [Avg Review Score (Late)] )\n"
     "RETURN DIVIDE ( _newScore, [Reviews] )",
     "0.00", "Scenario"),
    ("Scenario Uplift", "[Scenario Avg Review Score] - [Avg Review Score]", "+0.00;-0.00;0.00", "Scenario"),
    ("Scenario Low Reviews Avoided",
     "VAR _x = DIVIDE ( [Late Reduction % Value], 100 )\n"
     "VAR _lateRev = CALCULATE ( [Reviews], FCT_ORDERS[is_late] = TRUE () )\n"
     "VAR _lowLate = DIVIDE ( CALCULATE ( [Low Reviews (1-2)], FCT_ORDERS[is_late] = TRUE () ), _lateRev )\n"
     "VAR _lowOnTime = DIVIDE (\n"
     '    CALCULATE ( [Low Reviews (1-2)], FCT_ORDERS[delivery_bucket] = "On time" ),\n'
     '    CALCULATE ( [Reviews], FCT_ORDERS[delivery_bucket] = "On time" )\n'
     ")\n"
     "RETURN _lateRev * _x * ( _lowLate - _lowOnTime )",
     "#,0", "Scenario"),
    ("Scenario Late Orders Fixed", "[Late Orders] * DIVIDE ( [Late Reduction % Value], 100 )", "#,0", "Scenario"),
    # Titles (dynamic insight headlines)
    ("Title | Overview",
     'FORMAT ( [Orders], "#,0" ) & " orders and R$ " & FORMAT ( [GMV] / 1e6, "0.0" ) & "M in GMV: "\n'
     '    & FORMAT ( [Late Delivery %], "0.0%" ) & " of deliveries arrived late and the average review is "\n'
     '    & FORMAT ( [Avg Review Score], "0.00" )',
     None, "Titles"),
    ("Title | Delivery vs Experience",
     '"Late deliveries score " & FORMAT ( [Avg Review Score (Late)], "0.00" ) & " stars vs "\n'
     '    & FORMAT ( [Avg Review Score (On time)], "0.00" ) & " when on time; "\n'
     '    & FORMAT ( [Low Reviews from Late Orders %], "0%" ) & " of all 1-2 star reviews come from late orders"',
     None, "Titles"),
    ("Title | Time Split",
     '"Where the days go: on-time orders spend " & FORMAT ( CALCULATE ( [Avg Seller Handling Days], FCT_ORDERS[delivery_bucket] = "On time" ), "0.0" )\n'
     '    & " days with the seller + " & FORMAT ( CALCULATE ( [Avg Carrier Transit Days], FCT_ORDERS[delivery_bucket] = "On time" ), "0.0" )\n'
     '    & " in transit; late orders " & FORMAT ( CALCULATE ( [Avg Seller Handling Days], FCT_ORDERS[is_late] = TRUE () ), "0.0" )\n'
     '    & " + " & FORMAT ( CALCULATE ( [Avg Carrier Transit Days], FCT_ORDERS[is_late] = TRUE () ), "0.0" )',
     None, "Titles"),
    ("Title | Where",
     '"Interstate routes run " & FORMAT ( CALCULATE ( [Late Delivery %], FCT_ORDERS[is_interstate] = TRUE () ), "0.0%" )\n'
     '    & " late vs " & FORMAT ( CALCULATE ( [Late Delivery %], FCT_ORDERS[is_interstate] = FALSE (), FCT_ORDERS[is_delivered] = TRUE () ), "0.0%" )\n'
     '    & " within the same state; the Northeast and Rio de Janeiro are the outliers"',
     None, "Titles"),
    ("Title | Pareto",
     'FORMAT ( [States for 80% of Late Orders], "0" ) & " states hold 80% of all late orders: fix the lanes, not the map"',
     None, "Titles"),
    ("Title | Loyalty",
     '"Customers whose first order arrived late come back " & FORMAT ( [Repeat Rate after Late First Order], "0.0%" )\n'
     '    & " of the time, vs " & FORMAT ( [Repeat Rate after On-time First Order], "0.0%" ) & " after an on-time first order"',
     None, "Titles"),
    ("Title | Scenario",
     '"Cutting late deliveries by " & FORMAT ( [Late Reduction % Value], "0" ) & "% lifts the average review from "\n'
     '    & FORMAT ( [Avg Review Score], "0.00" ) & " to " & FORMAT ( [Scenario Avg Review Score], "0.00" )\n'
     '    & " and avoids " & FORMAT ( [Scenario Low Reviews Avoided], "#,0" ) & " one- and two-star reviews"',
     None, "Titles"),
    # Colors (conditional formatting by field value)
    ("Color | Delivery Bucket",
     'SWITCH (\n    SELECTEDVALUE ( FCT_ORDERS[delivery_bucket] ),\n'
     '    "On time", "#2B6CB0",\n    "Late 1-7 days", "#DD6B20",\n    "Late 8+ days", "#C53030",\n'
     '    "Canceled / unavailable", "#A0AEC0",\n    "#718096"\n)',
     None, "Colors"),
    ("Color | Late Flag",
     'IF ( SELECTEDVALUE ( FCT_ORDERS[is_late] ) = TRUE (), "#C53030", "#2B6CB0" )', None, "Colors"),
]


def tmdl_measures_table() -> str:
    """Measure-only table: a zero-column M partition, so Desktop shows the calculator icon."""
    out = [f"table {MEAS}", f"\tlineageTag: {guid()}", ""]
    for name, expr, fmt, folder in MEASURES:
        out.append(f"\tmeasure {q(name)} =")
        for ln in dax(expr).split("\n"):
            out.append("\t\t\t" + ln)
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        out.append(f"\t\tlineageTag: {guid()}")
        out.append(f"\t\tdisplayFolder: {folder}")
        out.append("")
    out += [
        f"\tpartition {MEAS} = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tlet",
        "\t\t\t\t    Source = #table({}, {})",
        "\t\t\t\tin",
        "\t\t\t\t    Source",
        "",
    ]
    return "\n".join(out) + "\n"


def tmdl_parameter_table() -> str:
    return f"""table 'Late Reduction %'
	lineageTag: {guid()}

	column 'Late Reduction %'
		dataType: int64
		formatString: 0
		lineageTag: {guid()}
		summarizeBy: none
		sourceColumn: [Value]

		annotation SummarizationSetBy = User

	partition 'Late Reduction %' = calculated
		mode: import
		source = GENERATESERIES ( 0, 100, 5 )

"""


def tmdl_datatable(table: str, cols: list, rows: list, measures: list | None = None) -> str:
    """Calculated table from DATATABLE. cols: (name, DAX type, tmdl type, format). rows: tuples."""
    def lit_(v):
        return str(v) if isinstance(v, (int, float)) else '"' + str(v).replace('"', '""') + '"'
    out = [f"table {q(table)}", f"\tlineageTag: {guid()}", ""]
    for name, _, tt, fmt in cols:
        out.append(f"\tcolumn {q(name)}")
        out.append(f"\t\tdataType: {tt}")
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        out.append("\t\tisNameInferred")
        out.append(f"\t\tlineageTag: {guid()}")
        out.append("\t\tsummarizeBy: none")
        out.append(f"\t\tsourceColumn: [{name}]")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = User")
        out.append("")
    for name, expr, fmt in (measures or []):
        out.append(f"\tmeasure {q(name)} = {expr}")
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        out.append(f"\t\tlineageTag: {guid()}")
        out.append("")
    header = ", ".join(f'"{n}", {dt}' for n, dt, _, _ in cols)
    out += [f"\tpartition {q(table)} = calculated", "\t\tmode: import", "\t\tsource =",
            "\t\t\t\tDATATABLE (", f"\t\t\t\t    {header},", "\t\t\t\t    {"]
    body = ",\n".join("\t\t\t\t        { " + ", ".join(lit_(v) for v in r) + " }" for r in rows)
    out += [body, "\t\t\t\t    }", "\t\t\t\t)", ""]
    return "\n".join(out) + "\n"


RECOMMENDATIONS = [
    (1, "Carrier / last-mile review on the SP to RJ lanes", "RJ on-time from 87.8% to the 93% national average", 3, 5),
    (2, "Re-set delivery promises by lane for the Northeast; pick partners by lane reliability", "NE late rate under 10%", 4, 4),
    (3, "Proactive message + voucher when an order passes its estimated date", "Late-order low-review rate from 62% toward 9%", 1, 4),
    (4, "Delivery-confirmation audit: 'delivered on time' orders the customer never received", "Close the gap between delivered and received", 3, 3),
    (5, "Weekly late-orders alert by seller and lane from this model", "Keep the fix visible", 1, 2),
    (6, "Classify all review comments with an LLM; add a split-shipment flag for multi-seller orders", "Size the remaining themes", 2, 3),
]

HOLIDAYS = [
    ("2017-01-01", "New Year"), ("2017-02-27", "Carnival Monday"), ("2017-02-28", "Carnival Tuesday"),
    ("2017-04-14", "Good Friday"), ("2017-04-21", "Tiradentes"), ("2017-05-01", "Labour Day"),
    ("2017-06-15", "Corpus Christi"), ("2017-09-07", "Independence Day"), ("2017-10-12", "Our Lady of Aparecida"),
    ("2017-11-02", "All Souls"), ("2017-11-15", "Republic Day"), ("2017-11-24", "Black Friday"), ("2017-12-25", "Christmas"),
    ("2018-01-01", "New Year"), ("2018-02-12", "Carnival Monday"), ("2018-02-13", "Carnival Tuesday"),
    ("2018-03-30", "Good Friday"), ("2018-04-21", "Tiradentes"), ("2018-05-01", "Labour Day"),
    ("2018-05-31", "Corpus Christi"), ("2018-09-07", "Independence Day"), ("2018-10-12", "Our Lady of Aparecida"),
    ("2018-11-02", "All Souls"), ("2018-11-15", "Republic Day"), ("2018-11-23", "Black Friday"), ("2018-12-25", "Christmas"),
]

DEFINITIONS = [
    ("Overview", "GMV", "Sum of item prices of the orders in the period (BRL). Freight is not included; no fees or taxes are deducted (the dataset has none).", "Sum of FCT_ORDERS[gmv]"),
    ("Overview", "Orders", "Count of orders purchased in the period, any status.", "COUNTROWS of FCT_ORDERS"),
    ("Overview", "Avg Order Value", "GMV divided by orders.", "GMV / Orders"),
    ("Overview", "On-time Delivery %", "Share of delivered orders that reached the customer on or before the estimated date. Canceled and in-transit orders are excluded from both sides.", "(Delivered - Late) / Delivered"),
    ("Overview", "Avg Review Score", "Average of the 1-5 star review, one review per order (the latest answer when there are several).", "AVERAGE of review_score"),
    ("Overview", "Repeat Customer %", "Customers with two or more orders over the whole dataset, divided by all customers. Not filtered by period.", "Customers with orders_count > 1 / customers"),
    ("Delivery", "Delivered", "Order status 'delivered' with a customer delivery timestamp.", "status = delivered AND delivered_to_customer_at IS NOT NULL"),
    ("Delivery", "Late", "Delivered after the estimated delivery date shown at checkout, in calendar days.", "delivered date > estimated date"),
    ("Delivery", "Delivery Outcome", "On time; Late 1-7 days; Late 8+ days; In progress; Canceled / unavailable.", "Buckets of delay_days and status"),
    ("Delivery", "Seller Handling Days", "Days between payment approval and the hand-over to the carrier.", "DATEDIFF(approved_at, delivered_to_carrier_at)"),
    ("Delivery", "Carrier Transit Days", "Days between the hand-over to the carrier and the delivery to the customer.", "DATEDIFF(delivered_to_carrier_at, delivered_to_customer_at)"),
    ("Delivery", "Near Holiday?", "Purchase date within 3 days of a Brazilian national holiday, Carnival or Black Friday.", "Holidays table, +-3 days"),
    ("Delivery", "Interstate?", "The main seller of the order is in a different state from the customer.", "seller state <> customer state"),
    ("Delivery", "Share of Late Orders", "The state's (or region's) share of every late order in the period.", "Late Orders / Late Orders (all states)"),
    ("Experience", "Low Review %", "Reviews with 1 or 2 stars divided by reviews.", "Low reviews / reviews"),
    ("Experience", "Complaint Theme", "Theme of each 1-2 star comment, assigned by keyword rules in Portuguese (not received, late, wrong or incomplete, defect, service, other).", "sql/50_cortex.sql, REVIEW_THEMES_RULES"),
    ("Loyalty", "Is First Order", "The customer's earliest order in the dataset.", "purchased_at = MIN per customer"),
    ("Loyalty", "Repeat Rate after Late First Order", "Among customers whose first order was late, the share that bought again (any time).", "Repeat customers / customers with a late first order"),
    ("Freight", "Freight % of GMV", "Freight charged to customers divided by GMV.", "Freight / GMV"),
    ("Scenario", "Late Reduction %", "What-if parameter: share of late orders assumed to be delivered on time.", "Slider 0-100"),
    ("Scenario", "Scenario Avg Review Score", "Moved orders receive the on-time average score instead of the late average; everything else unchanged.", "(total score + moved x (on-time avg - late avg)) / reviews"),
    ("Data", "Analysis window", "Orders purchased from Jan 2017 to Aug 2018; the edges of the dataset are sparse.", "Power Query filter on purchase_date_key"),
]

RELATIONSHIPS = [
    ("FCT_ORDERS", "purchase_date_key", "DIM_DATE", "date_key"),
    ("FCT_ORDERS", "customer_unique_id", "DIM_CUSTOMER", "customer_unique_id"),
    ("FCT_ORDERS", "primary_seller_id", "DIM_SELLER", "seller_id"),
    ("FCT_ORDER_ITEMS", "purchase_date_key", "DIM_DATE", "date_key"),
    ("FCT_ORDER_ITEMS", "customer_unique_id", "DIM_CUSTOMER", "customer_unique_id"),
    ("FCT_ORDER_ITEMS", "seller_id", "DIM_SELLER", "seller_id"),
    ("FCT_ORDER_ITEMS", "product_id", "DIM_PRODUCT", "product_id"),
    ("REVIEW_THEMES_RULES", "order_id", "FCT_ORDERS", "order_id"),
]


def tmdl_relationships() -> str:
    out = []
    for ft, fc, tt, tc in RELATIONSHIPS:
        out.append(f"relationship {guid()}")
        out.append(f"\tfromColumn: {q(ft)}.{q(disp(fc))}")
        out.append(f"\ttoColumn: {q(tt)}.{q(disp(tc))}")
        out.append("")
    return "\n".join(out) + "\n"


def build_semantic_model() -> None:
    write(SM / "definition.pbism", json.dumps({"version": "4.0", "settings": {}}, indent=2) + "\n")
    write_json(SM / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": guid()},
    })
    write(SM / "definition" / "database.tmdl", "database\n\tcompatibilityLevel: 1601\n\n")
    order = [n for n, _ in PARAMETERS] + list(SNOWFLAKE_TABLES) + [MEAS, "Late Reduction %", "Recommendations", "Holidays", "Definitions"]
    write(SM / "definition" / "model.tmdl",
          "model Model\n"
          "\tculture: en-US\n"
          "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
          "\tsourceQueryCulture: en-US\n"
          "\tdataAccessOptions\n"
          "\t\tlegacyRedirects\n"
          "\t\treturnErrorValuesAsNull\n"
          "\n"
          "annotation __PBI_TimeIntelligenceEnabled = 0\n"
          "\n"
          f"annotation PBI_QueryOrder = {json.dumps(order)}\n"
          "\n")
    write(SM / "definition" / "expressions.tmdl", tmdl_expressions())
    for t, spec in SNOWFLAKE_TABLES.items():
        write(SM / "definition" / "tables" / f"{t}.tmdl", tmdl_table(t, spec))
    write(SM / "definition" / "tables" / f"{MEAS}.tmdl", tmdl_measures_table())
    write(SM / "definition" / "tables" / "Late Reduction %.tmdl", tmdl_parameter_table())
    write(SM / "definition" / "tables" / "Recommendations.tmdl", tmdl_datatable(
        "Recommendations",
        [("No", "INTEGER", "int64", "0"), ("Action", "STRING", "string", None), ("Target", "STRING", "string", None),
         ("Effort", "INTEGER", "int64", "0"), ("Impact", "INTEGER", "int64", "0")],
        RECOMMENDATIONS,
        measures=[("Effort (1-5)", "MAX ( Recommendations[Effort] )", "0"), ("Impact (1-5)", "MAX ( Recommendations[Impact] )", "0")]))
    write(SM / "definition" / "tables" / "Holidays.tmdl", tmdl_datatable(
        "Holidays", [("Date", "DATETIME", "dateTime", "Short Date"), ("Holiday", "STRING", "string", None)], HOLIDAYS))
    write(SM / "definition" / "tables" / "Definitions.tmdl", tmdl_datatable(
        "Definitions",
        [("Page", "STRING", "string", None), ("Metric", "STRING", "string", None),
         ("Definition", "STRING", "string", None), ("Rule", "STRING", "string", None)],
        DEFINITIONS))
    write(SM / "definition" / "relationships.tmdl", tmdl_relationships())


# =============================================================================
# 2. Report (PBIR)
# =============================================================================
SCHEMA_BASE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
# Standard pages: visuals laid out on a 1280x720 grid and scaled onto a 1600x900 canvas, leaving a
# BAND-pixel strip at the top for the branded background. Tall pages use raw 1600-wide coordinates.
PAGE_W, PAGE_H = 1600, 900
BAND = 64
SX = PAGE_W / 1280
SY = (PAGE_H - BAND) / 720
BRANDING = ROOT / "branding"
BACKGROUNDS = {900: "bg_1600x900.png", 1600: "bg_1600x1600.png"}

BLUE, RED, GRAY, ORANGE, GREEN, PURPLE, GOLD, SLATE = (
    "#2B6CB0", "#C53030", "#718096", "#DD6B20", "#2F855A", "#6B46C1", "#B7791F", "#4A5568")
NAVY = "#1A365D"


def lit(value) -> dict:
    """Literal expression. Strings must be passed with single quotes already, e.g. "'text'"."""
    return {"expr": {"Literal": {"Value": value}}}


def s(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def col(table: str, name: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": disp(name)}}


def mea(name: str, table: str = MEAS) -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def proj(field: dict) -> dict:
    kind = "Column" if "Column" in field else "Measure"
    entity = field[kind]["Expression"]["SourceRef"]["Entity"]
    prop = field[kind]["Property"]
    return {"field": field, "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}


def title_obj(text=None, measure=None, size=12, show=True) -> dict:
    props = {"show": lit("true" if show else "false")}
    if text is not None:
        props["text"] = lit(s(text))
    if measure is not None:
        props["text"] = {"expr": mea(measure)}
    props["fontSize"] = lit(f"{size}D")
    props["bold"] = lit("true")
    props["fontColor"] = lit(s("#1A202C"))
    return {"title": [{"properties": props}]}


class Page:
    def __init__(self, name: str, display: str, height: int = PAGE_H, raw: bool = False):
        self.name = name
        self.display = display
        self.height = height
        self.raw = raw  # raw: coordinates are canvas pixels (1600 wide); otherwise the 1280x720 grid
        self.visuals = []

    def add(self, vtype: str, x: int, y: int, w: int, h: int, roles: dict | None = None,
            title: str | None = None, title_measure: str | None = None, objects: dict | None = None,
            sort: tuple | None = None, extra: dict | None = None, no_title: bool = False, title_size: int = 12,
            vc_objects: dict | None = None, raw: bool | None = None):
        use_raw = self.raw if raw is None else raw
        if use_raw:
            pos = {"x": x, "y": y, "width": w, "height": h}
        else:
            pos = {"x": round(x * SX), "y": round(y * SY) + BAND, "width": round(w * SX), "height": round(h * SY)}
        v = {
            "$schema": f"{SCHEMA_BASE}/visualContainer/1.0.0/schema.json",
            "name": uuid.uuid5(NS, "visual:" + self.name + ":" + json.dumps(
                [vtype, title, title_measure, roles, objects, vc_objects], sort_keys=True, default=str)).hex[:16],
            "position": {**pos, "z": len(self.visuals), "tabOrder": len(self.visuals)},
            "visual": {"visualType": vtype, "drillFilterOtherVisuals": True},
        }
        vis = v["visual"]
        if roles:
            vis["query"] = {"queryState": {role: {"projections": [proj(f) for f in fields]}
                                           for role, fields in roles.items()}}
            if sort:
                field, direction = sort
                vis["query"]["sortDefinition"] = {"sort": [{"field": field, "direction": direction}],
                                                  "isDefaultSort": True}
        if objects:
            vis["objects"] = objects
        vco = {}
        if no_title:
            vco = title_obj(show=False)
        elif title is not None or title_measure is not None:
            vco = title_obj(text=title, measure=title_measure, size=title_size)
        if vc_objects:
            vco.update(vc_objects)
        if vco:
            vis["visualContainerObjects"] = vco
        if extra:
            vis.update(extra)
        self.visuals.append(v)
        return v


def textbox(page: Page, x, y, w, h, runs, raw=None):
    """runs: list of paragraphs; each paragraph is a list of (text, style dict)."""
    paragraphs = []
    for para in runs:
        paragraphs.append({"textRuns": [{"value": t, "textStyle": st} for t, st in para]})
    return page.add("textbox", x, y, w, h,
                    objects={"general": [{"properties": {"paragraphs": paragraphs}}]}, no_title=True, raw=raw)


def card(page: Page, x, y, w, h, measure: str, label_size=24, raw=None):
    return page.add("card", x, y, w, h, roles={"Values": [mea(measure)]},
                    objects={"labels": [{"properties": {"fontSize": lit(f"{label_size}D"),
                                                        "color": lit(s("#1A202C")),
                                                        "labelDisplayUnits": lit("1D")}}],
                             "categoryLabels": [{"properties": {"show": lit("true"),
                                                                "fontSize": lit("10D"),
                                                                "color": lit(s(GRAY))}}]},
                    no_title=True, raw=raw)


def slicer(page: Page, x, y, w, h, field: dict, title: str, mode: str = "Dropdown", raw=None):
    return page.add("slicer", x, y, w, h, roles={"Values": [field]},
                    objects={"data": [{"properties": {"mode": lit(s(mode))}}],
                             "header": [{"properties": {"show": lit("true"), "text": lit(s(title)),
                                                        "fontSize": lit("10D")}}]},
                    no_title=True, raw=raw)


def nav_button(page: Page, text: str, target: str, x=1452, y=14, w=128, h=36):
    """Action button in the top band that navigates to another page (info / back)."""
    return page.add("actionButton", x, y, w, h, raw=True,
                    objects={"text": [{"properties": {"show": lit("true"), "text": lit(s(text)),
                                                      "fontSize": lit("11D"), "fontColor": lit(s("#FFFFFF"))}}],
                             "fill": [{"properties": {"show": lit("true"),
                                                      "fillColor": {"solid": {"color": lit(s(BLUE))}}}}],
                             "outline": [{"properties": {"show": lit("false")}}],
                             "action": [{"properties": {"show": lit("true"),
                                                        "type": lit(s("PageNavigation")),
                                                        "navigationTarget": lit(s(target))}}]},
                    no_title=True)


def data_labels(show=True, units_none=False) -> dict:
    props = {"show": lit("true" if show else "false")}
    if units_none:
        props["labelDisplayUnits"] = lit("1D")
    return {"labels": [{"properties": props}]}


def axes_off() -> dict:
    """Executive charts: the visual title carries the meaning; raw axis titles stay off."""
    return {"categoryAxis": [{"properties": {"showAxisTitle": lit("false")}}],
            "valueAxis": [{"properties": {"showAxisTitle": lit("false")}}]}


def legend_top() -> dict:
    return {"legend": [{"properties": {"show": lit("true"), "position": lit(s("Top"))}}]}


def field_color(measure: str) -> dict:
    return {"dataPoint": [{
        "properties": {"fill": {"solid": {"color": {"expr": mea(measure)}}}},
        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]},
    }]}


def heat(measure: str, low: str = "#FFFFFF", high: str = RED) -> dict:
    """Matrix cell background as a two-colour gradient on the measure value."""
    return {"values": [{
        "properties": {"backColor": {"solid": {"color": {"expr": {"FillRule": {
            "Input": mea(measure),
            "FillRule": {"linearGradient2": {"min": {"color": {"Literal": {"Value": s(low)}}},
                                             "max": {"color": {"Literal": {"Value": s(high)}}}}}}}}}}},
        "selector": {"metadata": f"{MEAS}.{measure}"},
    }]}


H1 = {"fontSize": "18pt", "fontWeight": "bold", "color": "#1A202C"}
SUB = {"fontSize": "10pt", "color": "#4A5568"}
BODY = {"fontSize": "10pt", "color": "#1A202C"}
BODYB = {"fontSize": "10pt", "fontWeight": "bold", "color": "#1A202C"}
NOTE = {"fontSize": "9pt", "color": "#718096"}
DEFS_PAGE = "p6_definitions"


def header(page: Page, title: str, subtitle: str, slicers=True, info=True):
    if page.raw:
        textbox(page, 24, 80, 950, 84, [[(title, H1)], [(subtitle, SUB)]])
        if slicers:
            slicer(page, 1000, 84, 270, 68, col("DIM_DATE", "year"), "Year")
            slicer(page, 1300, 84, 276, 68, col("DIM_CUSTOMER", "customer_region"), "Customer region")
    else:
        textbox(page, 20, 12, 760, 70, [[(title, H1)], [(subtitle, SUB)]])
        if slicers:
            slicer(page, 800, 16, 216, 58, col("DIM_DATE", "year"), "Year")
            slicer(page, 1040, 16, 216, 58, col("DIM_CUSTOMER", "customer_region"), "Customer region")
    if info:
        nav_button(page, "ⓘ  Definitions", DEFS_PAGE)


def build_pages() -> list:
    pages = []

    # ---------------------------------------------------------------- page 1
    p = Page("p1_overview", "Executive Overview")
    header(p, "Delivering on the promise",
           "How late deliveries shape customer experience on a Brazilian marketplace (Olist, Jan 2017 to Aug 2018)")
    kpis = ["GMV (M)", "Orders", "Avg Order Value", "On-time Delivery %", "Avg Review Score", "Repeat Customer %"]
    for i, m in enumerate(kpis):
        card(p, 20 + i * 208, 90, 196, 92, m)
    p.add("lineClusteredColumnComboChart", 20, 196, 760, 300,
          roles={"Category": [col("DIM_DATE", "year_month")],
                 "Y": [mea("Orders")],
                 "Y2": [mea("On-time Delivery %")],
                 "Tooltips": [mea("Late Orders"), mea("Late Delivery %"), mea("Avg Delivery Days"),
                              mea("Avg Review Score"), mea("GMV"), mea("Avg Order Value")]},
          title_measure="Title | Overview", title_size=12,
          objects={**legend_top(), **axes_off()})
    p.add("clusteredBarChart", 800, 196, 456, 300,
          roles={"Category": [col("DIM_CUSTOMER", "customer_state")],
                 "Y": [mea("Orders")],
                 "Tooltips": [mea("GMV"), mea("On-time Delivery %"), mea("Share of Late Orders"), mea("Avg Review Score")]},
          sort=(mea("Orders"), "Descending"),
          title="Where the orders are: São Paulo is 4 in 10 orders, Rio and Minas follow",
          objects={**data_labels(units_none=True), **axes_off()})
    textbox(p, 20, 512, 400, 190, [
        [("The headline", BODYB)],
        [("Sales grew through 2017 and 2018, but satisfaction did not follow and only 3 in 100 customers ever bought again. "
          "One in fifteen deliveries arrives after the promised date, and a late delivery is the single most damaging "
          "experience in the data: it is 6.7 times more likely to end in a 1-2 star review.", BODY)],
        [("The next pages show the mechanism, where it happens, who comes back, and what to do first.", NOTE)],
    ])
    p.add("lineChart", 440, 512, 400, 190,
          roles={"Category": [col("DIM_DATE", "year_month")], "Y": [mea("Avg Review Score")],
                 "Tooltips": [mea("Reviews"), mea("Low Review %"), mea("Late Delivery %")]},
          title="Average review score by month stays near 4.1 while volume triples",
          objects=axes_off())
    p.add("scatterChart", 860, 512, 396, 190,
          roles={"Category": [col("DIM_DATE", "year_month")],
                 "X": [mea("Orders")],
                 "Y": [mea("Late Delivery %")],
                 "Tooltips": [mea("Avg Delivery Days"), mea("Avg Review Score")]},
          title="Does volume drive lateness? Each dot is a month: only the Black Friday peak breaks the pattern",
          objects={"categoryLabels": [{"properties": {"show": lit("true")}}]})
    pages.append(p)

    # ---------------------------------------------------------------- page 2 (tall)
    p = Page("p2_delivery_experience", "Delivery & Customer Experience", height=1600, raw=True)
    header(p, "A late order is a bad review",
           "Review score by delivery outcome; reviews are collected when the order is delivered or the estimated date passes")
    cardw = (1576 - 24 - 5 * 14) // 6
    for i, m in enumerate(["Avg Review Score (On time)", "Avg Review Score (Late)", "Low Review % (On time)",
                           "Low Review % (Late)", "Low Reviews from Late Orders %", "Avg Delay Days (late only)"]):
        card(p, 24 + i * (cardw + 14), 176, cardw, 104, m, label_size=24)
    # Row C: outcome vs score · score distribution
    p.add("clusteredColumnChart", 24, 296, 764, 330,
          roles={"Category": [col("FCT_ORDERS", "delivery_bucket")],
                 "Y": [mea("Avg Review Score")],
                 "Tooltips": [mea("Orders"), mea("Low Review %"), mea("Avg Delay Days (late only)")]},
          title_measure="Title | Delivery vs Experience",
          objects={**data_labels(), **field_color("Color | Delivery Bucket"), **axes_off()})
    p.add("clusteredColumnChart", 812, 296, 764, 330,
          roles={"Category": [col("FCT_ORDERS", "review_score")],
                 "Y": [mea("Share of on-time reviews"), mea("Share of late reviews")]},
          title="Distribution of review scores, on time (blue) vs late (red): late orders pile up at 1 star",
          objects={**data_labels(), **legend_top(), **axes_off()})
    # Row D: month trend · where the days go
    p.add("lineClusteredColumnComboChart", 24, 642, 764, 300,
          roles={"Category": [col("DIM_DATE", "year_month")],
                 "Y": [mea("Late Delivery %")],
                 "Y2": [mea("Avg Review Score")],
                 "Tooltips": [mea("Orders"), mea("Late Orders"), mea("Avg Delivery Days")]},
          title="Late rate by month (columns) against average review (line): the spikes line up",
          objects={**legend_top(), **axes_off()})
    p.add("clusteredColumnChart", 812, 642, 764, 300,
          roles={"Category": [col("FCT_ORDERS", "delivery_bucket")],
                 "Y": [mea("Avg Seller Handling Days"), mea("Avg Carrier Transit Days")],
                 "Tooltips": [mea("Avg Delivery Days"), mea("Avg Estimated Days"), mea("Orders")]},
          title_measure="Title | Time Split",
          objects={**data_labels(), **legend_top(), **axes_off()})
    # Row E: weekday · weekday x month heatmap · holiday weeks
    p.add("clusteredBarChart", 24, 958, 420, 300,
          roles={"Category": [col("DIM_DATE", "day_short")],
                 "Y": [mea("Late Delivery %")],
                 "Tooltips": [mea("Orders"), mea("Avg Delivery Days")]},
          title="Late rate by purchase weekday",
          objects={**data_labels(), **axes_off()})
    p.add("pivotTable", 460, 958, 700, 300,
          roles={"Rows": [col("DIM_DATE", "day_short")],
                 "Columns": [col("DIM_DATE", "year_month")],
                 "Values": [mea("Late Delivery %")]},
          title="Heat map: late rate by purchase weekday (rows) and month (columns); darker = later",
          objects=heat("Late Delivery %"))
    p.add("clusteredBarChart", 1176, 958, 400, 300,
          roles={"Category": [col("DIM_DATE", "Purchase Period")],
                 "Y": [mea("Late Delivery %")],
                 "Tooltips": [mea("Orders"), mea("Avg Delivery Days"), mea("Avg Review Score")]},
          title="Orders placed within 3 days of a holiday, Carnival or Black Friday vs regular weeks",
          objects={**data_labels(), **axes_off()})
    # Row F: cart size · weight · categories
    p.add("clusteredBarChart", 24, 1274, 420, 150,
          roles={"Category": [col("FCT_ORDERS", "Cart Size")],
                 "Y": [mea("Late Delivery %")],
                 "Tooltips": [mea("Orders"), mea("Low Review %")]},
          title="Late rate by items in the order",
          objects={**data_labels(), **axes_off()})
    p.add("clusteredBarChart", 460, 1274, 420, 150,
          roles={"Category": [col("DIM_PRODUCT", "weight_band")],
                 "Y": [mea("Late Delivery % (Items)")],
                 "Tooltips": [mea("Items Sold")]},
          title="Late rate by product weight band",
          objects={**data_labels(), **axes_off()})
    p.add("tableEx", 896, 1274, 680, 150,
          roles={"Values": [col("DIM_PRODUCT", "category_label"), mea("Items Sold"),
                            mea("Late Delivery % (Items, min 500)"), mea("Avg Review Score (Items)"),
                            mea("Freight % of GMV (Items)")]},
          sort=(mea("Late Delivery % (Items, min 500)"), "Descending"),
          title="Categories with the highest late rate (500+ items sold); scroll for the full list",
          objects={"total": [{"properties": {"totals": lit("false")}}]})
    # Row G: complaint themes · sample comments
    p.add("barChart", 24, 1440, 764, 140,
          roles={"Category": [col("REVIEW_THEMES_RULES", "theme")],
                 "Series": [col("REVIEW_THEMES_RULES", "is_late")],
                 "Y": [mea("Low Review Comments")]},
          sort=(mea("Low Review Comments"), "Descending"),
          title="What 1-2 star comments say (rule-based themes; blank = order not delivered): 'never received' leads",
          objects={**data_labels(), **legend_top(), **axes_off()})
    p.add("tableEx", 812, 1440, 764, 140,
          roles={"Values": [col("REVIEW_THEMES_RULES", "theme"), col("REVIEW_THEMES_RULES", "review_comment")]},
          title="Read the voice of the customer: click a theme on the left to filter the comments",
          objects={"total": [{"properties": {"totals": lit("false")}}]})
    pages.append(p)

    # ---------------------------------------------------------------- page 3
    p = Page("p3_where", "Where it happens")
    header(p, "Two different problems: Rio de Janeiro and the Northeast",
           "On-time delivery, lead time and freight share by customer state and by seller-to-customer lane")
    p.add("barChart", 20, 90, 520, 420,
          roles={"Category": [col("DIM_CUSTOMER", "customer_state")],
                 "Y": [mea("On-time Delivery % (min 100 orders)")],
                 "Tooltips": [mea("Orders"), mea("Share of Late Orders"), mea("Avg Delivery Days"),
                              mea("Avg Review Score"), mea("Freight % of GMV")]},
          sort=(mea("On-time Delivery % (min 100 orders)"), "Ascending"),
          title_measure="Title | Where",
          objects={**data_labels(), **axes_off()})
    p.add("pivotTable", 560, 90, 696, 200,
          roles={"Rows": [col("DIM_SELLER", "seller_region")],
                 "Columns": [col("DIM_CUSTOMER", "customer_region")],
                 "Values": [mea("Late Delivery %")]},
          title="Late rate by lane: seller region (rows) to customer region (columns)",
          objects=heat("Late Delivery %"))
    p.add("scatterChart", 560, 310, 696, 200,
          roles={"Category": [col("DIM_CUSTOMER", "customer_state")],
                 "X": [mea("Freight % of GMV")],
                 "Y": [mea("Late Delivery % (min 100 orders)")],
                 "Size": [mea("Orders")]},
          title="Freight share vs late rate by state (bubble size = orders): the Northeast pays more and waits longer",
          objects={"categoryLabels": [{"properties": {"show": lit("true")}}]})
    p.add("lineClusteredColumnComboChart", 20, 526, 620, 176,
          roles={"Category": [col("DIM_CUSTOMER", "customer_state")],
                 "Y": [mea("Late Orders")],
                 "Y2": [mea("Cumulative Share of Late Orders")],
                 "Tooltips": [mea("Share of Late Orders"), mea("Late Delivery %")]},
          sort=(mea("Late Orders"), "Descending"),
          title_measure="Title | Pareto",
          objects={**legend_top(), **axes_off()})
    p.add("pivotTable", 660, 526, 596, 176,
          roles={"Rows": [col("DIM_CUSTOMER", "customer_state")],
                 "Columns": [col("FCT_ORDERS", "is_interstate")],
                 "Values": [mea("Late Delivery % (min 100 orders)")]},
          title="Same-state vs interstate late rate per state: Rio is late even on local deliveries",
          objects=heat("Late Delivery % (min 100 orders)"))
    pages.append(p)

    # ---------------------------------------------------------------- page 4: loyalty
    p = Page("p4_loyalty", "Loyalty & Cohorts")
    header(p, "Who comes back, and what the first delivery has to do with it",
           "Repeat purchase is measured over the whole dataset; the first order is the customer's earliest order")
    for i, m in enumerate(["Customers (all time)", "Repeat Customers", "Repeat Customer %",
                           "Repeat Rate after On-time First Order", "Repeat Rate after Late First Order",
                           "Repeat Rate after Low-review First Order"]):
        card(p, 20 + i * 208, 90, 196, 92, m, label_size=22)
    p.add("clusteredBarChart", 20, 196, 620, 300,
          roles={"Category": [col("DIM_CUSTOMER", "customer_region")],
                 "Y": [mea("Repeat Customer %")],
                 "Tooltips": [mea("Customers (all time)"), mea("Repeat Customers"), mea("Avg Review Score (First Orders)")]},
          sort=(mea("Repeat Customer %"), "Descending"),
          title_measure="Title | Loyalty",
          objects={**data_labels(), **axes_off()})
    p.add("pivotTable", 660, 196, 596, 300,
          roles={"Rows": [col("DIM_CUSTOMER", "First Purchase Month")],
                 "Values": [mea("Customers (all time)"), mea("Repeat Customer %"), mea("Avg Review Score (First Orders)"),
                            mea("Late Delivery %")]},
          title="Cohorts by first-purchase month: customers, how many returned, their first review and late rate",
          objects=heat("Repeat Customer %", high=GREEN))
    p.add("clusteredBarChart", 20, 512, 620, 190,
          roles={"Category": [col("DIM_CUSTOMER", "customer_state")],
                 "Y": [mea("Repeat Customer %")],
                 "Tooltips": [mea("Customers (all time)"), mea("On-time Delivery %")]},
          sort=(mea("Repeat Customer %"), "Descending"),
          title="Repeat rate by customer state",
          objects={**data_labels(), **axes_off()})
    textbox(p, 660, 512, 596, 190, [
        [("How to read this page", BODYB)],
        [("Only 3 in 100 customers ever place a second order, so the business lives on first impressions. The three "
          "cards on the right split customers by what happened on their first order: delivered on time, delivered late, "
          "or rated 1-2 stars. If the repeat rate after a late first order is clearly lower, late deliveries are not "
          "only a review problem but a retention problem, and the carrier work on page 3 has a revenue case.", BODY)],
        [("Repeat status comes from the whole dataset (a customer may have returned after Aug 2018 is not visible), "
          "so the rates are conservative. Cohorts list customers by the month of their first purchase.", NOTE)],
    ])
    pages.append(p)

    # ---------------------------------------------------------------- page 5: recommendations
    p = Page("p5_recommendations", "Recommendations")
    textbox(p, 20, 12, 760, 70, [[("What to do first", H1)],
                                 [("Three actions in order, and a what-if on how much satisfaction they buy back", SUB)]])
    slicer(p, 800, 16, 216, 58, col("DIM_CUSTOMER", "customer_region"), "Customer region")
    slicer(p, 1040, 16, 216, 58, col("DIM_CUSTOMER", "customer_state"), "Customer state")
    nav_button(p, "ⓘ  Definitions", DEFS_PAGE)
    slicer(p, 20, 90, 300, 84, col("Late Reduction %", "Late Reduction %"), "Late deliveries cut by (%)",
           mode="Single")
    for i, m in enumerate(["Late Orders", "Scenario Late Orders Fixed", "Scenario Avg Review Score",
                           "Scenario Uplift", "Scenario Low Reviews Avoided"]):
        card(p, 340 + i * 186, 90, 174, 84, m, label_size=22)
    p.add("scatterChart", 20, 190, 360, 320,
          roles={"Category": [col("Recommendations", "No")],
                 "X": [mea("Effort (1-5)", "Recommendations")],
                 "Y": [mea("Impact (1-5)", "Recommendations")]},
          title="Impact vs effort by action number: start top-left",
          objects={"categoryLabels": [{"properties": {"show": lit("true")}}]})
    p.add("tableEx", 400, 190, 520, 320,
          roles={"Values": [col("Recommendations", "No"), col("Recommendations", "Action"),
                            col("Recommendations", "Target")]},
          sort=(col("Recommendations", "No"), "Ascending"),
          title="Recommended actions and targets",
          objects={"total": [{"properties": {"totals": lit("false")}}]})
    textbox(p, 940, 190, 316, 320, [
        [("Why these, in this order", BODYB)],
        [("1 Rio: the largest pool of late orders that one carrier conversation can fix; it is late even on local "
          "deliveries (page 3). 2 Northeast: 19-25 day lead times and 12-22% late rates are a network and promise "
          "problem, so promises and partners are set by lane. 3 Proactive message: the cheapest lever; it targets the "
          "62% bad-review rate of late orders while logistics is fixed. 4 Audit: ~1,100 orders are 'delivered on time' "
          "in the system while the customer says nothing arrived. 5-6 keep the fix visible and size the other complaint "
          "themes.", BODY)],
        [("The what-if: move the slider to assume a share of late orders had arrived on time; those orders take the "
          "on-time average score. Filter to a region or state to see where the gain concentrates.", NOTE)],
    ])
    p.add("clusteredBarChart", 20, 526, 1236, 176,
          roles={"Category": [col("DIM_CUSTOMER", "customer_state")],
                 "Y": [mea("Scenario Low Reviews Avoided")],
                 "Tooltips": [mea("Late Orders"), mea("Scenario Avg Review Score")]},
          sort=(mea("Scenario Low Reviews Avoided"), "Descending"),
          title_measure="Title | Scenario",
          objects={**data_labels(), **axes_off()})
    pages.append(p)

    # ---------------------------------------------------------------- page 6: definitions
    p = Page(DEFS_PAGE, "Definitions")
    textbox(p, 20, 12, 1000, 70, [[("Metric dictionary and business rules", H1)],
                                  [("What each number means, how it is computed and which rule it follows. Use the page slicer to focus.", SUB)]])
    slicer(p, 1040, 16, 216, 58, col("Definitions", "Page"), "Page")
    nav_button(p, "← Overview", "p1_overview")
    p.add("tableEx", 20, 90, 1236, 612,
          roles={"Values": [col("Definitions", "Page"), col("Definitions", "Metric"),
                            col("Definitions", "Definition"), col("Definitions", "Rule")]},
          sort=(col("Definitions", "Page"), "Ascending"),
          title="Definitions",
          objects={"total": [{"properties": {"totals": lit("false")}}],
                   "grid": [{"properties": {"textSize": lit("10D")}}]})
    pages.append(p)

    # ---------------------------------------------------------------- page 7: appendix
    p = Page("p7_appendix", "Appendix: Model & Data Quality")
    textbox(p, 20, 12, 1236, 70, [[("Under the hood", H1)],
                                  [("Snowflake model, business rules, data quality checks and the measure dictionary", SUB)]])
    nav_button(p, "ⓘ  Definitions", DEFS_PAGE)
    textbox(p, 20, 90, 600, 612, [
        [("Architecture", BODYB)],
        [("9 Kaggle CSVs land in OLIST.RAW (one table per file, all VARCHAR, replayable). OLIST.STG views type, rename and "
          "deduplicate to one row per business key (one review per order, payments aggregated to the order). OLIST.MARTS is a "
          "star schema materialized as tables: DIM_DATE, DIM_CUSTOMER (grain: customer_unique_id), DIM_SELLER, DIM_PRODUCT, "
          "FCT_ORDERS (grain: order) and FCT_ORDER_ITEMS (grain: item). A Snowflake SEMANTIC VIEW (SV_ORDERS) defines the "
          "KPIs once; the DAX measures mirror it name for name. In medallion terms: RAW is bronze, STG is silver, MARTS is gold.", BODY)],
        [("Business rules", BODYB)],
        [("Delivered = status 'delivered' with a customer delivery timestamp. Late = delivered after the estimated date "
          "(calendar days). Low review = score 1 or 2. Interstate = primary seller state differs from customer state. "
          "Analysis window = orders purchased Jan 2017 to Aug 2018 (edges of the dataset are sparse); applied in the "
          "Power Query partitions of both facts. Holidays, handling and transit days, cart size and first-order flags are "
          "computed in the model (DAX) on top of the warehouse columns.", BODY)],
        [("Data quality checks (sql/90_checks.sql)", BODYB)],
        [("Unique keys in every mart; row counts RAW = STG = MARTS; GMV reconciled to the cent (R$ 13,591,643.70) across "
          "RAW, FCT_ORDERS and FCT_ORDER_ITEMS; zero orphan keys; 775 canceled/unavailable orders without items kept and "
          "documented; review duplicates resolved to the latest answer per order; geolocation averaged per zip prefix "
          "inside the Brazil bounding box. The same checks run in CI against Snowflake with a read-only service user.", BODY)],
        [("Governance", BODYB)],
        [("Power BI connects in Import mode with the read-only role BI_READER, which can only see OLIST.MARTS, through a "
          "service user with key-pair authentication. Naming follows dbt conventions (stg_, dim_, fct_). The report is a "
          "Power BI Project (PBIP: TMDL + PBIR) generated from code and versioned in Git; every pull request runs SQL lint, "
          "schema validation and a semantic-model diff.", BODY)],
        [("Every number reconciled against the warehouse before use.", NOTE)],
    ])
    p.add("tableEx", 640, 90, 616, 300,
          roles={"Values": [col("DIM_DATE", "year_month"), mea("Orders"), mea("GMV"), mea("Late Delivery %"),
                            mea("Avg Review Score")]},
          sort=(col("DIM_DATE", "year_month"), "Ascending"),
          title="Reconciliation: matches OLIST.MARTS.V_KPI_MONTHLY for Jan 2017 to Aug 2018")
    textbox(p, 640, 406, 616, 296, [
        [("Measure dictionary (selection)", BODYB)],
        [("GMV = SUM(FCT_ORDERS[gmv]) · Orders = COUNTROWS(FCT_ORDERS) · Delivered Orders = Orders where is_delivered · "
          "Late Orders = Orders where is_late · On-time Delivery % = (Delivered - Late) / Delivered · Avg Review Score = "
          "AVERAGE(review_score) at order grain · Low Review % = reviews with score 1-2 / reviews · Freight % of GMV = "
          "SUM(freight) / SUM(gmv) · Repeat Customer % = customers with 2+ orders / customers (all time).", BODY)],
        [("Scenario: if X% of late orders in the current selection had arrived on time, they are assumed to receive the "
          "on-time average score instead of the late average. Uplift = scenario average - current average; low reviews "
          "avoided = moved orders x (late low-review rate - on-time low-review rate).", BODY)],
        [("Full definitions on the Definitions page, in powerbi/measures.md and in sql/40_semantic.sql.", NOTE)],
    ])
    pages.append(p)
    return pages


THEME = {
    "name": "OlistTheme",
    "dataColors": [BLUE, RED, GRAY, ORANGE, GREEN, PURPLE, GOLD, SLATE],
    "background": "#FFFFFF",
    "foreground": "#1A202C",
    "tableAccent": BLUE,
    "good": GREEN,
    "neutral": ORANGE,
    "bad": RED,
    "maximum": BLUE,
    "center": "#A0AEC0",
    "minimum": RED,
    "textClasses": {
        "label": {"fontSize": 10, "fontFace": "Segoe UI", "color": "#1A202C"},
        "title": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#1A202C"},
        "header": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#1A202C"},
        "callout": {"fontSize": 24, "fontFace": "Segoe UI", "color": "#1A202C"},
    },
    "visualStyles": {
        "*": {"*": {
            "background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
            "border": [{"show": True, "color": {"solid": {"color": "#E2E8F0"}}, "radius": 6}],
            "title": [{"show": True, "fontSize": 12, "bold": True, "fontColor": {"solid": {"color": "#1A202C"}}}],
        }},
        "page": {"*": {"background": [{"color": {"solid": {"color": "#F7FAFC"}}, "transparency": 0}]}},
    },
}


def page_background(image: str) -> dict:
    return {"background": [{"properties": {
        "image": {"image": {
            "name": lit(s(image)),
            "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1, "ItemName": image}}},
            "scaling": lit(s("Fit")),
        }},
        "transparency": lit("0D"),
    }}]}


def build_report(pages: list) -> None:
    write_json(RP / "definition.pbir", {
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}},
    })
    write_json(RP / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": guid()},
    })
    write_json(RP / "StaticResources" / "RegisteredResources" / "OlistTheme.json", THEME)
    for image in BACKGROUNDS.values():
        bg = BRANDING / image
        if not bg.exists():
            raise SystemExit(f"missing {bg}: run branding/make_backgrounds.py first")
        shutil.copyfile(bg, RP / "StaticResources" / "RegisteredResources" / image)
    write_json(RP / "definition" / "version.json", {
        "$schema": f"{SCHEMA_BASE}/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0",
    })
    write_json(RP / "definition" / "report.json", {
        "$schema": f"{SCHEMA_BASE}/report/1.0.0/schema.json",
        "themeCollection": {
            "baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.55", "type": "SharedResources"},
            "customTheme": {"name": "OlistTheme.json", "reportVersionAtImport": "5.55", "type": "RegisteredResources"},
        },
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": "CY24SU06", "path": "BaseThemes/CY24SU06.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": "OlistTheme.json", "path": "OlistTheme.json", "type": "CustomTheme"}]
                      + [{"name": img, "path": img, "type": "Image"} for img in BACKGROUNDS.values()]},
        ],
        "layoutOptimization": "None",
        "settings": {
            "useStylableVisualContainerHeader": True,
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
        },
    })
    write_json(RP / "definition" / "pages" / "pages.json", {
        "$schema": f"{SCHEMA_BASE}/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [p.name for p in pages],
        "activePageName": pages[0].name,
    })
    for p in pages:
        write_json(RP / "definition" / "pages" / p.name / "page.json", {
            "$schema": f"{SCHEMA_BASE}/page/1.0.0/schema.json",
            "name": p.name,
            "displayName": p.display,
            "displayOption": "FitToPage" if p.height == PAGE_H else "FitToWidth",
            "height": p.height,
            "width": PAGE_W,
            "objects": page_background(BACKGROUNDS[p.height]),
        })
        for v in p.visuals:
            write_json(RP / "definition" / "pages" / p.name / "visuals" / v["name"] / "visual.json", v)


def build_pbip() -> None:
    write_json(OUT / f"{NAME}.pbip", {
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })
    write(OUT / ".gitignore", "# Power BI Desktop local cache\n*.SemanticModel/.pbi/\n*.Report/.pbi/\n")


def main() -> None:
    if OUT.exists():
        # keep Desktop's local caches if present; regenerate everything else
        for sub in (SM / "definition", RP / "definition", RP / "StaticResources"):
            if sub.exists():
                shutil.rmtree(sub)
    build_semantic_model()
    build_report(build_pages())
    build_pbip()
    n_vis = sum(1 for _ in RP.rglob("visual.json"))
    n_tbl = sum(1 for _ in (SM / "definition" / "tables").glob("*.tmdl"))
    print(f"OK: {OUT}\n  tables: {n_tbl}  measures: {len(MEASURES)}  visuals: {n_vis}")


if __name__ == "__main__":
    main()
