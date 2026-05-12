from __future__ import annotations

import numpy as np
import pandas as pd


def _to_arrays(y_true, y_pred) -> tuple[np.ndarray, np.ndarray]:
    actual = np.asarray(y_true, dtype=float)
    forecast = np.asarray(y_pred, dtype=float)
    if actual.shape != forecast.shape:
        raise ValueError("Размеры факта и прогноза должны совпадать.")
    return actual, forecast


def mae(y_true, y_pred) -> float:
    actual, forecast = _to_arrays(y_true, y_pred)
    return float(np.mean(np.abs(actual - forecast)))


def rmse(y_true, y_pred) -> float:
    actual, forecast = _to_arrays(y_true, y_pred)
    return float(np.sqrt(np.mean((actual - forecast) ** 2)))


def wmape(y_true, y_pred) -> float:
    actual, forecast = _to_arrays(y_true, y_pred)
    denominator = np.sum(np.abs(actual))
    if denominator == 0:
        return float("nan")
    return float(np.sum(np.abs(actual - forecast)) / denominator)


def forecast_bias(y_true, y_pred) -> float:
    actual, forecast = _to_arrays(y_true, y_pred)
    denominator = np.sum(actual)
    if denominator == 0:
        return float("nan")
    return float(np.sum(forecast - actual) / denominator)


def metrics_table(y_true, y_pred) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"metric": "WMAPE", "value": wmape(y_true, y_pred)},
            {"metric": "MAE", "value": mae(y_true, y_pred)},
            {"metric": "RMSE", "value": rmse(y_true, y_pred)},
            {"metric": "Forecast bias", "value": forecast_bias(y_true, y_pred)},
        ]
    )

