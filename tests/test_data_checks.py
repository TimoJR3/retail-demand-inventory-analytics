from pathlib import Path

import pandas as pd
import pytest

from src.data_checks import assert_required_columns, missing_files, normalize_columns


def test_missing_files_detects_absent_path(tmp_path: Path):
    paths = {"transactions": tmp_path / "online_retail.xlsx"}
    assert missing_files(paths) == [tmp_path / "online_retail.xlsx"]


def test_assert_required_columns_raises_clear_error():
    frame = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError, match="отсутствуют колонки"):
        assert_required_columns(frame, {"a", "b"}, "test_table")


def test_normalize_columns_maps_online_retail_names():
    frame = pd.DataFrame(columns=["InvoiceNo", "StockCode", "UnitPrice", "Customer ID"])
    assert list(normalize_columns(frame).columns) == ["invoice", "stock_code", "unit_price", "customer_id"]
