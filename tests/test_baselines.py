import pandas as pd

from src.baselines import (
    median_by_weekday,
    moving_average_7,
    moving_average_28,
    naive_last_value,
    seasonal_naive_7,
    seasonal_naive_28,
)


def sample_daily_sales() -> pd.DataFrame:
    rows = []
    for stock_code, market_id, multiplier in [("A", "UK", 1), ("B", "UK", 10)]:
        for index, date in enumerate(pd.date_range("2024-01-01", periods=35, freq="D"), start=1):
            rows.append(
                {
                    "sales_date": date,
                    "stock_code": stock_code,
                    "market_id": market_id,
                    "net_sales_qty": index * multiplier,
                }
            )
    return pd.DataFrame(rows)


def test_all_baselines_return_expected_length():
    frame = sample_daily_sales()
    functions = [
        naive_last_value,
        seasonal_naive_7,
        seasonal_naive_28,
        moving_average_7,
        moving_average_28,
        median_by_weekday,
    ]

    for function in functions:
        assert len(function(frame)) == len(frame)


def test_seasonal_naive_7_uses_value_7_days_ago():
    frame = sample_daily_sales().query("stock_code == 'A'").copy()
    forecast = seasonal_naive_7(frame)

    assert forecast.iloc[7] == 1
    assert forecast.iloc[8] == 2


def test_moving_average_7_uses_only_past_values():
    frame = sample_daily_sales().query("stock_code == 'A'").copy()
    forecast = moving_average_7(frame)

    assert forecast.iloc[0] != forecast.iloc[0]
    assert forecast.iloc[3] == 2
    assert forecast.iloc[7] == 4


def test_median_by_weekday_works_for_different_weekdays():
    frame = sample_daily_sales().query("stock_code == 'A'").copy()
    forecast = median_by_weekday(frame)

    assert forecast.iloc[7] == 1
    assert forecast.iloc[14] == 4.5
