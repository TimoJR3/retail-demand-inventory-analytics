import re

import pandas as pd

from src.segmentation import build_abc_xyz_segments


def sample_segments_source() -> pd.DataFrame:
    rows = []
    for stock_code, market_id, revenue, sales_values in [
        ("A", "UK", 1000, [10, 10, 10, 10]),
        ("B", "UK", 150, [5, 8, 4, 9]),
        ("C", "UK", 50, [1, 20, 0, 30]),
    ]:
        for index, sales in enumerate(sales_values):
            rows.append(
                {
                    "sales_date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=index),
                    "stock_code": stock_code,
                    "market_id": market_id,
                    "net_sales_qty": sales,
                    "revenue": revenue / len(sales_values),
                }
            )
    return pd.DataFrame(rows)


def test_abc_segments_are_created(tmp_path):
    result = build_abc_xyz_segments(sample_segments_source(), tmp_path / "segments.csv")
    assert set(result["abc_segment"]).issubset({"A", "B", "C"})
    assert "abc_segment" in result.columns


def test_xyz_segments_are_created(tmp_path):
    result = build_abc_xyz_segments(sample_segments_source(), tmp_path / "segments.csv")
    assert set(result["xyz_segment"]).issubset({"X", "Y", "Z"})
    assert "xyz_segment" in result.columns


def test_abc_xyz_segment_has_expected_format(tmp_path):
    result = build_abc_xyz_segments(sample_segments_source(), tmp_path / "segments.csv")
    assert result["abc_xyz_segment"].map(lambda value: bool(re.fullmatch(r"[ABC][XYZ]", value))).all()


def test_higher_revenue_gets_higher_abc_segment(tmp_path):
    result = build_abc_xyz_segments(sample_segments_source(), tmp_path / "segments.csv")
    segments = result.set_index("stock_code")["abc_segment"]
    rank = {"A": 1, "B": 2, "C": 3}

    assert rank[segments["A"]] <= rank[segments["B"]]
    assert rank[segments["B"]] <= rank[segments["C"]]

