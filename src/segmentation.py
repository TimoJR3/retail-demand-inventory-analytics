from __future__ import annotations

import numpy as np
import pandas as pd


def add_abc_segment(frame: pd.DataFrame, value_column: str = "revenue") -> pd.DataFrame:
    result = frame.sort_values(value_column, ascending=False).copy()
    total = result[value_column].sum()
    if total == 0:
        result["abc_segment"] = "C"
        return result

    result["value_share"] = result[value_column] / total
    result["cumulative_share"] = result["value_share"].cumsum()
    previous_share = result["cumulative_share"] - result["value_share"]
    result["abc_segment"] = np.select(
        [previous_share < 0.8, previous_share < 0.95],
        ["A", "B"],
        default="C",
    )
    return result


def add_xyz_segment(frame: pd.DataFrame, mean_column: str = "mean_sales", std_column: str = "std_sales") -> pd.DataFrame:
    result = frame.copy()
    result["variation_coef"] = result[std_column] / result[mean_column].replace(0, np.nan)
    result["xyz_segment"] = pd.cut(
        result["variation_coef"],
        bins=[-np.inf, 0.5, 1.0, np.inf],
        labels=["X", "Y", "Z"],
    ).astype(str)
    result.loc[result["variation_coef"].isna(), "xyz_segment"] = "Z"
    return result


def build_abc_xyz(daily_sales: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    grouped = (
        daily_sales.groupby(group_columns, as_index=False)
        .agg(revenue=("revenue", "sum"), mean_sales=("sales", "mean"), std_sales=("sales", "std"))
        .fillna({"std_sales": 0})
    )
    return add_xyz_segment(add_abc_segment(grouped))
