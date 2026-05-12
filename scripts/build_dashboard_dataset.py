from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"

FORECAST_FILE = RESULTS_DIR / "forecast_vs_actual_sample.csv"
SEGMENTS_FILE = RESULTS_DIR / "abc_xyz_segments.csv"
INVENTORY_FILE = RESULTS_DIR / "inventory_risk_table.csv"
OUTPUT_FILE = RESULTS_DIR / "dashboard_forecast_inventory.csv"

FINAL_COLUMNS = [
    "sales_date",
    "stock_code",
    "description",
    "market_id",
    "abc_segment",
    "xyz_segment",
    "abc_xyz_segment",
    "actual_sales",
    "forecast_sales",
    "forecast_error",
    "abs_forecast_error",
    "wmape",
    "mae",
    "rmse",
    "bias",
    "revenue",
    "stockout_risk_flag",
    "overstock_risk_flag",
    "suggested_reorder_point",
    "suggested_safety_stock",
]

COLUMN_ALIASES = {
    "date": "sales_date",
    "actual": "actual_sales",
    "actual_qty": "actual_sales",
    "net_sales_qty": "actual_sales",
    "sales": "actual_sales",
    "forecast": "forecast_sales",
    "forecast_qty": "forecast_sales",
    "forecast_net_sales_qty": "forecast_sales",
    "model_forecast": "forecast_sales",
    "forecast_bias": "bias",
    "stockout_flag": "stockout_risk_flag",
    "overstock_flag": "overstock_risk_flag",
    "reorder_point": "suggested_reorder_point",
    "safety_stock": "suggested_safety_stock",
}


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Приводит названия колонок к ожидаемому формату dashboard-датасета."""
    result = frame.copy()
    normalized_columns = []
    for column in result.columns:
        normalized = str(column).strip().lower().replace("-", "_").replace(" ", "_")
        normalized_columns.append(COLUMN_ALIASES.get(normalized, normalized))
    result.columns = normalized_columns
    return result


def require_files(paths: list[Path]) -> None:
    """Проверяет наличие входных файлов и показывает понятное сообщение."""
    missing = [path for path in paths if not path.exists()]
    if missing:
        details = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Не найдены входные файлы для dashboard-датасета. "
            "Сначала запустите ноутбуки 02, 04 и 05.\n"
            f"Отсутствуют:\n{details}"
        )


def require_columns(frame: pd.DataFrame, required_columns: list[str], source_name: str) -> None:
    """Проверяет обязательные колонки в конкретном источнике."""
    missing = sorted(set(required_columns) - set(frame.columns))
    if missing:
        raise ValueError(
            f"В файле {source_name} не хватает колонок: {', '.join(missing)}. "
            "Проверьте, что предыдущий шаг проекта завершился без ошибок."
        )


def read_source(path: Path, required_columns: list[str]) -> pd.DataFrame:
    """Загружает CSV, нормализует названия и проверяет обязательные поля."""
    frame = normalize_columns(pd.read_csv(path))
    require_columns(frame, required_columns, path.name)
    return frame


def calculate_group_metrics(forecast: pd.DataFrame) -> pd.DataFrame:
    """Считает метрики прогноза на уровне stock_code x market_id."""
    rows = []
    for keys, group in forecast.groupby(["stock_code", "market_id"], sort=False):
        stock_code, market_id = keys
        actual = pd.to_numeric(group["actual_sales"], errors="coerce").fillna(0)
        predicted = pd.to_numeric(group["forecast_sales"], errors="coerce").fillna(0)
        error = actual - predicted
        abs_error = error.abs()
        actual_sum = actual.abs().sum()

        if actual_sum == 0:
            wmape = 0.0 if abs_error.sum() == 0 else 1.0
            bias = 0.0 if (predicted - actual).sum() == 0 else float(np.sign((predicted - actual).sum()))
        else:
            wmape = float(abs_error.sum() / actual_sum)
            bias = float((predicted - actual).sum() / actual_sum)

        rows.append(
            {
                "stock_code": stock_code,
                "market_id": market_id,
                "wmape": wmape,
                "mae": float(abs_error.mean()) if len(group) else 0.0,
                "rmse": float(np.sqrt(np.mean(np.square(error)))) if len(group) else 0.0,
                "bias": bias,
            }
        )
    return pd.DataFrame(rows)


def choose_inventory_source(inventory: pd.DataFrame) -> pd.DataFrame:
    """Оставляет один сценарный слой запасов на пару товар-рынок."""
    if "source" in inventory.columns:
        model_rows = inventory[inventory["source"].astype(str).str.lower().eq("model")]
        if not model_rows.empty:
            inventory = model_rows.copy()

    return (
        inventory.sort_values(["stock_code", "market_id"])
        .drop_duplicates(["stock_code", "market_id"], keep="first")
        .copy()
    )


def build_dashboard_dataset() -> pd.DataFrame:
    """Собирает единый датасет для dashboard-аналитики прогноза и запасов."""
    require_files([FORECAST_FILE, SEGMENTS_FILE, INVENTORY_FILE])

    forecast = read_source(
        FORECAST_FILE,
        ["sales_date", "stock_code", "market_id", "actual_sales", "forecast_sales"],
    )
    segments = read_source(
        SEGMENTS_FILE,
        ["stock_code", "market_id", "abc_segment", "xyz_segment", "abc_xyz_segment"],
    )
    inventory = read_source(
        INVENTORY_FILE,
        [
            "stock_code",
            "market_id",
            "stockout_risk_flag",
            "overstock_risk_flag",
            "suggested_reorder_point",
            "suggested_safety_stock",
        ],
    )

    inventory = choose_inventory_source(inventory)
    metrics = calculate_group_metrics(forecast)

    forecast["sales_date"] = pd.to_datetime(forecast["sales_date"], errors="coerce")
    forecast["actual_sales"] = pd.to_numeric(forecast["actual_sales"], errors="coerce").fillna(0)
    forecast["forecast_sales"] = pd.to_numeric(forecast["forecast_sales"], errors="coerce").fillna(0)
    forecast["forecast_error"] = forecast["actual_sales"] - forecast["forecast_sales"]
    forecast["abs_forecast_error"] = forecast["forecast_error"].abs()

    dashboard = (
        forecast.merge(segments, on=["stock_code", "market_id"], how="left", suffixes=("", "_segment"))
        .merge(inventory, on=["stock_code", "market_id"], how="left", suffixes=("", "_inventory"))
        .merge(metrics, on=["stock_code", "market_id"], how="left")
    )

    if "description" not in dashboard.columns:
        dashboard["description"] = ""
    if "revenue" not in dashboard.columns:
        dashboard["revenue"] = np.nan
    if "forecast_error_inventory" in dashboard.columns:
        dashboard["forecast_error"] = dashboard["forecast_error"].fillna(dashboard["forecast_error_inventory"])
    if "bias_inventory" in dashboard.columns:
        dashboard["bias"] = dashboard["bias"].fillna(dashboard["bias_inventory"])

    for column in FINAL_COLUMNS:
        if column not in dashboard.columns:
            dashboard[column] = np.nan

    dashboard = dashboard[FINAL_COLUMNS].sort_values(["sales_date", "stock_code", "market_id"]).reset_index(drop=True)
    if dashboard.empty:
        raise ValueError("Итоговый dashboard-датасет пустой. Проверьте входные CSV в папке results/.")
    return dashboard


def main() -> None:
    dashboard = build_dashboard_dataset()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    dashboard.to_csv(OUTPUT_FILE, index=False)
    print(f"Готово: сохранен файл {OUTPUT_FILE}")
    print(f"Строк: {len(dashboard):,}; колонок: {len(dashboard.columns):,}")


if __name__ == "__main__":
    main()
