import numpy as np

from src.metrics import forecast_bias, mae, rmse, service_level_proxy, stockout_risk_rate, wmape


def test_mae_for_simple_arrays():
    assert mae([100, 200, 300], [90, 220, 330]) == 20


def test_rmse_for_simple_arrays():
    actual = [100, 200, 300]
    forecast = [90, 220, 330]
    assert round(rmse(actual, forecast), 4) == round(np.sqrt((100 + 400 + 900) / 3), 4)


def test_wmape_for_simple_arrays():
    assert round(wmape([100, 200, 300], [90, 220, 330]), 4) == round(60 / 600, 4)


def test_forecast_bias_shows_direction():
    assert round(forecast_bias([100, 200, 300], [90, 220, 330]), 4) == round(40 / 600, 4)
    assert forecast_bias([100, 100], [80, 90]) < 0


def test_metrics_are_stable_when_actual_sales_are_zero():
    assert wmape([0, 0], [0, 0]) == 0
    assert wmape([0, 0], [1, 2]) == 1
    assert forecast_bias([0, 0], [0, 0]) == 0
    assert forecast_bias([0, 0], [1, 2]) == 1


def test_service_level_proxy():
    assert service_level_proxy([10, 20, 30], [10, 18, 35]) == 2 / 3


def test_stockout_risk_rate():
    assert stockout_risk_rate([10, 20, 30], [10, 18, 25], threshold=2) == 1 / 3

