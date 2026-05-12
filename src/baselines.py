from __future__ import annotations

import pandas as pd


def seasonal_naive(frame: pd.DataFrame, group_columns: list[str], target_column: str = "sales", season_length: int = 7) -> pd.Series:
    ordered = frame.sort_values(group_columns + ["date"])
    return ordered.groupby(group_columns, sort=False)[target_column].shift(season_length)


def moving_average_forecast(
    frame: pd.DataFrame,
    group_columns: list[str],
    target_column: str = "sales",
    window: int = 28,
) -> pd.Series:
    ordered = frame.sort_values(group_columns + ["date"])
    grouped = ordered.groupby(group_columns, sort=False)[target_column]
    return grouped.transform(lambda series: series.shift(1).rolling(window=window, min_periods=1).mean())
