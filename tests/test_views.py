import json
from collections.abc import Iterator
from typing import Any
from unittest.mock import Mock, patch

import pandas as pd
import pytest
import requests

import views


def make_response(data: Any = None, error: bool = False) -> Mock:
    response = Mock()
    response.json.return_value = data
    if error:
        response.raise_for_status.side_effect = requests.RequestException(
            "boom"
        )
    return response


@pytest.fixture
def fake_outside() -> Iterator[None]:
    with (
        patch.object(
            views,
            "load_settings",
            return_value={"user_currencies": ["USD"], "user_stocks": ["AAPL"]},
        ),
        patch.object(
            views,
            "get_currency_rates",
            side_effect=lambda cur: [
                {"currency": c, "rate": 90.0} for c in cur
            ],
        ),
        patch.object(
            views,
            "get_stock_prices",
            side_effect=lambda st: [{"stock": s, "price": 1.0} for s in st],
        ),
    ):
        yield


@pytest.mark.parametrize(
    ("hour", "expected"),
    [
        (5, "Доброй ночи"),
        (6, "Доброе утро"),
        (11, "Доброе утро"),
        (12, "Добрый день"),
        (17, "Добрый день"),
        (18, "Добрый вечер"),
        (22, "Добрый вечер"),
        (23, "Доброй ночи"),
        (0, "Доброй ночи"),
    ],
)
def test_get_greeting(hour: int, expected: str) -> None:
    assert views.get_greeting(hour) == expected


def test_get_stock_prices() -> None:
    answers = {
        "AAPL": make_response(
            {"chart": {"result": [{"meta": {"regularMarketPrice": 150.456}}]}}
        ),
        "EMPTY": make_response({"chart": {"result": []}}),
        "NOPRICE": make_response({"chart": {"result": [{"meta": {}}]}}),
        "BROKEN": make_response({"oops": 1}),
        "DOWN": make_response(error=True),
    }

    def fake_get(url: str, **kwargs: Any) -> Mock:
        return answers[url.rsplit("/", 1)[1]]

    with patch.object(views.requests, "get", side_effect=fake_get):
        result = views.get_stock_prices(
            ["aapl.US", "EMPTY", "NOPRICE", "BROKEN", "DOWN"]
        )

    assert [r["price"] for r in result] == [150.46, None, None, None, None]
    assert result[0]["stock"] == "aapl.US"


def test_home_page(transactions: pd.DataFrame, fake_outside: None) -> None:
    result = json.loads(views.home_page("2021-03-31 12:00:00", transactions))

    assert result["greeting"] == "Добрый день"
    assert result["cards"] == [
        {"last_digits": "5091", "total_spent": 1000.0, "cashback": 10.0},
        {"last_digits": "5091", "total_spent": 20.0, "cashback": 0.0},
        {"last_digits": "7197", "total_spent": 750.0, "cashback": 7.0},
    ]
    top = result["top_transactions"]
    assert len(top) == 5
    assert top[0] == {
        "date": "08.03.2021",
        "amount": 3000.0,
        "category": "Пополнения",
        "description": "Зарплата",
    }
    assert result["currency_rates"] == [{"currency": "USD", "rate": 90.0}]
    assert result["stock_prices"] == [{"stock": "AAPL", "price": 1.0}]


def test_home_page_without_settings(
    transactions: pd.DataFrame, fake_outside: None
) -> None:
    with patch.object(views, "load_settings", side_effect=OSError("no file")):
        result = json.loads(
            views.home_page("2021-03-31 23:30:00", transactions)
        )

    assert result["greeting"] == "Доброй ночи"
    assert result["currency_rates"] == []
    assert result["stock_prices"] == []