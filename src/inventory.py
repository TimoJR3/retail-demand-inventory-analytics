from __future__ import annotations

import numpy as np
import pandas as pd


SERVICE_LEVEL_Z = {
    0.90: 1.28,
    0.95: 1.65,
    0.98: 2.05,
}


def safety_stock(demand_std: pd.Series | float, lead_time_days: int, service_level: float = 0.95):
    z_value = SERVICE_LEVEL_Z.get(service_level, 1.65)
    return z_value * np.asarray(demand_std) * np.sqrt(lead_time_days)


def reorder_point(mean_daily_demand: pd.Series | float, demand_std: pd.Series | float, lead_time_days: int, service_level: float = 0.95):
    base_demand = np.asarray(mean_daily_demand) * lead_time_days
    return base_demand + safety_stock(demand_std, lead_time_days, service_level)


def classify_stock_risk(
    frame: pd.DataFrame,
    stock_column: str = "stock_on_hand",
    reorder_column: str = "reorder_point",
) -> pd.Series:
    stock = frame[stock_column]
    reorder = frame[reorder_column]
    conditions = [
        stock <= reorder,
        stock >= reorder * 2,
    ]
    choices = ["stockout_risk", "overstock_risk"]
    return pd.Series(np.select(conditions, choices, default="normal"), index=frame.index)


def scenario_inventory_metrics(
    demand: pd.DataFrame,
    group_columns: list[str],
    lead_time_days: int = 7,
    service_level: float = 0.95,
) -> pd.DataFrame:
    grouped = (
        demand.groupby(group_columns, as_index=False)
        .agg(mean_daily_demand=("sales", "mean"), demand_std=("sales", "std"))
        .fillna({"demand_std": 0})
    )
    grouped["safety_stock"] = safety_stock(grouped["demand_std"], lead_time_days, service_level)
    grouped["reorder_point"] = reorder_point(
        grouped["mean_daily_demand"],
        grouped["demand_std"],
        lead_time_days,
        service_level,
    )
    return grouped
