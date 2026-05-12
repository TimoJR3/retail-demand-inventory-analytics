import numpy as np

from src.metrics import forecast_bias, mae, rmse, wmape


def test_metrics_for_simple_arrays():
    actual = [100, 200, 300]
    forecast = [90, 220, 330]

    assert mae(actual, forecast) == 20
    assert round(rmse(actual, forecast), 4) == round(np.sqrt((100 + 400 + 900) / 3), 4)
    assert round(wmape(actual, forecast), 4) == round(60 / 600, 4)
    assert round(forecast_bias(actual, forecast), 4) == round(40 / 600, 4)


def test_wmape_returns_nan_when_actual_sum_is_zero():
    assert np.isnan(wmape([0, 0], [1, 2]))

