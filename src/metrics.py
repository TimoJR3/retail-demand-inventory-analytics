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
    """Считает среднюю абсолютную ошибку прогноза."""
    actual, forecast = _to_arrays(y_true, y_pred)
    if actual.size == 0:
        return 0.0
    return float(np.mean(np.abs(actual - forecast)))


def rmse(y_true, y_pred) -> float:
    """Считает корень из средней квадратичной ошибки прогноза."""
    actual, forecast = _to_arrays(y_true, y_pred)
    if actual.size == 0:
        return 0.0
    return float(np.sqrt(np.mean((actual - forecast) ** 2)))


def wmape(y_true, y_pred) -> float:
    """Считает WMAPE, основную метрику проекта для спроса с частыми нулевыми продажами."""
    actual, forecast = _to_arrays(y_true, y_pred)
    numerator = np.sum(np.abs(actual - forecast))
    denominator = np.sum(np.abs(actual))
    if denominator == 0:
        return 0.0 if numerator == 0 else 1.0
    return float(numerator / denominator)


def forecast_bias(y_true, y_pred) -> float:
    """Показывает систематическое завышение или занижение прогноза."""
    actual, forecast = _to_arrays(y_true, y_pred)
    bias_sum = np.sum(forecast - actual)
    denominator = np.sum(np.abs(actual))
    if denominator == 0:
        if bias_sum == 0:
            return 0.0
        return float(np.sign(bias_sum))
    return float(bias_sum / denominator)


def service_level_proxy(y_true, y_pred) -> float:
    """Оценивает долю строк, где прогноз покрывает фактический спрос."""
    actual, forecast = _to_arrays(y_true, y_pred)
    if actual.size == 0:
        return 0.0
    return float(np.mean(forecast >= actual))


def stockout_risk_rate(y_true, y_pred, threshold: float = 0.0) -> float:
    """Считает долю строк, где недопрогноз превышает заданный порог."""
    actual, forecast = _to_arrays(y_true, y_pred)
    if actual.size == 0:
        return 0.0
    return float(np.mean((actual - forecast) > threshold))


def metrics_table(y_true, y_pred) -> pd.DataFrame:
    """Возвращает таблицу метрик качества прогноза."""
    return pd.DataFrame(
        [
            {"metric": "wmape", "value": wmape(y_true, y_pred)},
            {"metric": "mae", "value": mae(y_true, y_pred)},
            {"metric": "rmse", "value": rmse(y_true, y_pred)},
            {"metric": "bias", "value": forecast_bias(y_true, y_pred)},
            {"metric": "service_level_proxy", "value": service_level_proxy(y_true, y_pred)},
            {"metric": "stockout_risk_rate", "value": stockout_risk_rate(y_true, y_pred, threshold=0)},
        ]
    )
