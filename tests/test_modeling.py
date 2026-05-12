from pathlib import Path

import pandas as pd

from src.modeling import (
    evaluate_model,
    get_feature_columns,
    prepare_train_test,
    save_predictions,
    train_model,
)


def sample_features(days: int = 50) -> pd.DataFrame:
    rows = []
    for stock_code, market_id, offset in [("A", "UK", 0), ("B", "FR", 10)]:
        for index, date in enumerate(pd.date_range("2024-01-01", periods=days, freq="D"), start=1):
            rows.append(
                {
                    "sales_date": date,
                    "stock_code": stock_code,
                    "market_id": market_id,
                    "net_sales_qty": index + offset,
                    "avg_unit_price": 10 + index % 3,
                    "lag_7": max(index - 7, 0),
                    "rolling_mean_7": max(index - 4, 0),
                    "weekday": date.dayofweek,
                    "month": date.month,
                    "year": date.year,
                    "is_weekend": int(date.dayofweek in [5, 6]),
                }
            )
    return pd.DataFrame(rows)


def test_prepare_train_test_returns_non_empty_frames():
    train, test, feature_columns = prepare_train_test(sample_features(), holdout_days=10)

    assert not train.empty
    assert not test.empty
    assert feature_columns


def test_feature_columns_do_not_contain_target_or_date():
    feature_columns = get_feature_columns(sample_features())

    assert "net_sales_qty" not in feature_columns
    assert "sales_date" not in feature_columns


def test_train_model_returns_model_object():
    train, _, feature_columns = prepare_train_test(sample_features(), holdout_days=10)
    model = train_model(train, feature_columns)

    assert hasattr(model, "predict")


def test_evaluate_model_returns_required_metrics():
    result = evaluate_model([10, 20, 30], [11, 18, 29])

    assert {"wmape", "mae", "rmse", "bias"}.issubset(result)


def test_save_predictions_creates_csv(tmp_path: Path):
    _, test, _ = prepare_train_test(sample_features(), holdout_days=10)
    forecast = pd.Series(test["net_sales_qty"].to_numpy(), index=test.index)
    output_path = tmp_path / "forecast_vs_actual_sample.csv"

    save_predictions(test, forecast, output_path)

    assert output_path.exists()
    saved = pd.read_csv(output_path)
    assert "forecast_net_sales_qty" in saved.columns
