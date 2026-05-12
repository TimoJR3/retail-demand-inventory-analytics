from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
RESULTS_DIR = PROJECT_ROOT / "results"

RAW_FILE_CANDIDATES = [
    RAW_DATA_DIR / "online_retail_II.xlsx",
    RAW_DATA_DIR / "online_retail.xlsx",
    RAW_DATA_DIR / "online_retail_II.csv",
    RAW_DATA_DIR / "online_retail.csv",
]

# Алиас оставлен для старых ноутбуков проекта.
RAW_DATA_CANDIDATES = RAW_FILE_CANDIDATES

REQUIRED_COLUMNS = [
    "invoice",
    "stock_code",
    "description",
    "quantity",
    "invoice_date",
    "unit_price",
    "customer_id",
    "country",
]

MART_KEYS = ["sales_date", "stock_code", "market_id"]
TARGET_COLUMN = "net_sales_qty"
