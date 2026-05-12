from __future__ import annotations

import pandas as pd


def _validate_date_column(df: pd.DataFrame, date_col: str) -> None:
    if date_col not in df.columns:
        raise ValueError(f"В таблице нет колонки даты: {date_col}")


def _sorted_by_date(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    result = df.copy()
    result[date_col] = pd.to_datetime(result[date_col])
    return result.sort_values(date_col).reset_index(drop=True)


def train_holdout_split(df: pd.DataFrame, date_col: str, holdout_days: int = 28) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Делит данные по времени: последние holdout_days календарных дат уходят в holdout."""
    _validate_date_column(df, date_col)
    ordered = _sorted_by_date(df, date_col)
    unique_dates = pd.Series(ordered[date_col].drop_duplicates()).sort_values().reset_index(drop=True)
    if len(unique_dates) <= holdout_days:
        raise ValueError("Недостаточно дат для выделения holdout-периода.")

    holdout_dates = set(unique_dates.tail(holdout_days))
    holdout_start = unique_dates.iloc[-holdout_days]

    # Временной порядок важен: будущие продажи не должны попадать в обучение,
    # иначе качество прогноза будет оценено слишком оптимистично.
    train = ordered[ordered[date_col] < holdout_start].copy()
    holdout = ordered[ordered[date_col].isin(holdout_dates)].copy()
    return train, holdout


def make_time_splits(
    df: pd.DataFrame,
    date_col: str,
    n_splits: int,
    horizon_days: int,
) -> list[dict[str, pd.Timestamp]]:
    """Создает последовательные rolling-сплиты без случайного перемешивания строк."""
    _validate_date_column(df, date_col)
    if n_splits <= 0:
        raise ValueError("n_splits должен быть положительным.")
    if horizon_days <= 0:
        raise ValueError("horizon_days должен быть положительным.")

    ordered = _sorted_by_date(df, date_col)
    unique_dates = pd.Series(ordered[date_col].drop_duplicates()).sort_values().reset_index(drop=True)
    min_required_dates = n_splits * horizon_days + 1
    if len(unique_dates) < min_required_dates:
        raise ValueError("Недостаточно дат для заданного числа сплитов и горизонта.")

    splits: list[dict[str, pd.Timestamp]] = []
    first_valid_start_idx = len(unique_dates) - n_splits * horizon_days

    for split_number in range(n_splits):
        valid_start_idx = first_valid_start_idx + split_number * horizon_days
        valid_end_idx = valid_start_idx + horizon_days - 1
        train_end_idx = valid_start_idx - 1
        splits.append(
            {
                "split": split_number + 1,
                "train_start": unique_dates.iloc[0],
                "train_end": unique_dates.iloc[train_end_idx],
                "valid_start": unique_dates.iloc[valid_start_idx],
                "valid_end": unique_dates.iloc[valid_end_idx],
            }
        )

    return splits


def split_by_fold(frame: pd.DataFrame, fold: dict[str, pd.Timestamp], date_column: str = "sales_date"):
    """Возвращает train/valid для заранее заданных временных границ."""
    _validate_date_column(frame, date_column)
    dates = pd.to_datetime(frame[date_column])
    train_mask = (dates >= fold["train_start"]) & (dates <= fold["train_end"])
    valid_mask = (dates >= fold["valid_start"]) & (dates <= fold["valid_end"])
    return frame.loc[train_mask].copy(), frame.loc[valid_mask].copy()


def make_time_series_folds(
    dates: pd.Series,
    validation_size: int,
    n_folds: int,
    gap: int = 0,
) -> list[dict[str, pd.Timestamp]]:
    """Совместимый helper для старых вызовов: строит последовательные временные окна."""
    frame = pd.DataFrame({"sales_date": pd.to_datetime(dates)})
    splits = make_time_splits(frame, "sales_date", n_folds, validation_size)
    if gap == 0:
        return splits

    adjusted = []
    unique_dates = pd.Series(frame["sales_date"].drop_duplicates()).sort_values().reset_index(drop=True)
    for split in splits:
        train_end_position = unique_dates[unique_dates == split["valid_start"]].index[0] - gap - 1
        if train_end_position < 0:
            raise ValueError("Недостаточно истории для заданного gap.")
        copy = dict(split)
        copy["train_end"] = unique_dates.iloc[train_end_position]
        adjusted.append(copy)
    return adjusted
