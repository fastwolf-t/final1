import json
from typing import Any

import pandas as pd
import requests

from utils import get_currency_rates, load_settings


def get_greeting(hour: int) -> str:
    """Возвращает приветствие в зависимости от времени суток"""

    if 6 <= hour < 12:
        return "Доброе утро"
    if 12 <= hour < 18:
        return "Добрый день"
    if 18 <= hour < 23:
        return "Добрый вечер"

    return "Доброй ночи"


def get_stock_prices(stocks: list[str]) -> list[dict[str, Any]]:
    """Получает последние доступные цены акций через Yahoo Finance"""

    result = []

    for stock in stocks:
        symbol = stock.upper().replace(".US", "")

        try:
            response = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                params={"range": "1d", "interval": "1d"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            chart_result = data["chart"]["result"]

            if not chart_result:
                price = None
            else:
                price = chart_result[0]["meta"].get("regularMarketPrice")

                if price is not None:
                    price = round(float(price), 2)

        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError,
            IndexError,
        ):
            price = None

        result.append({"stock": stock, "price": price})

    return result


def home_page(date_time: str, transactions: pd.DataFrame) -> str:
    """Формирует данные главной страницы в JSON"""

    data = transactions.copy()
    data["Дата операции"] = pd.to_datetime(
        data["Дата операции"],
        dayfirst=True,
        errors="coerce",
    )

    target_date = pd.to_datetime(date_time)
    start_date = target_date.replace(day=1)

    data = data[
        (data["Дата операции"] >= start_date)
        & (data["Дата операции"] <= target_date)
    ].copy()

    cards = []
    card_data = data.dropna(subset=["Номер карты"])

    for card, group in card_data.groupby("Номер карты"):
        for currency, currency_group in group.groupby(
            "Валюта платежа",
            dropna=False,
        ):
            expenses = (
                currency_group.loc[
                    currency_group["Сумма платежа"] < 0,
                    "Сумма платежа",
                ]
                .abs()
                .sum()
            )

            cards.append(
                {
                    "last_digits": str(card)[-4:],
                    "total_spent": round(float(expenses), 2),
                    "cashback": float(int(expenses // 100)),
                }
            )

    top_data = data.copy()
    top_data["abs_amount"] = pd.to_numeric(
        top_data["Сумма платежа"],
        errors="coerce",
    ).abs()
    top_data = top_data.nlargest(5, "abs_amount")

    top_transactions = []

    for _, transaction in top_data.iterrows():
        operation_date = transaction["Дата операции"]
        amount = transaction["Сумма платежа"]

        top_transactions.append(
            {
                "date": (
                    operation_date.strftime("%d.%m.%Y")
                    if pd.notna(operation_date)
                    else None
                ),
                "amount": (
                    round(float(amount), 2) if pd.notna(amount) else None
                ),
                "category": transaction["Категория"],
                "description": transaction["Описание"],
            }
        )

    try:
        settings = load_settings()
    except OSError, json.JSONDecodeError:
        settings = {}

    currencies = settings.get("user_currencies", [])
    stocks = settings.get("user_stocks", [])

    result = {
        "greeting": get_greeting(target_date.hour),
        "cards": cards,
        "top_transactions": top_transactions,
        "currency_rates": get_currency_rates(currencies),
        "stock_prices": get_stock_prices(stocks),
    }

    return json.dumps(result, ensure_ascii=False, default=str)
