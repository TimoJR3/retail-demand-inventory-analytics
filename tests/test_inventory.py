import pandas as pd
import pytest

from src.inventory import (
    estimate_reorder_point,
    estimate_safety_stock,
    excess_stock_proxy,
    inventory_policy_table,
    stockout_risk_proxy,
)


def sample_forecast_actual() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sales_date": pd.date_range("2024-01-01", periods=4).tolist()
            + pd.date_range("2024-01-01", periods=4).tolist(),
            "stock_code": ["A", "A", "A", "A", "B", "B", "B", "B"],
            "market_id": ["UK", "UK", "UK", "UK", "FR", "FR", "FR", "FR"],
            "net_sales_qty": [10, 15, 0, -2, 1, 1, 1, 1],
            "forecast_net_sales_qty": [8, 20, 0, 3, 2, 2, 2, 2],
        }
    )


def test_safety_stock_is_calculated_correctly():
    result = estimate_safety_stock(demand_std=4, lead_time_days=9, z_score=1.5)
    assert result == 18


def test_reorder_point_formula():
    result = estimate_reorder_point(avg_daily_demand=10, lead_time_days=7, safety_stock=5)
    assert result == 75


def test_stockout_risk_proxy_marks_risk():
    result = stockout_risk_proxy(
        actual_sales=pd.Series([10, 5, 0]),
        forecast_sales=pd.Series([8, 5, 1]),
        available_stock_assumption=pd.Series([8, 6, 1]),
    )
    assert result.tolist() == [True, False, False]


def test_excess_stock_proxy_marks_overstock_risk():
    result = excess_stock_proxy(
        forecast_sales=pd.Series([12, 5, 0]),
        actual_sales=pd.Series([10, 5, 0]),
    )
    assert result.tolist() == [True, False, False]


def test_inventory_policy_table_creates_required_columns():
    result = inventory_policy_table(sample_forecast_actual(), lead_time_days=7)
    required_columns = {
        "stock_code",
        "market_id",
        "avg_daily_demand",
        "demand_std",
        "forecast_error",
        "forecast_bias",
        "stockout_risk_flag",
        "overstock_risk_flag",
        "suggested_reorder_point",
        "suggested_safety_stock",
    }
    assert required_columns.issubset(result.columns)


def test_zero_demand_does_not_break_calculations():
    frame = pd.DataFrame(
        {
            "sales_date": pd.date_range("2024-01-01", periods=3),
            "stock_code": ["Z", "Z", "Z"],
            "market_id": ["UK", "UK", "UK"],
            "net_sales_qty": [0, 0, 0],
            "forecast_net_sales_qty": [0, 1, 0],
        }
    )
    result = inventory_policy_table(frame, lead_time_days=7)
    assert len(result) == 1
    assert result.loc[0, "avg_daily_demand"] == 0
    assert result.loc[0, "suggested_reorder_point"] >= 0


def test_negative_lead_time_days_raises_clear_error():
    with pytest.raises(ValueError, match="lead_time_days"):
        estimate_safety_stock(demand_std=1, lead_time_days=-1, z_score=1.65)

    with pytest.raises(ValueError, match="lead_time_days"):
        inventory_policy_table(sample_forecast_actual(), lead_time_days=-1)
