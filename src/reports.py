from functools import wraps
from pathlib import Path
from typing import Any

import pandas as pd


def save_report(file: str):
    """Сохраняет результат отчёта в Excel"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            if isinstance(result, pd.DataFrame):
                path = Path(file)
                path.parent.mkdir(parents=True, exist_ok=True)
                result.to_excel(path, index=False)

            return result

        return wrapper

    return decorator


def prepare_period(
    transactions: pd.DataFrame,
    date: str | None = None,
) -> tuple[pd.DataFrame, Any]:
    """Подготавливает операции за последние три месяца"""

    data = transactions.copy()
    data["Дата операции"] = pd.to_datetime(
        data["Дата операции"],
        format="mixed",
        dayfirst=True,
        errors="coerce",
    )

    if date is None:
        target_date = data["Дата операции"].max()
    else:
        target_date = pd.to_datetime(
            date,
            format="mixed",
            dayfirst=False,
            errors="coerce",
        )

    return data, target_date


@save_report("report/spending_by_category.xlsx")
def spending_by_category(
    transactions: pd.DataFrame,
    category: str,
    date: str | None = None,
) -> pd.DataFrame:
    """Возвращает расходы по категории за три месяца"""

    data, target_date = prepare_period(transactions, date)

    if pd.isna(target_date):
        return data.iloc[0:0].copy()

    start_date = target_date - pd.DateOffset(months=3)
    amounts = pd.to_numeric(data["Сумма платежа"], errors="coerce")

    data = data[
        (data["Дата операции"] >= start_date)
        & (data["Дата операции"] <= target_date)
        & (
            data["Категория"].astype("string").str.casefold()
            == category.casefold()
        )
        & (amounts < 0)
    ].copy()

    data["Расходы"] = pd.to_numeric(
        data["Сумма платежа"],
        errors="coerce",
    ).abs()

    return data


@save_report("report/spending_by_weekday.xlsx")
def average_spending_by_weekday(
    transactions: pd.DataFrame,
    date: str | None = None,
) -> pd.DataFrame:
    """Рассчитывает средние расходы по дням недели"""

    data, target_date = prepare_period(transactions, date)
    columns = ["День недели", "Валюта", "Средние расходы"]

    if pd.isna(target_date):
        return pd.DataFrame(columns=columns)

    start_date = target_date - pd.DateOffset(months=3)
    amounts = pd.to_numeric(data["Сумма платежа"], errors="coerce")

    data = data[
        (data["Дата операции"] >= start_date)
        & (data["Дата операции"] <= target_date)
        & (amounts < 0)
    ].copy()

    if data.empty:
        return pd.DataFrame(columns=columns)

    data["Расходы"] = pd.to_numeric(
        data["Сумма платежа"],
        errors="coerce",
    ).abs()
    data["Номер дня"] = data["Дата операции"].dt.weekday

    result = (
        data.groupby(["Номер дня", "Валюта платежа"])["Расходы"]
        .mean()
        .reset_index()
    )

    weekdays = [
        "Понедельник",
        "Вторник",
        "Среда",
        "Четверг",
        "Пятница",
        "Суббота",
        "Воскресенье",
    ]

    result["День недели"] = result["Номер дня"].map(
        dict(zip(range(7), weekdays))
    )
    result = result.rename(
        columns={
            "Валюта платежа": "Валюта",
            "Расходы": "Средние расходы",
        }
    )
    result["Средние расходы"] = result["Средние расходы"].round(2)

    return result[columns]


@save_report("report/spending_by_day_type.xlsx")
def average_spending_by_day_type(
    transactions: pd.DataFrame,
    date: str | None = None,
) -> pd.DataFrame:
    """Рассчитывает средние расходы в будни и выходные"""

    data, target_date = prepare_period(transactions, date)
    columns = ["Тип дня", "Валюта", "Средние расходы"]

    if pd.isna(target_date):
        return pd.DataFrame(columns=columns)

    start_date = target_date - pd.DateOffset(months=3)
    amounts = pd.to_numeric(data["Сумма платежа"], errors="coerce")

    data = data[
        (data["Дата операции"] >= start_date)
        & (data["Дата операции"] <= target_date)
        & (amounts < 0)
    ].copy()

    if data.empty:
        return pd.DataFrame(columns=columns)

    data["Расходы"] = pd.to_numeric(
        data["Сумма платежа"],
        errors="coerce",
    ).abs()
    data["Тип дня"] = "Рабочий день"
    data.loc[
        data["Дата операции"].dt.weekday >= 5,
        "Тип дня",
    ] = "Выходной день"

    result = (
        data.groupby(["Тип дня", "Валюта платежа"])["Расходы"]
        .mean()
        .reset_index()
    )

    result = result.rename(
        columns={
            "Валюта платежа": "Валюта",
            "Расходы": "Средние расходы",
        }
    )
    result["Средние расходы"] = result["Средние расходы"].round(2)

    return result[columns]
