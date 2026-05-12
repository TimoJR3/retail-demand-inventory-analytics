from __future__ import annotations

import numpy as np
import pandas as pd


KEY_COLUMNS = ["stock_code", "market_id"]
DATE_COLUMN = "sales_date"
TARGET_COLUMN = "net_sales_qty"
REQUIRED_FEATURE_COLUMNS = [
    "sales_date",
    "stock_code",
    "market_id",
    "net_sales_qty",
    "avg_unit_price",
    "invoices_cnt",
    "customers_cnt",
]


def _validate_required_columns(df: pd.DataFrame, required_columns: list[str] | None = None) -> None:
    required = required_columns or REQUIRED_FEATURE_COLUMNS
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError("Для построения признаков не хватает колонок: " + ", ".join(missing))


def _sort_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result[DATE_COLUMN] = pd.to_datetime(result[DATE_COLUMN])
    return result.sort_values(KEY_COLUMNS + [DATE_COLUMN]).reset_index(drop=True)


def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет лаги спроса внутри пары товар-рынок без использования будущих продаж."""
    _validate_required_columns(df)
    result = _sort_feature_frame(df)
    grouped = result.groupby(KEY_COLUMNS, sort=False)

    for lag in (7, 14, 28):
        result[f"lag_{lag}"] = grouped[TARGET_COLUMN].shift(lag)

    result["invoices_cnt_lag_7"] = grouped["invoices_cnt"].shift(7)
    result["customers_cnt_lag_7"] = grouped["customers_cnt"].shift(7)
    return result


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет скользящие признаки, рассчитанные только по прошлым дням."""
    _validate_required_columns(df)
    result = _sort_feature_frame(df)
    grouped = result.groupby(KEY_COLUMNS, sort=False)[TARGET_COLUMN]

    result["rolling_mean_7"] = grouped.transform(lambda values: values.shift(1).rolling(7, min_periods=1).mean())
    result["rolling_mean_28"] = grouped.transform(lambda values: values.shift(1).rolling(28, min_periods=1).mean())
    result["rolling_std_28"] = grouped.transform(lambda values: values.shift(1).rolling(28, min_periods=2).std())
    result["rolling_median_28"] = grouped.transform(lambda values: values.shift(1).rolling(28, min_periods=1).median())
    return result


def add_price_features(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет лаг цены и изменение цены относительно значения 7 дней назад."""
    _validate_required_columns(df)
    result = _sort_feature_frame(df)
    grouped = result.groupby(KEY_COLUMNS, sort=False)

    result["avg_unit_price_lag_7"] = grouped["avg_unit_price"].shift(7)
    result["price_change_abs"] = result["avg_unit_price"] - result["avg_unit_price_lag_7"]
    result["price_change_pct"] = np.where(
        result["avg_unit_price_lag_7"].abs() > 0,
        result["price_change_abs"] / result["avg_unit_price_lag_7"],
        np.nan,
    )
    return result


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет календарные признаки из даты продажи."""
    _validate_required_columns(df, ["sales_date"])
    result = df.copy()
    dates = pd.to_datetime(result[DATE_COLUMN])
    result["weekday"] = dates.dt.dayofweek
    result["month"] = dates.dt.month
    result["year"] = dates.dt.year
    result["is_weekend"] = result["weekday"].isin([5, 6]).astype(int)
    return result


def add_zero_sales_features(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет признаки паузы в продажах, используя только историю до текущего дня."""
    _validate_required_columns(df)
    result = _sort_feature_frame(df)
    result["days_since_last_sale"] = np.nan
    result["zero_sales_streak"] = 0

    for _, index in result.groupby(KEY_COLUMNS, sort=False).groups.items():
        last_sale_date = None
        zero_streak = 0
        for row_index in index:
            current_date = result.at[row_index, DATE_COLUMN]
            current_sales = result.at[row_index, TARGET_COLUMN]

            if last_sale_date is not None:
                result.at[row_index, "days_since_last_sale"] = (current_date - last_sale_date).days
            result.at[row_index, "zero_sales_streak"] = zero_streak

            if pd.notna(current_sales) and current_sales > 0:
                last_sale_date = current_date
                zero_streak = 0
            else:
                zero_streak += 1

    return result


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Собирает полный набор признаков для витрины sales_date x stock_code x market_id."""
    _validate_required_columns(df)
    result = _sort_feature_frame(df)
    result = add_calendar_features(result)
    result = add_lag_features(result)
    result = add_rolling_features(result)
    result = add_price_features(result)
    result = add_zero_sales_features(result)
    return result


def add_lag_rolling_features(
    frame: pd.DataFrame,
    group_columns: list[str] | None = None,
    target_column: str = TARGET_COLUMN,
    lags: tuple[int, ...] = (7, 14, 28),
    windows: tuple[int, ...] = (7, 28),
) -> pd.DataFrame:
    """Совместимый helper для старых ноутбуков: добавляет лаги и rolling без будущих значений."""
    group_columns = group_columns or KEY_COLUMNS
    date_column = DATE_COLUMN if DATE_COLUMN in frame.columns else "date"
    result = frame.copy()
    result[date_column] = pd.to_datetime(result[date_column])
    result = result.sort_values(group_columns + [date_column]).reset_index(drop=True)
    grouped = result.groupby(group_columns, sort=False)[target_column]

    for lag in lags:
        result[f"lag_{lag}"] = grouped.shift(lag)
    for window in windows:
        result[f"rolling_mean_{window}"] = grouped.transform(
            lambda values: values.shift(1).rolling(window=window, min_periods=1).mean()
        )
    return result
