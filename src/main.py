import json
from datetime import datetime

import pandas as pd

from reports import (
    average_spending_by_day_type,
    average_spending_by_weekday,
    spending_by_category,
)
from services import (
    cashback_by_category,
    find_person_transfers,
    find_phone_numbers,
    investment_bank,
    simple_search,
)
from utils import load_operations, load_settings
from views import home_page


def json_default(value):
    """Преобразует типы pandas в JSON"""

    if pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%d.%m.%Y")
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def print_json(title, data):
    """Выводит данные в формате JSON"""

    print(f"\n{title}")
    print(json.dumps(data, ensure_ascii=False, indent=2, default=json_default))


def short_transactions(transactions):
    """Оставляет первые три операции и основные поля"""

    fields = [
        "Дата операции",
        "Сумма платежа",
        "Валюта платежа",
        "Категория",
        "Описание",
    ]

    result = []

    for transaction in transactions[:3]:
        item = {}

        for field in fields:
            if field in transaction:
                item[field] = transaction[field]

        result.append(item)

    return result


def main():
    transactions = load_operations("data/operations.xlsx")
    dates = pd.to_datetime(
        transactions["Дата операции"],
        dayfirst=True,
        errors="coerce",
    ).dropna()

    if dates.empty:
        print("В файле нет операций с корректными датами")
        return

    current_date = dates.max()
    date_string = current_date.strftime("%Y-%m-%d %H:%M:%S")
    month_string = current_date.strftime("%Y-%m")

    try:
        settings = load_settings()
    except OSError, json.JSONDecodeError:
        settings = {}

    print_json(
        "ГЛАВНАЯ СТРАНИЦА",
        json.loads(home_page(date_string, transactions)),
    )

    print_json(
        "ПОИСК ОПЕРАЦИЙ",
        short_transactions(simple_search(transactions, "перевод")),
    )

    print_json(
        "ПЕРЕВОДЫ ФИЗИЧЕСКИМ ЛИЦАМ",
        short_transactions(find_person_transfers(transactions)),
    )

    print_json(
        "ОПЕРАЦИИ С НОМЕРАМИ ТЕЛЕФОНОВ",
        short_transactions(find_phone_numbers(transactions)),
    )

    cashback = cashback_by_category(
        transactions,
        current_date.year,
        current_date.month,
    )

    if isinstance(cashback, dict):
        cashback = dict(list(cashback.items())[:3])
    else:
        cashback = cashback[:3]

    print_json("КЕШБЭК ПО КАТЕГОРИЯМ", cashback)

    category_report = spending_by_category(
        transactions,
        "Супермаркеты",
        date_string,
    )

    print_json(
        "РАСХОДЫ ПО СУПЕРМАРКЕТАМ",
        category_report[["Дата операции", "Описание", "Расходы"]]
        .head(3)
        .to_dict(orient="records"),
    )

    print_json(
        "СРЕДНИЕ РАСХОДЫ ПО ДНЯМ НЕДЕЛИ",
        average_spending_by_weekday(
            transactions,
            date_string,
        )
        .head(3)
        .to_dict(orient="records"),
    )

    print_json(
        "СРЕДНИЕ РАСХОДЫ В БУДНИ И ВЫХОДНЫЕ",
        average_spending_by_day_type(
            transactions,
            date_string,
        )
        .head(3)
        .to_dict(orient="records"),
    )

    print_json(
        "ИНВЕСТКОПИЛКА",
        {
            "month": month_string,
            "rounding_limit": 100,
            "total": investment_bank(
                month_string,
                transactions.to_dict(orient="records"),
                100,
            ),
        },
    )

    print_json(
        "НАСТРОЙКИ ПОЛЬЗОВАТЕЛЯ",
        {
            "currencies": settings.get("user_currencies", []),
            "stocks": settings.get("user_stocks", []),
        },
    )


main()
