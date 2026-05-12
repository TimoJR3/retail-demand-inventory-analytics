from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_RAW_COLUMNS = {
    "transactions": {
        "invoice",
        "stock_code",
        "description",
        "quantity",
        "invoice_date",
        "unit_price",
        "customer_id",
        "country",
    }
}

COLUMN_ALIASES = {
    "invoice": "invoice",
    "invoiceno": "invoice",
    "stockcode": "stock_code",
    "stock_code": "stock_code",
    "description": "description",
    "quantity": "quantity",
    "invoicedate": "invoice_date",
    "invoice_date": "invoice_date",
    "price": "unit_price",
    "unitprice": "unit_price",
    "unit_price": "unit_price",
    "customerid": "customer_id",
    "customer_id": "customer_id",
    "customer id": "customer_id",
    "country": "country",
}


def missing_files(paths: dict[str, Path]) -> list[Path]:
    """Возвращает список обязательных файлов, которых нет на диске."""
    return [path for path in paths.values() if not path.exists()]


def assert_files_exist(paths: dict[str, Path]) -> None:
    missing = missing_files(paths)
    if missing:
        formatted = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Не найдены файлы с исходными данными: {formatted}")


def find_raw_data_file(candidates: list[Path]) -> Path:
    for path in candidates:
        if path.exists():
            return path
    formatted = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Положите один из файлов с транзакциями в data/raw/: {formatted}")


def normalize_column_name(column: str) -> str:
    compact = str(column).strip().lower().replace("-", "_")
    compact = "_".join(compact.split())
    lookup_key = compact.replace("_", "")
    return COLUMN_ALIASES.get(compact, COLUMN_ALIASES.get(lookup_key, compact))


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result.columns = [normalize_column_name(column) for column in result.columns]
    return result


def read_transactions(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        sheets = pd.read_excel(path, sheet_name=None)
        frame = pd.concat(sheets.values(), ignore_index=True)
    elif suffix == ".csv":
        frame = pd.read_csv(path)
    else:
        raise ValueError("Поддерживаются файлы .xlsx, .xls и .csv.")

    result = normalize_columns(frame)
    assert_required_columns(result, REQUIRED_RAW_COLUMNS["transactions"], "transactions")
    return result


def find_missing_columns(frame: pd.DataFrame, required_columns: set[str]) -> set[str]:
    return set(required_columns) - set(frame.columns)


def assert_required_columns(frame: pd.DataFrame, required_columns: set[str], dataset_name: str) -> None:
    missing = find_missing_columns(frame, required_columns)
    if missing:
        columns = ", ".join(sorted(missing))
        raise ValueError(f"В таблице {dataset_name} отсутствуют колонки: {columns}")


def data_quality_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Краткая сводка качества: тип, пропуски, доля пропусков, число уникальных."""
    return pd.DataFrame(
        {
            "column": frame.columns,
            "dtype": [str(dtype) for dtype in frame.dtypes],
            "missing_count": frame.isna().sum().to_numpy(),
            "missing_share": frame.isna().mean().to_numpy(),
            "unique_count": frame.nunique(dropna=True).to_numpy(),
        }
    )
