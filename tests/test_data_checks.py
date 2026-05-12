from pathlib import Path

import pandas as pd
import pytest

from src.data_checks import (
    assert_required_columns,
    check_duplicate_transaction_rows,
    check_missing_invoice_date,
    check_missing_prices_share,
    check_missing_stock_code,
    check_negative_prices,
    check_required_columns,
    check_returns_share,
    missing_files,
    normalize_column_names,
    run_all_data_checks,
)


def valid_transactions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "invoice": ["10001", "10002"],
            "stock_code": ["A1", "B2"],
            "description": ["Товар A", "Товар B"],
            "quantity": [2, 3],
            "invoice_date": ["2011-01-01 10:00:00", "2011-01-02 11:00:00"],
            "unit_price": [10.0, 20.0],
            "customer_id": ["1", "2"],
            "country": ["United Kingdom", "France"],
        }
    )


def test_missing_files_detects_absent_path(tmp_path: Path):
    paths = {"transactions": tmp_path / "online_retail.xlsx"}
    assert missing_files(paths) == [tmp_path / "online_retail.xlsx"]


def test_normalize_column_names_maps_online_retail_names():
    frame = pd.DataFrame(columns=["InvoiceNo", "StockCode", "UnitPrice", "Customer ID", "InvoiceDate"])
    assert list(normalize_column_names(frame).columns) == [
        "invoice",
        "stock_code",
        "unit_price",
        "customer_id",
        "invoice_date",
    ]


def test_check_required_columns_passes_for_valid_frame():
    result = check_required_columns(valid_transactions())
    assert result["passed"] is True
    assert result["metric"]["missing_columns"] == []


def test_check_required_columns_reports_missing_columns():
    result = check_required_columns(pd.DataFrame({"invoice": ["10001"]}))
    assert result["passed"] is False
    assert "stock_code" in result["metric"]["missing_columns"]


def test_assert_required_columns_raises_clear_error():
    with pytest.raises(ValueError, match="отсутствуют колонки"):
        assert_required_columns(pd.DataFrame({"invoice": ["10001"]}))


def test_check_negative_prices_reports_zero_and_negative_values():
    frame = valid_transactions()
    frame.loc[0, "unit_price"] = 0
    frame.loc[1, "unit_price"] = -1
    result = check_negative_prices(frame)
    assert result["passed"] is False
    assert result["metric"]["invalid_price_rows"] == 2


def test_check_duplicate_transaction_rows_reports_duplicates():
    frame = pd.concat([valid_transactions(), valid_transactions().iloc[[0]]], ignore_index=True)
    result = check_duplicate_transaction_rows(frame)
    assert result["passed"] is False
    assert result["metric"]["duplicates_count"] == 1


def test_check_missing_invoice_date_reports_invalid_dates():
    frame = valid_transactions()
    frame.loc[0, "invoice_date"] = None
    frame.loc[1, "invoice_date"] = "not a date"
    result = check_missing_invoice_date(frame)
    assert result["passed"] is False
    assert result["metric"]["missing_invoice_date_count"] == 2


def test_check_missing_stock_code_reports_empty_values():
    frame = valid_transactions()
    frame.loc[0, "stock_code"] = ""
    result = check_missing_stock_code(frame)
    assert result["passed"] is False
    assert result["metric"]["missing_stock_code_count"] == 1


def test_check_missing_prices_share_reports_missing_values():
    frame = valid_transactions()
    frame.loc[0, "unit_price"] = None
    result = check_missing_prices_share(frame)
    assert result["passed"] is False
    assert result["metric"]["missing_prices_count"] == 1


def test_check_returns_share_counts_cancelled_and_negative_quantity():
    frame = valid_transactions()
    frame.loc[0, "invoice"] = "C10001"
    frame.loc[1, "quantity"] = -3
    result = check_returns_share(frame)
    assert result["passed"] is True
    assert result["metric"]["returns_count"] == 2


def test_run_all_data_checks_returns_expected_columns():
    result = run_all_data_checks(valid_transactions())
    assert set(["check", "passed", "metric", "message"]).issubset(result.columns)
    assert len(result) == 7
