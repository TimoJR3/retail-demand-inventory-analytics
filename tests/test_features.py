import pandas as pd
import pytest

from src.features import (
    add_calendar_features,
    add_lag_features,
    add_price_features,
    add_rolling_features,
    build_feature_matrix,
)


def sample_daily_sales() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    rows = []
    for stock_code, market_id, offset in [("A", "UK", 0), ("A", "FR", 100)]:
        for index, date in enumerate(dates, start=1):
            rows.append(
                {
                    "sales_date": date,
                    "stock_code": stock_code,
                    "market_id": market_id,
                    "net_sales_qty": index + offset,
                    "avg_unit_price": 10 if index <= 7 else 12,
                    "invoices_cnt": index,
                    "customers_cnt": index + 1,
                    "revenue": (index + offset) * 10,
                }
            )
    return pd.DataFrame(rows)


def test_lags_are_calculated_inside_stock_market_group():
    result = add_lag_features(sample_daily_sales())
    uk_day_8 = result[(result["stock_code"] == "A") & (result["market_id"] == "UK")].iloc[7]
    fr_day_8 = result[(result["stock_code"] == "A") & (result["market_id"] == "FR")].iloc[7]

    assert uk_day_8["lag_7"] == 1
    assert fr_day_8["lag_7"] == 101


def test_rolling_features_use_only_past_values():
    frame = sample_daily_sales().query("market_id == 'UK'").copy()
    result = add_rolling_features(frame)
    day_3 = result.iloc[2]

    assert day_3["rolling_mean_7"] == 1.5
    assert result.iloc[0]["rolling_mean_7"] != result.iloc[0]["rolling_mean_7"]


def test_price_change_pct_is_correct():
    frame = sample_daily_sales().query("market_id == 'UK'").copy()
    result = add_price_features(frame)
    day_8 = result.iloc[7]

    assert day_8["avg_unit_price_lag_7"] == 10
    assert day_8["price_change_abs"] == 2
    assert round(day_8["price_change_pct"], 4) == 0.2


def test_calendar_features_are_created():
    result = add_calendar_features(sample_daily_sales())

    assert {"weekday", "month", "year", "is_weekend"}.issubset(result.columns)
    assert result.loc[0, "month"] == 1
    assert result.loc[0, "year"] == 2024


def test_missing_required_columns_raise_clear_error():
    with pytest.raises(ValueError, match="не хватает колонок"):
        build_feature_matrix(pd.DataFrame({"sales_date": pd.date_range("2024-01-01", periods=2)}))

