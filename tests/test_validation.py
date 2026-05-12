import pandas as pd
import pytest

from src.validation import make_time_splits, train_holdout_split


def sample_dates(days: int = 60) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sales_date": pd.date_range("2024-01-01", periods=days, freq="D"),
            "value": range(days),
        }
    )


def test_holdout_contains_last_28_days():
    frame = sample_dates(60)
    _, holdout = train_holdout_split(frame, "sales_date", holdout_days=28)
    expected_dates = set(frame["sales_date"].tail(28))

    assert set(holdout["sales_date"]) == expected_dates


def test_train_has_no_future_dates_relative_to_holdout():
    train, holdout = train_holdout_split(sample_dates(60), "sales_date", holdout_days=28)

    assert train["sales_date"].max() < holdout["sales_date"].min()


def test_rolling_splits_move_forward_in_time():
    splits = make_time_splits(sample_dates(80), "sales_date", n_splits=3, horizon_days=7)

    assert len(splits) == 3
    assert splits[0]["valid_end"] < splits[1]["valid_start"]
    assert splits[1]["valid_end"] < splits[2]["valid_start"]
    assert all(split["train_end"] < split["valid_start"] for split in splits)


def test_validation_is_deterministic_and_not_random():
    frame = sample_dates(80).sample(frac=1, random_state=42)
    first = make_time_splits(frame, "sales_date", n_splits=2, horizon_days=7)
    second = make_time_splits(frame, "sales_date", n_splits=2, horizon_days=7)

    assert first == second


def test_wrong_date_column_raises_clear_error():
    with pytest.raises(ValueError, match="нет колонки даты"):
        train_holdout_split(sample_dates(60), "wrong_date", holdout_days=28)

