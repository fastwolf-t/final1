import json
from pathlib import Path
from typing import Any

import pandas as pd
import requests


def load_operations(file_path: str | Path) -> pd.DataFrame:
    """Загружает банковские операции из Excel-файла"""
    return pd.read_excel(file_path)


def load_settings(
    file_path: str | Path = "user_settings.json",
) -> dict[str, Any]:
    """Загружает настройки проекта из JSON-файла"""
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_currency_rates(currencies: list[str]) -> list[dict[str, Any]]:
    """Получает курсы валют к рублю"""
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        available_rates = response.json()["Valute"]
    except requests.RequestException, ValueError, KeyError, TypeError:
        try:
            response = requests.get(
                "https://www.cbr-xml-daily.com/latest.js", timeout=15
            )
            response.raise_for_status()
            inverse_rates = response.json()["rates"]
            available_rates = {}

            for currency, inverse_rate in inverse_rates.items():
                if inverse_rate:
                    available_rates[currency] = {
                        "Value": 1 / float(inverse_rate),
                        "Nominal": 1,
                    }
        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError,
            ZeroDivisionError,
        ):
            return [
                {
                    "currency": currency.upper(),
                    "rate": 1.0 if currency.upper() == "RUB" else None,
                }
                for currency in currencies
            ]
    result = []
    for currency in currencies:
        code = currency.upper()

        if code == "RUB":
            result.append({"currency": code, "rate": 1.0})
            continue
        currency_data = available_rates.get(code)

        if currency_data is None:
            rate = None
        else:
            try:
                value = float(currency_data["Value"])
                nominal = float(currency_data["Nominal"])
                rate = round(value / nominal, 4) if nominal > 0 else None
            except KeyError, TypeError, ValueError, ZeroDivisionError:
                rate = None

        result.append({"currency": code, "rate": rate})

    return result
