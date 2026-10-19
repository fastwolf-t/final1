import math
from typing import Any

import pandas as pd

from utils import get_currency_rates

# фамилия/имя и инициал, например "Валерий А."
PERSON_PATTERN = r"^[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.$"

# российский номер: +7 921 111-22-33, 8 (921) 111 22 33 итд
PHONE_PATTERN = (
    r"(?<!\d)(?:\+7|8)[\s-]*"
    r"\(?\d{3}\)?[\s-]*"
    r"\d{3}[\s-]*\d{2}[\s-]*\d{2}(?!\d)"
)


def simple_search(
    transactions: pd.DataFrame,
    query: str,
) -> list[dict[Any, Any]]:
    """Ищет операции по описанию и категории"""

    if not query:
        return transactions.to_dict(orient="records")

    in_description = (
        transactions["Описание"]
        .astype("string")
        .str.contains(query, case=False, na=False, regex=False)
    )
    in_category = (
        transactions["Категория"]
        .astype("string")
        .str.contains(query, case=False, na=False, regex=False)
    )

    return transactions[in_description | in_category].to_dict(orient="records")


def _collect_currencies(transactions: list[dict[Any, Any]]) -> list[str]:
    """Собирает уникальные валюты операций (RUB, если валюта не указана)"""

    currencies: list[str] = []

    for transaction in transactions:
        currency = transaction.get("Валюта операции", "RUB")

        if isinstance(currency, str) and currency.upper() not in currencies:
            currencies.append(currency.upper())

    return currencies


def _get_rates(transactions: list[dict[Any, Any]]) -> dict[str, float]:
    """Возвращает курсы валют к рублю, найденные для операций"""

    rates_data = get_currency_rates(_collect_currencies(transactions))
    rates = {
        item["currency"]: item["rate"]
        for item in rates_data
        if item["rate"] is not None
    }
    rates["RUB"] = 1.0

    return rates


def _spent_in_rubles(
    transaction: dict[Any, Any],
    month: str,
    rates: dict[str, float],
) -> float | None:
    """Возвращает трату в рублях или None, если операция не подходит"""

    date = transaction.get("Дата операции")
    amount = transaction.get("Сумма операции", 0)
    currency = transaction.get("Валюта операции", "RUB")

    if date is None or pd.isna(amount) or not isinstance(currency, str):
        return None

    transaction_date = pd.to_datetime(date, dayfirst=True, errors="coerce")

    try:
        amount = float(amount)
    except TypeError, ValueError:
        return None

    if pd.isna(transaction_date):
        return None

    if transaction_date.strftime("%Y-%m") != month or amount >= 0:
        return None

    rate = rates.get(currency.upper())

    if rate is None:
        return None

    return abs(amount) * rate


def investment_bank(
    month: str,
    transactions: list[dict[Any, Any]],
    limit: int,
) -> float:
    """Рассчитывает округление покупок для инвесткопилки в рублях"""

    if limit <= 0:
        raise ValueError("Лимит округления не может быть отрицательным!")

    rates = _get_rates(transactions)
    total = 0.0

    for transaction in transactions:
        spent = _spent_in_rubles(transaction, month, rates)

        if spent is None:
            continue

        rounded = math.ceil(spent / limit) * limit
        total += rounded - spent

    return round(total, 2)


def find_person_transfers(
    transactions: pd.DataFrame,
) -> list[dict[Any, Any]]:
    """Ищет переводы физическим лицам"""

    is_transfer = (
        transactions["Категория"]
        .astype("string")
        .str.fullmatch("Переводы", case=False, na=False)
    )
    is_person = (
        transactions["Описание"]
        .astype("string")
        .str.contains(PERSON_PATTERN, case=False, na=False, regex=True)
    )

    return transactions[is_transfer & is_person].to_dict(orient="records")


def find_phone_numbers(
    transactions: pd.DataFrame,
) -> list[dict[Any, Any]]:
    """Находит операции с российскими номерами телефонов"""

    has_phone = (
        transactions["Описание"]
        .astype("string")
        .str.contains(PHONE_PATTERN, case=False, na=False, regex=True)
    )

    return transactions[has_phone].to_dict(orient="records")


def cashback_by_category(
    transactions: pd.DataFrame,
    year: int,
    month: int,
) -> dict[Any, float]:
    """Рассчитывает кешбэк по категориям и валютам за месяц"""

    dates = pd.to_datetime(
        transactions["Дата операции"],
        dayfirst=True,
        errors="coerce",
    )
    amounts = pd.to_numeric(transactions["Сумма платежа"], errors="coerce")

    data = transactions[
        (dates.dt.year == year) & (dates.dt.month == month) & (amounts < 0)
    ].copy()

    # 1 рубль кешбэка за каждые полные 100 потраченных
    data["Кешбэк"] = (
        pd.to_numeric(data["Сумма платежа"], errors="coerce").abs() // 100
    )

    grouped = (
        data.groupby(["Категория", "Валюта платежа"], dropna=False)["Кешбэк"]
        .sum()
        .reset_index()
    )

    return {
        f"{category} ({currency})": round(float(amount), 2)
        for category, currency, amount in zip(
            grouped["Категория"],
            grouped["Валюта платежа"],
            grouped["Кешбэк"],
        )
    }
