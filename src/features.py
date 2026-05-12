from __future__ import annotations

import pandas as pd


def clean_transactions(
    transactions: pd.DataFrame,
    remove_returns: bool = True,
    remove_missing_customer: bool = False,
) -> pd.DataFrame:
    result = transactions.copy()
    result["invoice"] = result["invoice"].astype(str)
    result["stock_code"] = result["stock_code"].astype(str)
    result["description"] = result["description"].astype(str).str.strip()
    result["country"] = result["country"].astype(str).str.strip()
    result["invoice_date"] = pd.to_datetime(result["invoice_date"], errors="coerce")
    result["quantity"] = pd.to_numeric(result["quantity"], errors="coerce")
    result["unit_price"] = pd.to_numeric(result["unit_price"], errors="coerce")

    result = result.dropna(subset=["invoice_date", "stock_code", "quantity", "unit_price"])
    if remove_returns:
        result = result[~result["invoice"].str.startswith("C", na=False)]
        result = result[result["quantity"] > 0]
    result = result[result["unit_price"] > 0]
    if remove_missing_customer:
        result = result.dropna(subset=["customer_id"])

    result["date"] = result["invoice_date"].dt.floor("D")
    result["revenue"] = result["quantity"] * result["unit_price"]
    return result.reset_index(drop=True)


def build_daily_sales(transactions: pd.DataFrame, group_columns: list[str] | None = None) -> pd.DataFrame:
    if group_columns is None:
        group_columns = ["stock_code", "country"]

    frame = clean_transactions(transactions)
    daily = (
        frame.groupby(["date", *group_columns], as_index=False)
        .agg(
            sales=("quantity", "sum"),
            revenue=("revenue", "sum"),
            avg_unit_price=("unit_price", "mean"),
            invoices=("invoice", "nunique"),
            customers=("customer_id", "nunique"),
        )
        .sort_values(["date", *group_columns])
    )
    return daily


def add_calendar_features(frame: pd.DataFrame, date_column: str = "date") -> pd.DataFrame:
    result = frame.copy()
    dates = pd.to_datetime(result[date_column])
    result["day_of_week"] = dates.dt.dayofweek
    result["week_of_year"] = dates.dt.isocalendar().week.astype(int)
    result["month"] = dates.dt.month
    result["year"] = dates.dt.year
    result["is_weekend"] = result["day_of_week"].isin([5, 6]).astype(int)
    return result


def add_lag_rolling_features(
    frame: pd.DataFrame,
    group_columns: list[str],
    target_column: str = "sales",
    lags: tuple[int, ...] = (7, 14, 28),
    windows: tuple[int, ...] = (7, 28),
) -> pd.DataFrame:
    result = frame.sort_values(group_columns + ["date"]).copy()
    grouped = result.groupby(group_columns, sort=False)[target_column]

    for lag in lags:
        result[f"lag_{lag}"] = grouped.shift(lag)

    for window in windows:
        result[f"rolling_mean_{window}"] = grouped.transform(
            lambda series: series.shift(1).rolling(window=window, min_periods=1).mean()
        )

    return result
