from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.config import RESULTS_DIR


GROUP_COLUMNS = ["stock_code", "market_id"]
REQUIRED_COLUMNS = ["stock_code", "market_id", "net_sales_qty", "revenue"]


def _validate_columns(df: pd.DataFrame) -> None:
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError("Для ABC/XYZ-сегментации не хватает колонок: " + ", ".join(missing))


def add_abc_segment(df: pd.DataFrame, value_column: str = "revenue") -> pd.DataFrame:
    """Присваивает ABC-сегмент по накопленному вкладу в выручку."""
    result = df.sort_values(value_column, ascending=False).copy()
    total = result[value_column].sum()
    if total <= 0:
        result["value_share"] = 0.0
        result["cumulative_share"] = 0.0
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


def add_xyz_segment(df: pd.DataFrame, mean_column: str = "mean_net_sales_qty", std_column: str = "std_net_sales_qty") -> pd.DataFrame:
    """Присваивает XYZ-сегмент по коэффициенту вариации спроса."""
    result = df.copy()
    result["coefficient_of_variation"] = result[std_column] / result[mean_column].replace(0, np.nan)
    result["xyz_segment"] = pd.cut(
        result["coefficient_of_variation"],
        bins=[-np.inf, 0.5, 1.0, np.inf],
        labels=["X", "Y", "Z"],
    ).astype(str)
    result.loc[result["coefficient_of_variation"].isna(), "xyz_segment"] = "Z"
    return result


def build_abc_xyz_segments(
    df: pd.DataFrame,
    output_path: Path | None = None,
) -> pd.DataFrame:
    """Строит ABC/XYZ-сегментацию по товару и рынку и сохраняет результат в CSV."""
    _validate_columns(df)
    grouped = (
        df.groupby(GROUP_COLUMNS, as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            total_net_sales_qty=("net_sales_qty", "sum"),
            mean_net_sales_qty=("net_sales_qty", "mean"),
            std_net_sales_qty=("net_sales_qty", "std"),
            active_days=("net_sales_qty", "count"),
        )
        .fillna({"std_net_sales_qty": 0})
    )
    result = add_xyz_segment(add_abc_segment(grouped))
    result["abc_xyz_segment"] = result["abc_segment"] + result["xyz_segment"]
    result = result.sort_values(["abc_segment", "xyz_segment", "revenue"], ascending=[True, True, False]).reset_index(drop=True)

    destination = output_path or RESULTS_DIR / "abc_xyz_segments.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(destination, index=False)
    return result


def build_abc_xyz(daily_sales: pd.DataFrame, group_columns: list[str] | None = None) -> pd.DataFrame:
    """Совместимый helper для старых вызовов сегментации."""
    frame = daily_sales.copy()
    if "net_sales_qty" not in frame.columns and "sales" in frame.columns:
        frame["net_sales_qty"] = frame["sales"]
    if "market_id" not in frame.columns and "country" in frame.columns:
        frame["market_id"] = frame["country"]
    return build_abc_xyz_segments(frame)
