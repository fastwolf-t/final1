import json
from pathlib import Path
from typing import Any

import pandas as pd
import requests

MAIN_RATES_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
BACKUP_RATES_URL = "https://www.cbr-xml-daily.com/latest.js"


def load_operations(file_path: str | Path) -> pd.DataFrame:
    """Загружает банковские операции из Excel-файла"""

    return pd.read_excel(file_path)


def load_settings(
    file_path: str | Path = "user_settings.json",
) -> dict[str, Any]:
    """Загружает настройки проекта из JSON-файла"""

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def _fetch_main_rates() -> dict[str, Any]:
    """Берёт курсы с основного сайта ЦБ"""

    response = requests.get(MAIN_RATES_URL, timeout=15)
    response.raise_for_status()

    return response.json()["Valute"]


def _fetch_backup_rates() -> dict[str, Any]:
    """Берёт курсы с запасного сайта и приводит к формату основного"""

    response = requests.get(BACKUP_RATES_URL, timeout=15)
    response.raise_for_status()
    inverse_rates = response.json()["rates"]

    return {
        code: {"Value": 1 / float(inverse_rate), "Nominal": 1}
        for code, inverse_rate in inverse_rates.items()
        if inverse_rate
    }


def _load_available_rates() -> dict[str, Any] | None:
    """Возвращает курсы с любого доступного сайта или None"""

    try:
        return _fetch_main_rates()
    except requests.RequestException, ValueError, KeyError, TypeError:
        pass

    try:
        return _fetch_backup_rates()
    except (
        requests.RequestException,
        ValueError,
        KeyError,
        TypeError,
        ZeroDivisionError,
    ):
        return None


def _rate_to_rubles(
    code: str,
    available_rates: dict[str, Any],
) -> float | None:
    """Считает курс одной валюты к рублю"""

    currency_data = available_rates.get(code)

    if currency_data is None:
        return None

    try:
        value = float(currency_data["Value"])
        nominal = float(currency_data["Nominal"])
    except KeyError, TypeError, ValueError:
        return None

    return round(value / nominal, 4) if nominal > 0 else None


def get_currency_rates(currencies: list[str]) -> list[dict[str, Any]]:
    """Получает курсы валют к рублю"""

    available_rates = _load_available_rates()

    if available_rates is None:
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
        else:
            result.append(
                {
                    "currency": code,
                    "rate": _rate_to_rubles(code, available_rates),
                }
            )

    return result
