from __future__ import annotations

import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor


def train_regression_model(train: pd.DataFrame, feature_columns: list[str], target_column: str = "sales"):
    model = HistGradientBoostingRegressor(random_state=42, max_iter=200, learning_rate=0.06)
    model.fit(train[feature_columns], train[target_column])
    return model


def predict_non_negative(model, frame: pd.DataFrame, feature_columns: list[str]) -> pd.Series:
    prediction = model.predict(frame[feature_columns])
    return pd.Series(prediction, index=frame.index).clip(lower=0)

