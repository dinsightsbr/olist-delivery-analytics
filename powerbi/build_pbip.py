"""
build_pbip.py — generates the Power BI Project (PBIP) for the Olist case.

Output: ./Olist Delivery Experience/
  Olist Delivery Experience.pbip
  Olist Delivery Experience.SemanticModel/   (TMDL: Snowflake import model + measures)
  Olist Delivery Experience.Report/          (PBIR: 5 pages, visuals as JSON)

Open the .pbip in Power BI Desktop, Refresh, sign in to Snowflake (user + MFA),
and the dashboard renders. Measures mirror sql/40_semantic.sql; the report
is the storyboard in docs/roteiro-apresentacao.md.

Run:  python build_pbip.py
"""
import json
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

MEAS = "_Measures"


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
# (model column name, Snowflake column, dataType, format)
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

# name -> (columns, snowflake table, filter_window, sortBy {col: by}, hidden cols, key col)
SNOWFLAKE_TABLES = {
    "DIM_DATE": dict(cols=T_DIM_DATE, src="DIM_DATE", window=False,
                     sort={"month_short": "month", "day_short": "day_of_week_iso"},
                     hidden={"date_key"}, key="date", is_date_table=True),
    "DIM_CUSTOMER": dict(cols=T_DIM_CUSTOMER, src="DIM_CUSTOMER", window=False, sort={}, hidden=set(), key=None),
    "DIM_SELLER": dict(cols=T_DIM_SELLER, src="DIM_SELLER", window=False, sort={}, hidden=set(), key=None),
    "DIM_PRODUCT": dict(cols=T_DIM_PRODUCT, src="DIM_PRODUCT", window=False, sort={}, hidden=set(), key=None),
    "FCT_ORDERS": dict(cols=T_FCT_ORDERS, src="FCT_ORDERS", window=True,
                       sort={"delivery_bucket": "delivery_bucket_sort"},
                       hidden={"purchase_date_key", "delivered_date_key", "estimated_delivery_date_key",
                               "customer_id", "customer_unique_id", "primary_seller_id", "review_score",
                               "delivery_bucket_sort"}, key=None),
    "FCT_ORDER_ITEMS": dict(cols=T_FCT_ORDER_ITEMS, src="FCT_ORDER_ITEMS", window=True,
                            sort={"delivery_bucket": "delivery_bucket_sort"},
                            hidden={"purchase_date_key", "customer_unique_id", "product_id", "seller_id",
                                    "review_score", "delivery_bucket_sort"}, key=None),
    "REVIEW_THEMES_RULES": dict(cols=T_REVIEW_THEMES, src="REVIEW_THEMES_RULES", window=False, sort={},
                                hidden={"review_score"}, key=None),
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


def q(name: str) -> str:
    """Quote a TMDL object name when needed."""
    ok = all(ch.isalnum() or ch == "_" for ch in name)
    return name if ok else f"'{name}'"


def m_partition(table: str, spec: dict) -> str:
    types = ", ".join(f'{{"{src}", {M_TYPES[dt]}}}' for _, src, dt, _ in spec["cols"])
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
    lines.append(f"    Typed = Table.TransformColumnTypes({last}, {{{types}}})")
    lines.append("in")
    lines.append("    Typed")
    return "\n".join("\t\t\t\t" + ln for ln in lines)


PARAMETERS = [("SnowflakeServer", SERVER), ("SnowflakeWarehouse", WAREHOUSE), ("SnowflakeRole", ROLE)]


def tmdl_expressions() -> str:
    """Power Query parameters: one place to point the model at another account or environment."""
    out = []
    for name, value in PARAMETERS:
        out += [
            f'expression {name} = "{value}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
            f"	lineageTag: {guid()}",
            "",
            "	annotation PBI_ResultType = Text",
            "",
        ]
    return "\n".join(out) + "\n"


def tmdl_table(table: str, spec: dict) -> str:
    out = [f"table {q(table)}", f"\tlineageTag: {guid()}"]
    if spec.get("is_date_table"):
        out.append("\tdataCategory: Time")
    out.append("")
    for name, src, dt, fmt in spec["cols"]:
        out.append(f"\tcolumn {q(name)}")
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
        out.append(f"\t\tsourceColumn: {src}")
        if name in spec["sort"]:
            out.append(f"\t\tsortByColumn: {q(spec['sort'][name])}")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = User")
        out.append("")
    out.append(f"\tpartition {q(table)} = m")
    out.append("\t\tmode: import")
    out.append("\t\tsource =")
    out.append(m_partition(table, spec))
    out.append("")
    return "\n".join(out) + "\n"


# ---- measures: (name, dax, format, folder) ---------------------------------
MEASURES = [
    # Sales
    ("GMV", "SUM ( FCT_ORDERS[gmv] )", r"\R\$ #,0", "Sales"),
    ("GMV (M)", "DIVIDE ( [GMV], 1000000 )", r"\R\$ #,0.0\M", "Sales"),
    ("Orders", "COUNTROWS ( FCT_ORDERS )", "#,0", "Sales"),
    ("Avg Order Value", "DIVIDE ( [GMV], [Orders] )", r"\R\$ #,0.00", "Sales"),
    ("Customers", "DISTINCTCOUNT ( FCT_ORDERS[customer_unique_id] )", "#,0", "Sales"),
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
    # share of all late orders that happen in the current customer state / region: "where is the pool?"
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
    ("Repeat Customer %",
     "DIVIDE (\n    CALCULATE ( DISTINCTCOUNT ( DIM_CUSTOMER[customer_unique_id] ), DIM_CUSTOMER[is_repeat_customer] = TRUE () ),\n    DISTINCTCOUNT ( DIM_CUSTOMER[customer_unique_id] )\n)",
     "0.0%", "Experience"),
    ("Low Review Comments", "COUNTROWS ( REVIEW_THEMES_RULES )", "#,0", "Experience"),
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
    ("Title | Where",
     '"Interstate routes run " & FORMAT ( CALCULATE ( [Late Delivery %], FCT_ORDERS[is_interstate] = TRUE () ), "0.0%" )\n'
     '    & " late vs " & FORMAT ( CALCULATE ( [Late Delivery %], FCT_ORDERS[is_interstate] = FALSE (), FCT_ORDERS[is_delivered] = TRUE () ), "0.0%" )\n'
     '    & " within the same state; the Northeast and Rio de Janeiro are the outliers"',
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
    out = [f"table {MEAS}", f"\tlineageTag: {guid()}", ""]
    for name, dax, fmt, folder in MEASURES:
        out.append(f"\tmeasure {q(name)} =")
        for ln in dax.split("\n"):
            out.append("\t\t\t" + ln)
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        out.append(f"\t\tlineageTag: {guid()}")
        out.append(f"\t\tdisplayFolder: {folder}")
        out.append("")
    out += [
        "\tcolumn Value",
        "\t\tdataType: int64",
        "\t\tisHidden",
        "\t\tisNameInferred",
        f"\t\tlineageTag: {guid()}",
        "\t\tsummarizeBy: none",
        "\t\tsourceColumn: [Value]",
        "",
        "\t\tannotation SummarizationSetBy = Automatic",
        "",
        f"\tpartition {MEAS} = calculated",
        "\t\tmode: import",
        '\t\tsource = ROW ( "Value", 1 )',
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


RECOMMENDATIONS = [
    (1, "Carrier / last-mile review on the SP to RJ lanes", "RJ on-time from 87.8% to the 93% national average", 3, 5),
    (2, "Re-set delivery promises by lane for the Northeast; pick partners by lane reliability", "NE late rate under 10%", 4, 4),
    (3, "Proactive message + voucher when an order passes its estimated date", "Late-order low-review rate from 62% toward 9%", 1, 4),
    (4, "Delivery-confirmation audit: 'delivered on time' orders the customer never received", "Close the gap between delivered and received", 3, 3),
    (5, "Weekly late-orders alert by seller and lane from this model", "Keep the fix visible", 1, 2),
    (6, "Classify all review comments with Cortex; add a split-shipment flag for multi-seller orders", "Size the remaining themes", 2, 3),
]


def tmdl_recommendations_table() -> str:
    rows = ",\n".join(
        f'            {{ {n}, "{a}", "{t}", {e}, {i} }}' for n, a, t, e, i in RECOMMENDATIONS
    )
    cols = [("No", "int64", "0"), ("Action", "string", None), ("Target", "string", None),
            ("Effort", "int64", "0"), ("Impact", "int64", "0")]
    out = ["table Recommendations", f"\tlineageTag: {guid()}", ""]
    for name, dt, fmt in cols:
        out.append(f"\tcolumn {name}")
        out.append(f"\t\tdataType: {dt}")
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        out.append("\t\tisNameInferred")
        out.append(f"\t\tlineageTag: {guid()}")
        out.append("\t\tsummarizeBy: none")
        out.append(f"\t\tsourceColumn: [{name}]")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = User")
        out.append("")
    out += [
        "\tmeasure 'Effort (1-5)' = MAX ( Recommendations[Effort] )",
        "\t\tformatString: 0",
        f"\t\tlineageTag: {guid()}",
        "",
        "\tmeasure 'Impact (1-5)' = MAX ( Recommendations[Impact] )",
        "\t\tformatString: 0",
        f"\t\tlineageTag: {guid()}",
        "",
        "\tpartition Recommendations = calculated",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tDATATABLE (",
        '\t\t\t\t    "No", INTEGER, "Action", STRING, "Target", STRING, "Effort", INTEGER, "Impact", INTEGER,',
        "\t\t\t\t    {",
    ]
    out += ["\t\t\t\t" + ln for ln in rows.split("\n")]
    out += ["\t\t\t\t    }", "\t\t\t\t)", ""]
    return "\n".join(out) + "\n"


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
        out.append(f"\tfromColumn: {q(ft)}.{q(fc)}")
        out.append(f"\ttoColumn: {q(tt)}.{q(tc)}")
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
    order = [n for n, _ in PARAMETERS] + list(SNOWFLAKE_TABLES) + [MEAS, "Late Reduction %", "Recommendations"]
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
    write(SM / "definition" / "tables" / "Recommendations.tmdl", tmdl_recommendations_table())
    write(SM / "definition" / "relationships.tmdl", tmdl_relationships())


# =============================================================================
# 2. Report (PBIR)
# =============================================================================
SCHEMA_BASE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
# Visuals are laid out on a 1280x720 grid and scaled onto a 1600x900 canvas, leaving a
# BAND-pixel strip at the top for the branded background (logo + dataset tag).
PAGE_W, PAGE_H = 1600, 900
BAND = 64
SX = PAGE_W / 1280
SY = (PAGE_H - BAND) / 720
BACKGROUND = "bg_1600x900.png"
BRANDING = ROOT / "branding"

BLUE, RED, GRAY, ORANGE, GREEN, PURPLE, GOLD, SLATE = (
    "#2B6CB0", "#C53030", "#718096", "#DD6B20", "#2F855A", "#6B46C1", "#B7791F", "#4A5568")


def lit(value) -> dict:
    """Literal expression. Strings must be passed with single quotes already, e.g. "'text'"."""
    return {"expr": {"Literal": {"Value": value}}}


def s(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def col(table: str, name: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


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
    def __init__(self, name: str, display: str):
        self.name = name
        self.display = display
        self.visuals = []

    def add(self, vtype: str, x: int, y: int, w: int, h: int, roles: dict | None = None,
            title: str | None = None, title_measure: str | None = None, objects: dict | None = None,
            sort: tuple | None = None, extra: dict | None = None, no_title: bool = False, title_size: int = 12):
        v = {
            "$schema": f"{SCHEMA_BASE}/visualContainer/1.0.0/schema.json",
            "name": uuid.uuid5(NS, "visual:" + self.name + ":" + json.dumps(
                [vtype, title, title_measure, roles, objects], sort_keys=True, default=str)).hex[:16],
            "position": {"x": round(x * SX), "y": round(y * SY) + BAND, "z": len(self.visuals),
                         "width": round(w * SX), "height": round(h * SY), "tabOrder": len(self.visuals)},
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
        if no_title:
            vis["visualContainerObjects"] = title_obj(show=False)
        elif title is not None or title_measure is not None:
            vis["visualContainerObjects"] = title_obj(text=title, measure=title_measure, size=title_size)
        if extra:
            vis.update(extra)
        self.visuals.append(v)
        return v


def textbox(page: Page, x, y, w, h, runs):
    """runs: list of paragraphs; each paragraph is a list of (text, style dict)."""
    paragraphs = []
    for para in runs:
        paragraphs.append({"textRuns": [{"value": t, "textStyle": st} for t, st in para]})
    return page.add("textbox", x, y, w, h,
                    objects={"general": [{"properties": {"paragraphs": paragraphs}}]}, no_title=True)


def card(page: Page, x, y, w, h, measure: str, label_size=24):
    return page.add("card", x, y, w, h, roles={"Values": [mea(measure)]},
                    objects={"labels": [{"properties": {"fontSize": lit(f"{label_size}D"),
                                                        "color": lit(s("#1A202C")),
                                                        "labelDisplayUnits": lit("1D")}}],
                             "categoryLabels": [{"properties": {"show": lit("true"),
                                                                "fontSize": lit("10D"),
                                                                "color": lit(s(GRAY))}}]},
                    no_title=True)


def slicer(page: Page, x, y, w, h, field: dict, title: str, mode: str = "Dropdown"):
    return page.add("slicer", x, y, w, h, roles={"Values": [field]},
                    objects={"data": [{"properties": {"mode": lit(s(mode))}}],
                             "header": [{"properties": {"show": lit("true"), "text": lit(s(title)),
                                                        "fontSize": lit("10D")}}]},
                    no_title=True)


def data_labels(show=True, units_none=False) -> dict:
    props = {"show": lit("true" if show else "false")}
    if units_none:
        props["labelDisplayUnits"] = lit("1D")
    return {"labels": [{"properties": props}]}


def field_color(measure: str) -> dict:
    return {"dataPoint": [{
        "properties": {"fill": {"solid": {"color": {"expr": mea(measure)}}}},
        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]},
    }]}


H1 = {"fontSize": "18pt", "fontWeight": "bold", "color": "#1A202C"}
SUB = {"fontSize": "10pt", "color": "#4A5568"}
BODY = {"fontSize": "10pt", "color": "#1A202C"}
BODYB = {"fontSize": "10pt", "fontWeight": "bold", "color": "#1A202C"}
NOTE = {"fontSize": "9pt", "color": "#718096"}


def header(page: Page, title: str, subtitle: str, slicers=True):
    textbox(page, 20, 12, 760, 70, [[(title, H1)], [(subtitle, SUB)]])
    if slicers:
        slicer(page, 800, 16, 216, 58, col("DIM_DATE", "year"), "Year")
        slicer(page, 1040, 16, 216, 58, col("DIM_CUSTOMER", "customer_region"), "Customer region")


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
                 "Y2": [mea("On-time Delivery %")]},
          title_measure="Title | Overview", title_size=12,
          objects={"legend": [{"properties": {"show": lit("true"), "position": lit(s("Top"))}}]})
    p.add("clusteredBarChart", 800, 196, 456, 300,
          roles={"Category": [col("DIM_CUSTOMER", "customer_state")],
                 "Y": [mea("Orders")],
                 "Tooltips": [mea("GMV"), mea("On-time Delivery %"), mea("Avg Review Score")]},
          sort=(mea("Orders"), "Descending"),
          title="Where the orders are: São Paulo is 4 in 10 orders, Rio and Minas follow",
          objects=data_labels(units_none=True))
    textbox(p, 20, 512, 400, 190, [
        [("The headline", BODYB)],
        [("Sales grew through 2017 and 2018, but satisfaction did not follow and only 3 in 100 customers ever bought again. "
          "One in fifteen deliveries arrives after the promised date, and a late delivery is the single most damaging "
          "experience in the data: it is 6.7 times more likely to end in a 1-2 star review.", BODY)],
        [("The next pages show the mechanism, where it happens and what to do first.", NOTE)],
    ])
    p.add("lineChart", 440, 512, 400, 190,
          roles={"Category": [col("DIM_DATE", "year_month")], "Y": [mea("Avg Review Score")]},
          title="Average review score by month stays near 4.1 while volume triples")
    p.add("clusteredBarChart", 860, 512, 396, 190,
          roles={"Category": [col("DIM_CUSTOMER", "customer_region")],
                 "Y": [mea("GMV")], "Tooltips": [mea("Orders"), mea("Freight % of GMV")]},
          sort=(mea("GMV"), "Descending"),
          title="GMV by customer region", objects=data_labels())
    pages.append(p)

    # ---------------------------------------------------------------- page 2
    p = Page("p2_delivery_experience", "Delivery & Customer Experience")
    header(p, "A late order is a bad review",
           "Review score by delivery outcome; reviews are collected when the order is delivered or the estimated date passes")
    for i, m in enumerate(["Avg Review Score (On time)", "Avg Review Score (Late)", "Low Review % (On time)",
                           "Low Review % (Late)", "Low Reviews from Late Orders %", "Avg Delay Days (late only)"]):
        card(p, 20 + i * 208, 90, 196, 92, m, label_size=22)
    p.add("clusteredColumnChart", 20, 196, 600, 300,
          roles={"Category": [col("FCT_ORDERS", "delivery_bucket")],
                 "Y": [mea("Avg Review Score")],
                 "Tooltips": [mea("Orders"), mea("Low Review %")]},
          title_measure="Title | Delivery vs Experience",
          objects={**data_labels(), **field_color("Color | Delivery Bucket")})
    p.add("clusteredColumnChart", 640, 196, 616, 300,
          roles={"Category": [col("FCT_ORDERS", "review_score")],
                 "Y": [mea("Share of on-time reviews"), mea("Share of late reviews")]},
          title="Distribution of review scores, on time (blue) vs late (red): late orders pile up at 1 star",
          objects={**data_labels(),
                   "legend": [{"properties": {"show": lit("true"), "position": lit(s("Top"))}}]})
    p.add("lineClusteredColumnComboChart", 20, 512, 600, 190,
          roles={"Category": [col("DIM_DATE", "year_month")],
                 "Y": [mea("Late Delivery %")],
                 "Y2": [mea("Avg Review Score")]},
          title="Late rate by month (columns) against average review (line): the spikes line up",
          objects={"legend": [{"properties": {"show": lit("true"), "position": lit(s("Top"))}}]})
    p.add("barChart", 640, 512, 616, 190,
          roles={"Category": [col("REVIEW_THEMES_RULES", "theme")],
                 "Series": [col("REVIEW_THEMES_RULES", "is_late")],
                 "Y": [mea("Low Review Comments")]},
          sort=(mea("Low Review Comments"), "Descending"),
          title="What 1-2 star comments say: 'never received' leads, and a third of those are marked delivered on time",
          objects={**data_labels(),
                   "legend": [{"properties": {"show": lit("true"), "position": lit(s("Top"))}}]})
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
          objects=data_labels())
    p.add("pivotTable", 560, 90, 696, 200,
          roles={"Rows": [col("DIM_SELLER", "seller_region")],
                 "Columns": [col("DIM_CUSTOMER", "customer_region")],
                 "Values": [mea("Late Delivery %")]},
          title="Late rate by lane: seller region (rows) to customer region (columns)")
    p.add("scatterChart", 560, 310, 696, 200,
          roles={"Category": [col("DIM_CUSTOMER", "customer_state")],
                 "X": [mea("Freight % of GMV")],
                 "Y": [mea("Late Delivery % (min 100 orders)")],
                 "Size": [mea("Orders")]},
          title="Freight share vs late rate by state (bubble size = orders): the Northeast pays more and waits longer",
          objects={"categoryLabels": [{"properties": {"show": lit("true")}}]})
    p.add("clusteredBarChart", 20, 526, 400, 176,
          roles={"Category": [col("DIM_PRODUCT", "weight_band")],
                 "Y": [mea("Late Delivery % (Items)")],
                 "Tooltips": [mea("Items Sold")]},
          title="Heavier items arrive late more often: 15 kg+ at 10.1% vs 6.2% under 1 kg",
          objects=data_labels())
    p.add("tableEx", 440, 526, 816, 176,
          roles={"Values": [col("DIM_PRODUCT", "category_label"), mea("Items Sold"),
                            mea("Late Delivery % (Items, min 500)"), mea("Avg Review Score (Items)"),
                            mea("Freight % of GMV (Items)")]},
          sort=(mea("Late Delivery % (Items, min 500)"), "Descending"),
          title="Categories with the highest late rate (500+ items sold); scroll for the full list",
          objects={"total": [{"properties": {"totals": lit("false")}}]})
    pages.append(p)

    # ---------------------------------------------------------------- page 4
    p = Page("p4_recommendations", "Recommendations")
    textbox(p, 20, 12, 760, 70, [[("What to do first", H1)],
                                 [("Three actions in order, and a what-if on how much satisfaction they buy back", SUB)]])
    slicer(p, 800, 16, 216, 58, col("DIM_CUSTOMER", "customer_region"), "Customer region")
    slicer(p, 1040, 16, 216, 58, col("DIM_CUSTOMER", "customer_state"), "Customer state")
    slicer(p, 20, 90, 300, 84, col("Late Reduction %", "Late Reduction %"), "Late deliveries cut by (%)",
           mode="Single")
    for i, m in enumerate(["Late Orders", "Scenario Late Orders Fixed", "Scenario Avg Review Score",
                           "Scenario Uplift", "Scenario Low Reviews Avoided"]):
        card(p, 340 + i * 186, 90, 174, 84, m, label_size=22)
    p.add("scatterChart", 20, 190, 400, 320,
          roles={"Category": [col("Recommendations", "No")],
                 "X": [mea("Effort (1-5)", "Recommendations")],
                 "Y": [mea("Impact (1-5)", "Recommendations")]},
          title="Impact vs effort by action number: start top-left",
          objects={"categoryLabels": [{"properties": {"show": lit("true")}}]})
    p.add("tableEx", 440, 190, 816, 320,
          roles={"Values": [col("Recommendations", "No"), col("Recommendations", "Action"),
                            col("Recommendations", "Target"), col("Recommendations", "Effort"),
                            col("Recommendations", "Impact")]},
          sort=(col("Recommendations", "No"), "Ascending"),
          title="Recommended actions, targets and effort",
          objects={"total": [{"properties": {"totals": lit("false")}}]})
    p.add("clusteredBarChart", 20, 526, 1236, 176,
          roles={"Category": [col("DIM_CUSTOMER", "customer_state")],
                 "Y": [mea("Scenario Low Reviews Avoided")],
                 "Tooltips": [mea("Late Orders"), mea("Scenario Avg Review Score")]},
          sort=(mea("Scenario Low Reviews Avoided"), "Descending"),
          title_measure="Title | Scenario",
          objects=data_labels())
    pages.append(p)

    # ---------------------------------------------------------------- page 5
    p = Page("p5_appendix", "Appendix: Model & Data Quality")
    textbox(p, 20, 12, 1236, 70, [[("Under the hood", H1)],
                                  [("Snowflake model, business rules, data quality checks and the measure dictionary", SUB)]])
    textbox(p, 20, 90, 600, 612, [
        [("Architecture", BODYB)],
        [("9 Kaggle CSVs land in OLIST.RAW (one table per file, all VARCHAR, replayable). OLIST.STG views type, rename and "
          "deduplicate to one row per business key (one review per order, payments aggregated to the order). OLIST.MARTS is a "
          "star schema materialized as tables: DIM_DATE, DIM_CUSTOMER (grain: customer_unique_id), DIM_SELLER, DIM_PRODUCT, "
          "FCT_ORDERS (grain: order) and FCT_ORDER_ITEMS (grain: item). A Snowflake SEMANTIC VIEW (SV_ORDERS) defines the "
          "KPIs once; the DAX measures mirror it name for name.", BODY)],
        [("Business rules", BODYB)],
        [("Delivered = status 'delivered' with a customer delivery timestamp. Late = delivered after the estimated date "
          "(calendar days). Low review = score 1 or 2. Interstate = primary seller state differs from customer state. "
          "Analysis window = orders purchased Jan 2017 to Aug 2018 (edges of the dataset are sparse); applied in the "
          "Power Query partitions of both facts.", BODY)],
        [("Data quality checks (sql/90_checks.sql)", BODYB)],
        [("Unique keys in every mart; row counts RAW = STG = MARTS; GMV reconciled to the cent (R$ 13,591,643.70) across "
          "RAW, FCT_ORDERS and FCT_ORDER_ITEMS; zero orphan keys; 775 canceled/unavailable orders without items kept and "
          "documented; review duplicates resolved to the latest answer per order; geolocation averaged per zip prefix "
          "inside the Brazil bounding box.", BODY)],
        [("Governance", BODYB)],
        [("Power BI connects in Import mode with the read-only role BI_READER, which can only see OLIST.MARTS. Naming follows "
          "dbt conventions (stg_, dim_, fct_). The report is saved as a Power BI Project (PBIP: TMDL + PBIR) and versioned "
          "in Git. Comment themes come from rule-based SQL because Cortex AI functions are not enabled on trial accounts; "
          "the Cortex version is written and ready for production.", BODY)],
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
        [("Full definitions: case-dataart/powerbi/measures.md and sql/40_semantic.sql.", NOTE)],
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
    bg = BRANDING / BACKGROUND
    if not bg.exists():
        raise SystemExit(f"missing {bg}: run branding/make_backgrounds.py first")
    shutil.copyfile(bg, RP / "StaticResources" / "RegisteredResources" / BACKGROUND)
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
             "items": [{"name": "OlistTheme.json", "path": "OlistTheme.json", "type": "CustomTheme"},
                       {"name": BACKGROUND, "path": BACKGROUND, "type": "Image"}]},
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
            "displayOption": "FitToPage",
            "height": PAGE_H,
            "width": PAGE_W,
            "objects": {
                "background": [{"properties": {
                    "image": {"image": {
                        "name": lit(s(BACKGROUND)),
                        "url": {"expr": {"ResourcePackageItem": {
                            "PackageName": "RegisteredResources", "PackageType": 1, "ItemName": BACKGROUND}}},
                        "scaling": lit(s("Fit")),
                    }},
                    "transparency": lit("0D"),
                }}],
            },
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
