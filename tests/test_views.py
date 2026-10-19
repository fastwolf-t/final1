import json
from typing import Any

import pandas as pd
import pytest
import requests

import views


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


class FakeResponse:
    def __init__(self, data: Any = None, error: bool = False) -> None:
        self._data = data
        self._error = error

    def raise_for_status(self) -> None:
        if self._error:
            raise requests.RequestException("boom")

    def json(self) -> Any:
        return self._data


def test_get_stock_prices(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = {
        "AAPL": FakeResponse(
            {"chart": {"result": [{"meta": {"regularMarketPrice": 150.456}}]}}
        ),
        "EMPTY": FakeResponse({"chart": {"result": []}}),
        "NOPRICE": FakeResponse({"chart": {"result": [{"meta": {}}]}}),
        "BROKEN": FakeResponse({"oops": 1}),
        "DOWN": FakeResponse(error=True),
    }

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        return answers[url.rsplit("/", 1)[1]]

    monkeypatch.setattr(views.requests, "get", fake_get)

    result = views.get_stock_prices(
        ["aapl.US", "EMPTY", "NOPRICE", "BROKEN", "DOWN"]
    )
    assert [r["price"] for r in result] == [150.46, None, None, None, None]
    assert result[0]["stock"] == "aapl.US"


@pytest.fixture
def fake_outside(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        views,
        "load_settings",
        lambda: {"user_currencies": ["USD"], "user_stocks": ["AAPL"]},
    )
    monkeypatch.setattr(
        views,
        "get_currency_rates",
        lambda cur: [{"currency": c, "rate": 90.0} for c in cur],
    )
    monkeypatch.setattr(
        views,
        "get_stock_prices",
        lambda st: [{"stock": s, "price": 1.0} for s in st],
    )


def test_home_page(transactions: pd.DataFrame, fake_outside: None) -> None:
    result = json.loads(views.home_page("2021-03-31 12:00:00", transactions))

    assert result["greeting"] == "Добрый день"
    assert result["cards"] == [
        {"last_digits": "5091", "total_spent": 1000.0, "cashback": 10.0},
        {"last_digits": "5091", "total_spent": 20.0, "cashback": 0.0},
        {"last_digits": "7197", "total_spent": 750.0, "cashback": 7.0},
    ]
    top = result["top_transactions"]
    assert len(top) == 5  # старая операция не попала
    assert top[0] == {
        "date": "08.03.2021",
        "amount": 3000.0,
        "category": "Пополнения",
        "description": "Зарплата",
    }
    assert result["currency_rates"] == [{"currency": "USD", "rate": 90.0}]
    assert result["stock_prices"] == [{"stock": "AAPL", "price": 1.0}]


def test_home_page_without_settings(
    transactions: pd.DataFrame,
    fake_outside: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken() -> dict[str, Any]:
        raise OSError("no file")

    monkeypatch.setattr(views, "load_settings", broken)
    result = json.loads(views.home_page("2021-03-31 23:30:00", transactions))
    assert result["greeting"] == "Доброй ночи"
    assert result["currency_rates"] == []
    assert result["stock_prices"] == []
