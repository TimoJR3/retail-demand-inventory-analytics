from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.config import REQUIRED_COLUMNS


COLUMN_ALIASES = {
    "invoice": "invoice",
    "invoiceno": "invoice",
    "invoice_no": "invoice",
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


def _check_result(check: str, passed: bool, metric: Any, message: str) -> dict[str, Any]:
    return {
        "check": check,
        "passed": bool(passed),
        "metric": metric,
        "message": message,
    }


def _share(part: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(part / total, 6)


def _column_or_empty(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series(pd.NA, index=df.index)


def missing_files(paths: dict[str, Path]) -> list[Path]:
    """Возвращает список файлов, которых нет на диске."""
    return [path for path in paths.values() if not path.exists()]


def find_raw_data_file(candidates: list[Path]) -> Path:
    """Находит первый доступный файл с транзакциями из списка допустимых путей."""
    for path in candidates:
        if path.exists():
            return path
    formatted = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Положите файл с транзакциями в один из путей: {formatted}")


def normalize_single_column_name(column: str) -> str:
    """Приводит одно название колонки к техническому snake_case-формату проекта."""
    normalized = str(column).strip().lower().replace("-", "_")
    normalized = "_".join(normalized.split())
    compact = normalized.replace("_", "")
    return COLUMN_ALIASES.get(normalized, COLUMN_ALIASES.get(compact, normalized))


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Нормализует названия колонок Online Retail к единому формату проекта."""
    result = df.copy()
    result.columns = [normalize_single_column_name(column) for column in result.columns]
    return result


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Совместимый алиас для старых вызовов нормализации колонок."""
    return normalize_column_names(df)


def check_required_columns(df: pd.DataFrame) -> dict[str, Any]:
    """Проверяет наличие обязательных полей транзакционного файла."""
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        return _check_result(
            "required_columns",
            False,
            {"missing_columns": missing},
            "Не хватает обязательных колонок: " + ", ".join(missing),
        )
    return _check_result(
        "required_columns",
        True,
        {"missing_columns": []},
        "Все обязательные колонки найдены.",
    )


def assert_required_columns(df: pd.DataFrame, required_columns: set[str] | None = None, dataset_name: str = "transactions") -> None:
    """Вызывает ошибку, если в таблице нет обязательных колонок."""
    columns = sorted(set(required_columns or REQUIRED_COLUMNS) - set(df.columns))
    if columns:
        raise ValueError(f"В таблице {dataset_name} отсутствуют колонки: {', '.join(columns)}")


def check_negative_prices(df: pd.DataFrame) -> dict[str, Any]:
    """Проверяет строки с нулевой или отрицательной ценой."""
    prices = pd.to_numeric(_column_or_empty(df, "unit_price"), errors="coerce")
    invalid_count = int((prices <= 0).sum())
    missing_count = int(prices.isna().sum())
    passed = invalid_count == 0
    return _check_result(
        "negative_or_zero_prices",
        passed,
        {"invalid_price_rows": invalid_count, "missing_price_rows": missing_count},
        "Строки с нулевой или отрицательной ценой не найдены." if passed else "Есть строки с нулевой или отрицательной ценой.",
    )


def check_duplicate_transaction_rows(df: pd.DataFrame) -> dict[str, Any]:
    """Проверяет полные дубли строк транзакций."""
    duplicates_count = int(df.duplicated().sum())
    passed = duplicates_count == 0
    return _check_result(
        "duplicate_transaction_rows",
        passed,
        {"duplicates_count": duplicates_count, "duplicates_share": _share(duplicates_count, len(df))},
        "Полные дубли строк не найдены." if passed else "Найдены полные дубли строк транзакций.",
    )


def check_missing_invoice_date(df: pd.DataFrame) -> dict[str, Any]:
    """Проверяет пропуски и некорректные даты счета."""
    dates = pd.to_datetime(_column_or_empty(df, "invoice_date"), errors="coerce")
    missing_count = int(dates.isna().sum())
    passed = missing_count == 0
    return _check_result(
        "missing_invoice_date",
        passed,
        {"missing_invoice_date_count": missing_count, "missing_invoice_date_share": _share(missing_count, len(df))},
        "Пропуски в дате счета не найдены." if passed else "Есть строки без корректной даты счета.",
    )


def check_missing_stock_code(df: pd.DataFrame) -> dict[str, Any]:
    """Проверяет пропуски кода товара."""
    stock_code = df.get("stock_code")
    if stock_code is None:
        missing_count = len(df)
    else:
        missing_count = int(stock_code.isna().sum() + stock_code.astype(str).str.strip().eq("").sum())
    passed = missing_count == 0
    return _check_result(
        "missing_stock_code",
        passed,
        {"missing_stock_code_count": missing_count, "missing_stock_code_share": _share(missing_count, len(df))},
        "Пропуски кода товара не найдены." if passed else "Есть строки без кода товара.",
    )


def check_missing_prices_share(df: pd.DataFrame) -> dict[str, Any]:
    """Считает долю строк без цены."""
    prices = pd.to_numeric(_column_or_empty(df, "unit_price"), errors="coerce")
    missing_count = int(prices.isna().sum())
    missing_share = _share(missing_count, len(df))
    passed = missing_count == 0
    return _check_result(
        "missing_prices_share",
        passed,
        {"missing_prices_count": missing_count, "missing_prices_share": missing_share},
        "Пропуски цены не найдены." if passed else "Есть строки без цены, это искажает выручку и среднюю цену.",
    )


def check_returns_share(df: pd.DataFrame) -> dict[str, Any]:
    """Считает долю возвратных или отмененных операций."""
    invoice = _column_or_empty(df, "invoice").fillna("").astype(str)
    quantity = pd.to_numeric(_column_or_empty(df, "quantity"), errors="coerce")
    returns_mask = invoice.str.startswith("C", na=False) | (quantity < 0)
    returns_count = int(returns_mask.sum())
    return _check_result(
        "returns_share",
        True,
        {"returns_count": returns_count, "returns_share": _share(returns_count, len(df))},
        "Возвраты и отмененные счета посчитаны отдельно, строки не удалены молча.",
    )


def run_all_data_checks(df: pd.DataFrame) -> pd.DataFrame:
    """Запускает все проверки качества и возвращает таблицу результатов."""
    checks = [
        check_required_columns(df),
        check_negative_prices(df),
        check_duplicate_transaction_rows(df),
        check_missing_invoice_date(df),
        check_missing_stock_code(df),
        check_missing_prices_share(df),
        check_returns_share(df),
    ]
    return pd.DataFrame(checks)


def read_transactions(path: Path) -> pd.DataFrame:
    """Загружает Excel или CSV с транзакциями и нормализует названия колонок."""
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        sheets = pd.read_excel(path, sheet_name=None)
        frame = pd.concat(sheets.values(), ignore_index=True)
    elif suffix == ".csv":
        frame = pd.read_csv(path)
    else:
        raise ValueError("Поддерживаются только файлы .xlsx, .xls и .csv.")

    result = normalize_column_names(frame)
    required_check = check_required_columns(result)
    if not required_check["passed"]:
        raise ValueError(required_check["message"])
    return result


def data_quality_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Формирует сводку по типам данных, пропускам и числу уникальных значений."""
    return pd.DataFrame(
        {
            "column": df.columns,
            "dtype": [str(dtype) for dtype in df.dtypes],
            "missing_count": df.isna().sum().to_numpy(),
            "missing_share": df.isna().mean().round(6).to_numpy(),
            "unique_count": df.nunique(dropna=True).to_numpy(),
        }
    )
