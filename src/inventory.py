from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


KEY_COLUMNS = ["stock_code", "market_id"]
DATE_COLUMN = "sales_date"
TARGET_COLUMN = "net_sales_qty"
FORECAST_COLUMN = "forecast_net_sales_qty"


def _as_array(values) -> np.ndarray:
    return np.asarray(values, dtype=float)


def _return_like_input(original, values: np.ndarray):
    if isinstance(original, pd.Series):
        return pd.Series(values, index=original.index)
    if np.isscalar(original):
        array = np.asarray(values)
        if array.dtype == bool:
            return bool(array)
        return float(array)
    return values


def _validate_non_negative(name: str, values) -> None:
    array = _as_array(values)
    if np.any(array < 0):
        raise ValueError(f"{name} не должен быть отрицательным.")


def estimate_safety_stock(demand_std, lead_time_days: int = 7, z_score: float = 1.65):
    """Считает сценарный страховой запас по стандартному отклонению спроса."""
    if lead_time_days < 0:
        raise ValueError("lead_time_days не должен быть отрицательным.")
    if z_score < 0:
        raise ValueError("z_score не должен быть отрицательным.")
    _validate_non_negative("demand_std", demand_std)

    result = _as_array(demand_std) * np.sqrt(lead_time_days) * z_score
    return _return_like_input(demand_std, result)


def estimate_reorder_point(avg_daily_demand, lead_time_days: int = 7, safety_stock=0):
    """Считает сценарную точку повторного заказа."""
    if lead_time_days < 0:
        raise ValueError("lead_time_days не должен быть отрицательным.")
    _validate_non_negative("avg_daily_demand", avg_daily_demand)
    _validate_non_negative("safety_stock", safety_stock)

    result = _as_array(avg_daily_demand) * lead_time_days + _as_array(safety_stock)
    return _return_like_input(avg_daily_demand, result)


def stockout_risk_proxy(actual_sales, forecast_sales, available_stock_assumption):
    """Помечает сценарный риск дефицита, если спрос выше условно доступного запаса."""
    _validate_non_negative("available_stock_assumption", available_stock_assumption)
    actual = np.clip(_as_array(actual_sales), a_min=0, a_max=None)
    forecast = np.clip(_as_array(forecast_sales), a_min=0, a_max=None)
    available_stock = _as_array(available_stock_assumption)
    result = (actual > available_stock) | (actual > forecast)
    return _return_like_input(actual_sales, result.astype(bool))


def excess_stock_proxy(forecast_sales, actual_sales):
    """Помечает сценарный риск избыточного запаса при заметном завышении прогноза."""
    actual = np.clip(_as_array(actual_sales), a_min=0, a_max=None)
    forecast = np.clip(_as_array(forecast_sales), a_min=0, a_max=None)
    result = forecast > actual
    return _return_like_input(forecast_sales, result.astype(bool))


def _required_columns(df: pd.DataFrame) -> None:
    required = {DATE_COLUMN, *KEY_COLUMNS, TARGET_COLUMN, FORECAST_COLUMN}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError("Для сценарного расчета запасов не хватает колонок: " + ", ".join(missing))


def _wmape(actual: pd.Series, forecast: pd.Series) -> float:
    denominator = actual.abs().sum()
    numerator = (actual - forecast).abs().sum()
    if denominator == 0:
        return 0.0 if numerator == 0 else 1.0
    return float(numerator / denominator)


def _bias(actual: pd.Series, forecast: pd.Series) -> float:
    denominator = actual.abs().sum()
    numerator = (forecast - actual).sum()
    if denominator == 0:
        if numerator == 0:
            return 0.0
        return float(np.sign(numerator))
    return float(numerator / denominator)


def inventory_policy_table(
    df: pd.DataFrame,
    lead_time_days: int = 7,
    z_score: float = 1.65,
    available_stock_multiplier: float = 1.0,
) -> pd.DataFrame:
    """Строит сценарную таблицу правил запасов без фактических складских остатков."""
    if lead_time_days < 0:
        raise ValueError("lead_time_days не должен быть отрицательным.")
    if available_stock_multiplier < 0:
        raise ValueError("available_stock_multiplier не должен быть отрицательным.")
    _required_columns(df)

    frame = df.copy()
    frame[DATE_COLUMN] = pd.to_datetime(frame[DATE_COLUMN])
    frame[TARGET_COLUMN] = pd.to_numeric(frame[TARGET_COLUMN], errors="coerce")
    frame[FORECAST_COLUMN] = pd.to_numeric(frame[FORECAST_COLUMN], errors="coerce")
    frame = frame.dropna(subset=[DATE_COLUMN, TARGET_COLUMN, FORECAST_COLUMN, *KEY_COLUMNS])
    if frame.empty:
        raise ValueError("После очистки входная таблица для сценарного расчета пуста.")

    frame["actual_demand_for_policy"] = frame[TARGET_COLUMN].clip(lower=0)
    frame["forecast_demand_for_policy"] = frame[FORECAST_COLUMN].clip(lower=0)
    frame["negative_actual_sales_flag"] = frame[TARGET_COLUMN] < 0
    frame["available_stock_assumption"] = frame["forecast_demand_for_policy"] * available_stock_multiplier
    frame["stockout_risk_flag"] = stockout_risk_proxy(
        frame["actual_demand_for_policy"],
        frame["forecast_demand_for_policy"],
        frame["available_stock_assumption"],
    )
    frame["overstock_risk_flag"] = excess_stock_proxy(
        frame["forecast_demand_for_policy"],
        frame["actual_demand_for_policy"],
    )

    rows: list[dict[str, Any]] = []
    for keys, group in frame.groupby(KEY_COLUMNS, sort=False):
        stock_code, market_id = keys
        avg_daily_demand = float(group["actual_demand_for_policy"].mean())
        demand_std = float(group["actual_demand_for_policy"].std(ddof=1) if len(group) > 1 else 0.0)
        if np.isnan(demand_std):
            demand_std = 0.0
        suggested_safety_stock = estimate_safety_stock(demand_std, lead_time_days, z_score)
        suggested_reorder_point = estimate_reorder_point(avg_daily_demand, lead_time_days, suggested_safety_stock)

        rows.append(
            {
                "stock_code": stock_code,
                "market_id": market_id,
                "observed_days": int(group[DATE_COLUMN].nunique()),
                "avg_daily_demand": avg_daily_demand,
                "demand_std": demand_std,
                "avg_forecast_sales": float(group["forecast_demand_for_policy"].mean()),
                "forecast_error": _wmape(group["actual_demand_for_policy"], group["forecast_demand_for_policy"]),
                "forecast_bias": _bias(group["actual_demand_for_policy"], group["forecast_demand_for_policy"]),
                "stockout_risk_rate": float(group["stockout_risk_flag"].mean()),
                "overstock_risk_rate": float(group["overstock_risk_flag"].mean()),
                "stockout_risk_flag": bool(group["stockout_risk_flag"].any()),
                "overstock_risk_flag": bool(group["overstock_risk_flag"].any()),
                "negative_actual_sales_count": int(group["negative_actual_sales_flag"].sum()),
                "lead_time_days": lead_time_days,
                "z_score": z_score,
                "available_stock_assumption": float(group["available_stock_assumption"].mean()),
                "suggested_safety_stock": suggested_safety_stock,
                "suggested_reorder_point": suggested_reorder_point,
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["stockout_risk_rate", "overstock_risk_rate", "forecast_error"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


SERVICE_LEVEL_Z = {0.90: 1.28, 0.95: 1.65, 0.98: 2.05}


def safety_stock(demand_std, lead_time_days: int, service_level: float = 0.95):
    """Совместимый helper для старых вызовов расчета safety stock."""
    return estimate_safety_stock(demand_std, lead_time_days, SERVICE_LEVEL_Z.get(service_level, 1.65))


def reorder_point(mean_daily_demand, demand_std, lead_time_days: int, service_level: float = 0.95):
    """Совместимый helper для старых вызовов расчета reorder point."""
    stock = safety_stock(demand_std, lead_time_days, service_level)
    return estimate_reorder_point(mean_daily_demand, lead_time_days, stock)
