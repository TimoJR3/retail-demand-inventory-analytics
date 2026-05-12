from __future__ import annotations

import pandas as pd


KEY_COLUMNS = ["stock_code", "market_id"]
DATE_COLUMN = "sales_date"
TARGET_COLUMN = "net_sales_qty"


def _validate_columns(df: pd.DataFrame, target_column: str = TARGET_COLUMN) -> None:
    required = [DATE_COLUMN, *KEY_COLUMNS, target_column]
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError("Для baseline-прогноза не хватает колонок: " + ", ".join(missing))


def _sort(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result[DATE_COLUMN] = pd.to_datetime(result[DATE_COLUMN])
    return result.sort_values(KEY_COLUMNS + [DATE_COLUMN]).reset_index(drop=True)


def naive_last_value(df: pd.DataFrame, target_column: str = TARGET_COLUMN) -> pd.Series:
    """Прогноз равен последнему известному значению спроса внутри товар-рынок."""
    _validate_columns(df, target_column)
    ordered = _sort(df)
    return ordered.groupby(KEY_COLUMNS, sort=False)[target_column].shift(1)


def seasonal_naive_7(df: pd.DataFrame, target_column: str = TARGET_COLUMN) -> pd.Series:
    """Прогноз равен значению спроса 7 строк назад внутри товар-рынок."""
    _validate_columns(df, target_column)
    ordered = _sort(df)
    return ordered.groupby(KEY_COLUMNS, sort=False)[target_column].shift(7)


def seasonal_naive_28(df: pd.DataFrame, target_column: str = TARGET_COLUMN) -> pd.Series:
    """Прогноз равен значению спроса 28 строк назад внутри товар-рынок."""
    _validate_columns(df, target_column)
    ordered = _sort(df)
    return ordered.groupby(KEY_COLUMNS, sort=False)[target_column].shift(28)


def moving_average_7(df: pd.DataFrame, target_column: str = TARGET_COLUMN) -> pd.Series:
    """Прогноз равен среднему за 7 прошлых значений без текущего дня."""
    _validate_columns(df, target_column)
    ordered = _sort(df)
    grouped = ordered.groupby(KEY_COLUMNS, sort=False)[target_column]
    return grouped.transform(lambda values: values.shift(1).rolling(7, min_periods=1).mean())


def moving_average_28(df: pd.DataFrame, target_column: str = TARGET_COLUMN) -> pd.Series:
    """Прогноз равен среднему за 28 прошлых значений без текущего дня."""
    _validate_columns(df, target_column)
    ordered = _sort(df)
    grouped = ordered.groupby(KEY_COLUMNS, sort=False)[target_column]
    return grouped.transform(lambda values: values.shift(1).rolling(28, min_periods=1).mean())


def median_by_weekday(df: pd.DataFrame, target_column: str = TARGET_COLUMN) -> pd.Series:
    """Прогноз равен исторической медиане спроса для того же дня недели."""
    _validate_columns(df, target_column)
    ordered = _sort(df)
    weekday = pd.to_datetime(ordered[DATE_COLUMN]).dt.dayofweek
    temp = ordered.assign(_weekday=weekday)
    return temp.groupby([*KEY_COLUMNS, "_weekday"], sort=False)[target_column].transform(
        lambda values: values.shift(1).expanding(min_periods=1).median()
    )


def seasonal_naive(frame: pd.DataFrame, group_columns: list[str] | None = None, target_column: str = TARGET_COLUMN, season_length: int = 7) -> pd.Series:
    """Совместимый helper: сезонный naive с произвольной длиной сезона."""
    group_columns = group_columns or KEY_COLUMNS
    date_column = DATE_COLUMN if DATE_COLUMN in frame.columns else "date"
    ordered = frame.copy()
    ordered[date_column] = pd.to_datetime(ordered[date_column])
    ordered = ordered.sort_values(group_columns + [date_column]).reset_index(drop=True)
    return ordered.groupby(group_columns, sort=False)[target_column].shift(season_length)


def moving_average_forecast(
    frame: pd.DataFrame,
    group_columns: list[str] | None = None,
    target_column: str = TARGET_COLUMN,
    window: int = 28,
) -> pd.Series:
    """Совместимый helper: скользящее среднее только по прошлым значениям."""
    group_columns = group_columns or KEY_COLUMNS
    date_column = DATE_COLUMN if DATE_COLUMN in frame.columns else "date"
    ordered = frame.copy()
    ordered[date_column] = pd.to_datetime(ordered[date_column])
    ordered = ordered.sort_values(group_columns + [date_column]).reset_index(drop=True)
    grouped = ordered.groupby(group_columns, sort=False)[target_column]
    return grouped.transform(lambda values: values.shift(1).rolling(window=window, min_periods=1).mean())
