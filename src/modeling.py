from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from src.config import RESULTS_DIR
from src.metrics import forecast_bias, mae, rmse, service_level_proxy, stockout_risk_rate, wmape
from src.validation import train_holdout_split


TARGET_COLUMN = "net_sales_qty"
DATE_COLUMN = "sales_date"
ID_COLUMNS = ["stock_code", "market_id"]
LEAKAGE_COLUMNS = {
    TARGET_COLUMN,
    DATE_COLUMN,
    "description",
    "sales_qty",
    "revenue",
    "returns_qty",
    "invoices_cnt",
    "customers_cnt",
    "is_return_flag",
}


def get_feature_columns(df: pd.DataFrame, target_col: str = TARGET_COLUMN, date_col: str = DATE_COLUMN) -> list[str]:
    """Возвращает числовые признаки, исключая дату, целевую переменную и поля утечки."""
    blocked = set(LEAKAGE_COLUMNS) | {target_col, date_col} | set(ID_COLUMNS)
    candidates = [column for column in df.columns if column not in blocked]
    feature_columns = [
        column
        for column in candidates
        if pd.api.types.is_numeric_dtype(df[column]) or pd.api.types.is_bool_dtype(df[column])
    ]
    if not feature_columns:
        raise ValueError("Не найдено числовых признаков для обучения модели.")
    return feature_columns


def prepare_train_test(
    df: pd.DataFrame,
    target_col: str = TARGET_COLUMN,
    date_col: str = DATE_COLUMN,
    holdout_days: int = 28,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Готовит train и holdout по последним датам временного ряда."""
    required = {target_col, date_col, *ID_COLUMNS}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError("Для подготовки train/test не хватает колонок: " + ", ".join(missing))

    frame = df.copy()
    frame[date_col] = pd.to_datetime(frame[date_col])
    frame[target_col] = pd.to_numeric(frame[target_col], errors="coerce")
    frame = frame.dropna(subset=[target_col, date_col]).sort_values([date_col, *ID_COLUMNS]).reset_index(drop=True)

    train, test = train_holdout_split(frame, date_col, holdout_days=holdout_days)
    feature_columns = get_feature_columns(frame, target_col=target_col, date_col=date_col)
    train = train.dropna(subset=[target_col]).copy()
    test = test.dropna(subset=[target_col]).copy()
    if train.empty or test.empty:
        raise ValueError("После временного разделения train или holdout оказался пустым.")
    return train, test, feature_columns


def train_model(train: pd.DataFrame, feature_columns: list[str], target_col: str = TARGET_COLUMN):
    """Обучает регрессионную модель; при отсутствии LightGBM использует scikit-learn fallback."""
    try:
        from lightgbm import LGBMRegressor

        model = LGBMRegressor(
            n_estimators=200,
            learning_rate=0.05,
            num_leaves=31,
            random_state=42,
            verbosity=-1,
        )
    except Exception:
        model = HistGradientBoostingRegressor(
            random_state=42,
            max_iter=200,
            learning_rate=0.06,
            l2_regularization=0.05,
        )

    model.fit(train[feature_columns], train[target_col])
    return model


def predict_non_negative(model, df: pd.DataFrame, feature_columns: list[str]) -> pd.Series:
    """Возвращает неотрицательный прогноз спроса."""
    forecast = model.predict(df[feature_columns])
    return pd.Series(np.asarray(forecast, dtype=float), index=df.index).clip(lower=0)


def evaluate_model(y_true, y_pred) -> dict[str, float]:
    """Считает основные метрики качества прогноза."""
    return {
        "wmape": wmape(y_true, y_pred),
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "bias": forecast_bias(y_true, y_pred),
        "service_level_proxy": service_level_proxy(y_true, y_pred),
        "stockout_risk_rate": stockout_risk_rate(y_true, y_pred, threshold=0),
    }


def compare_with_best_baseline(model_metrics: dict[str, float], baseline_metrics: pd.DataFrame | None) -> pd.DataFrame:
    """Сравнивает модель с лучшим baseline по WMAPE, если таблица baseline передана."""
    rows: list[dict[str, Any]] = [
        {
            "source": "model",
            "metric": "wmape",
            "value": model_metrics["wmape"],
        }
    ]
    if baseline_metrics is not None and not baseline_metrics.empty:
        table = baseline_metrics.copy()
        table["metric"] = table["metric"].str.lower()
        wmape_rows = table[table["metric"] == "wmape"].sort_values("value")
        if not wmape_rows.empty:
            best = wmape_rows.iloc[0]
            rows.append(
                {
                    "source": str(best.get("baseline", "best_baseline")),
                    "metric": "wmape",
                    "value": float(best["value"]),
                }
            )
    return pd.DataFrame(rows)


def save_predictions(
    df: pd.DataFrame,
    forecast: pd.Series,
    output_path: Path | None = None,
    target_col: str = TARGET_COLUMN,
) -> Path:
    """Сохраняет выборку факт-прогноз в CSV."""
    destination = output_path or RESULTS_DIR / "forecast_vs_actual_sample.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    columns = [DATE_COLUMN, *ID_COLUMNS, target_col]
    available_columns = [column for column in columns if column in df.columns]
    result = df[available_columns].copy()
    result["forecast_net_sales_qty"] = forecast.reindex(df.index).to_numpy()
    result.to_csv(destination, index=False)
    return destination


def save_model_metrics(metrics: dict[str, float], output_path: Path | None = None) -> Path:
    """Сохраняет метрики модели в CSV."""
    destination = output_path or RESULTS_DIR / "model_metrics.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([metrics]).to_csv(destination, index=False)
    return destination


def save_feature_importance(model, feature_columns: list[str], output_path: Path | None = None) -> Path | None:
    """Сохраняет важность признаков, если модель предоставляет такой атрибут."""
    importance = getattr(model, "feature_importances_", None)
    if importance is None:
        return None
    destination = output_path or RESULTS_DIR / "feature_importance.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"feature": feature_columns, "importance": importance}).sort_values(
        "importance", ascending=False
    ).to_csv(destination, index=False)
    return destination


def run_modeling_pipeline(
    features: pd.DataFrame,
    baseline_metrics: pd.DataFrame | None = None,
    holdout_days: int = 28,
) -> dict[str, Any]:
    """Запускает полный цикл: split, обучение, прогноз, метрики и сохранение результатов."""
    train, test, feature_columns = prepare_train_test(features, holdout_days=holdout_days)
    model = train_model(train, feature_columns)
    forecast = predict_non_negative(model, test, feature_columns)
    metrics = evaluate_model(test[TARGET_COLUMN], forecast)
    comparison = compare_with_best_baseline(metrics, baseline_metrics)

    save_model_metrics(metrics)
    save_predictions(test, forecast)
    feature_importance_path = save_feature_importance(model, feature_columns)
    comparison.to_csv(RESULTS_DIR / "model_vs_baseline.csv", index=False)

    return {
        "model": model,
        "train": train,
        "test": test,
        "feature_columns": feature_columns,
        "forecast": forecast,
        "metrics": metrics,
        "comparison": comparison,
        "feature_importance_path": feature_importance_path,
    }


def train_regression_model(train: pd.DataFrame, feature_columns: list[str], target_column: str = TARGET_COLUMN):
    """Совместимый helper для старых вызовов обучения."""
    return train_model(train, feature_columns, target_col=target_column)
