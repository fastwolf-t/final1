from pathlib import Path

import pandas as pd
import pytest

import reports


@pytest.fixture(autouse=True)
def _use_tmp_dir(in_tmp_dir: Path) -> None:
    """Все отчёты в этом файле пишутся во временную папку"""


def test_spending_by_category(transactions: pd.DataFrame) -> None:
    result = reports.spending_by_category(
        transactions, "супермаркеты", "2021-03-31"
    )
    assert list(result["Описание"]) == ["Колхоз", "Магнит"]
    assert list(result["Расходы"]) == [500.0, 250.0]
    assert Path("report/spending_by_category.xlsx").exists()


def test_spending_by_category_without_date(
    transactions: pd.DataFrame,
) -> None:
    # без даты берётся самая поздняя операция (09.03.2021)
    result = reports.spending_by_category(transactions, "Супермаркеты")
    assert len(result) == 2


def test_spending_by_category_bad_date(transactions: pd.DataFrame) -> None:
    result = reports.spending_by_category(
        transactions, "Супермаркеты", "не дата"
    )
    assert result.empty


def test_spending_by_weekday(transactions: pd.DataFrame) -> None:
    result = reports.average_spending_by_weekday(transactions, "2021-03-31")
    assert list(result.columns) == ["День недели", "Валюта", "Средние расходы"]
    found = {
        (row["День недели"], row["Валюта"]): row["Средние расходы"]
        for _, row in result.iterrows()
    }
    assert found == {
        ("Вторник", "USD"): 20.0,
        ("Пятница", "RUB"): 500.0,
        ("Суббота", "RUB"): 250.0,
        ("Воскресенье", "RUB"): 1000.0,
    }
    assert Path("report/spending_by_weekday.xlsx").exists()


def test_spending_by_weekday_empty(transactions: pd.DataFrame) -> None:
    assert reports.average_spending_by_weekday(
        transactions, "2019-01-01"
    ).empty
    assert reports.average_spending_by_weekday(transactions, "не дата").empty


def test_spending_by_day_type(transactions: pd.DataFrame) -> None:
    result = reports.average_spending_by_day_type(transactions, "2021-03-31")
    found = {
        (row["Тип дня"], row["Валюта"]): row["Средние расходы"]
        for _, row in result.iterrows()
    }
    assert found == {
        ("Рабочий день", "RUB"): 500.0,
        ("Рабочий день", "USD"): 20.0,
        ("Выходной день", "RUB"): 625.0,
    }
    assert Path("report/spending_by_day_type.xlsx").exists()


def test_spending_by_day_type_empty(transactions: pd.DataFrame) -> None:
    assert reports.average_spending_by_day_type(transactions, "2019-01-01").empty
    assert reports.average_spending_by_day_type(transactions, "не дата").empty


def test_save_report_skips_non_dataframe(in_tmp_dir: Path) -> None:
    @reports.save_report("report/x.xlsx")
    def not_a_table() -> int:
        return 5

    assert not_a_table() == 5
    assert not Path("report/x.xlsx").exists()
