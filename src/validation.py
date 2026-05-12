from __future__ import annotations

import pandas as pd


def make_time_series_folds(
    dates: pd.Series,
    validation_size: int,
    n_folds: int,
    gap: int = 0,
) -> list[dict[str, pd.Timestamp]]:
    """Создает последовательные окна валидации без перемешивания дат."""
    unique_dates = pd.Series(pd.to_datetime(dates).drop_duplicates()).sort_values().reset_index(drop=True)
    min_required = validation_size * n_folds + gap
    if len(unique_dates) <= min_required:
        raise ValueError("Недостаточно дат для заданной схемы валидации.")

    folds: list[dict[str, pd.Timestamp]] = []
    last_index = len(unique_dates) - 1

    for fold_number in range(n_folds, 0, -1):
        valid_end_index = last_index - validation_size * (n_folds - fold_number)
        valid_start_index = valid_end_index - validation_size + 1
        train_end_index = valid_start_index - gap - 1
        if train_end_index < 0:
            raise ValueError("Недостаточно истории для обучения.")
        folds.append(
            {
                "train_start": unique_dates.iloc[0],
                "train_end": unique_dates.iloc[train_end_index],
                "valid_start": unique_dates.iloc[valid_start_index],
                "valid_end": unique_dates.iloc[valid_end_index],
            }
        )

    return folds


def split_by_fold(frame: pd.DataFrame, fold: dict[str, pd.Timestamp], date_column: str = "date"):
    dates = pd.to_datetime(frame[date_column])
    train_mask = (dates >= fold["train_start"]) & (dates <= fold["train_end"])
    valid_mask = (dates >= fold["valid_start"]) & (dates <= fold["valid_end"])
    return frame.loc[train_mask].copy(), frame.loc[valid_mask].copy()

