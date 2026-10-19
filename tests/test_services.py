from typing import Any

import pandas as pd
import pytest

import services

# ---------- simple_search ----------


@pytest.fixture
def search_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Описание": ["Колхоз", "Пятёрочка", "Валерий А.", None],
            "Категория": [
                "Супермаркеты",
                "Супермаркеты",
                "Переводы",
                "Кафе (тест)",
            ],
        }
    )


def test_simple_search_empty_query_returns_all(
    search_df: pd.DataFrame,
) -> None:
    assert len(services.simple_search(search_df, "")) == 4


def test_simple_search_by_description_case_insensitive(
    search_df: pd.DataFrame,
) -> None:
    result = services.simple_search(search_df, "пЯтёРоЧка")
    assert [r["Описание"] for r in result] == ["Пятёрочка"]


def test_simple_search_by_category(search_df: pd.DataFrame) -> None:
    result = services.simple_search(search_df, "переводы")
    assert [r["Описание"] for r in result] == ["Валерий А."]


def test_simple_search_special_chars_are_literal(
    search_df: pd.DataFrame,
) -> None:
    # regex=False, so "(" must not raise and must match literally
    result = services.simple_search(search_df, "(тест)")
    assert len(result) == 1


def test_simple_search_no_match(search_df: pd.DataFrame) -> None:
    assert services.simple_search(search_df, "нет такого") == []


# ---------- investment_bank ----------


@pytest.fixture(autouse=True)
def fake_rates(monkeypatch: pytest.MonkeyPatch) -> None:
    rates: dict[str, float | None] = {"USD": 90.0, "XXX": None}

    def fake(currencies: list[str]) -> list[dict[str, Any]]:
        return [{"currency": c, "rate": rates.get(c)} for c in currencies]

    monkeypatch.setattr(services, "get_currency_rates", fake)


def test_investment_bank_rub_rounding() -> None:
    transactions = [
        {
            "Дата операции": "01.12.2021 10:00:00",
            "Сумма операции": -1712.0,
            "Валюта операции": "RUB",
        },
        {
            "Дата операции": "02.12.2021 10:00:00",
            "Сумма операции": -100.0,
            "Валюта операции": "RUB",
        },
    ]
    assert services.investment_bank("2021-12", transactions, 50) == 38.0


def test_investment_bank_ignores_income_and_other_months() -> None:
    transactions = [
        {
            "Дата операции": "01.12.2021 10:00:00",
            "Сумма операции": 1712.0,
            "Валюта операции": "RUB",
        },
        {
            "Дата операции": "01.11.2021 10:00:00",
            "Сумма операции": -1712.0,
            "Валюта операции": "RUB",
        },
    ]
    assert services.investment_bank("2021-12", transactions, 50) == 0.0


def test_investment_bank_foreign_currency() -> None:
    transactions = [
        {
            "Дата операции": "01.12.2021 10:00:00",
            "Сумма операции": -10.5,
            "Валюта операции": "usd",
        },
    ]
    # 10.5 * 90 = 945 -> 1000, diff 55
    assert services.investment_bank("2021-12", transactions, 100) == 55.0


def test_investment_bank_skips_unknown_rate_and_bad_data() -> None:
    transactions: list[dict[str, Any]] = [
        {
            "Дата операции": "01.12.2021 10:00:00",
            "Сумма операции": -10.0,
            "Валюта операции": "XXX",
        },
        {
            "Дата операции": "01.12.2021 10:00:00",
            "Сумма операции": "abc",
            "Валюта операции": "RUB",
        },
        {
            "Дата операции": "01.12.2021 10:00:00",
            "Сумма операции": float("nan"),
            "Валюта операции": "RUB",
        },
        {
            "Дата операции": "не дата",
            "Сумма операции": -10.0,
            "Валюта операции": "RUB",
        },
        {
            "Дата операции": None,
            "Сумма операции": -10.0,
            "Валюта операции": "RUB",
        },
    ]
    assert services.investment_bank("2021-12", transactions, 50) == 0.0


def test_investment_bank_default_currency_is_rub() -> None:
    transactions = [
        {"Дата операции": "01.12.2021 10:00:00", "Сумма операции": -1712.0},
    ]
    assert services.investment_bank("2021-12", transactions, 50) == 38.0


@pytest.mark.parametrize("limit", [0, -10])
def test_investment_bank_invalid_limit(limit: int) -> None:
    with pytest.raises(ValueError):
        services.investment_bank("2021-12", [], limit)


# ---------- find_person_transfers ----------


def test_find_person_transfers() -> None:
    df = pd.DataFrame(
        {
            "Категория": ["Переводы", "Переводы", "Супермаркеты", "переводы"],
            "Описание": [
                "Валерий А.",
                "Магазин Ромашка",
                "Сергей Л.",
                "Анна К.",
            ],
        }
    )
    result = services.find_person_transfers(df)
    assert [r["Описание"] for r in result] == ["Валерий А.", "Анна К."]


def test_find_person_transfers_empty() -> None:
    df = pd.DataFrame({"Категория": ["Кафе"], "Описание": ["Кофе"]})
    assert services.find_person_transfers(df) == []


# ---------- find_phone_numbers ----------


@pytest.mark.parametrize(
    "description",
    [
        "Я МТС +7 921 111-22-33",
        "Тинькофф Мобайл +79211112233",
        "Звонок 8 (999) 123-45-67",
        "8-999-123-45-67",
    ],
)
def test_find_phone_numbers_matches(description: str) -> None:
    df = pd.DataFrame({"Описание": [description]})
    assert len(services.find_phone_numbers(df)) == 1


@pytest.mark.parametrize(
    "description",
    ["Оплата 12345", "+7 921 111-22-334", "Пятёрочка", None],
)
def test_find_phone_numbers_no_match(description: str | None) -> None:
    df = pd.DataFrame({"Описание": [description]})
    assert services.find_phone_numbers(df) == []


# ---------- cashback_by_category ----------


@pytest.fixture
def cashback_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Дата операции": [
                "01.03.2021 00:00:00",
                "05.03.2021 00:00:00",
                "06.03.2021 00:00:00",
                "07.03.2021 00:00:00",
                "01.04.2021 00:00:00",
                "02.03.2021 00:00:00",
            ],
            "Сумма платежа": [
                -250.0,
                -199.99,
                -1000.0,
                500.0,
                -1000.0,
                -300.0,
            ],
            "Категория": ["Еда", "Еда", "Транспорт", "Еда", "Еда", "Еда"],
            "Валюта платежа": ["RUB", "RUB", "RUB", "RUB", "RUB", "USD"],
        }
    )


def test_cashback_by_category(cashback_df: pd.DataFrame) -> None:
    result = services.cashback_by_category(cashback_df, 2021, 3)
    assert result == {
        "Еда (RUB)": 3.0,  # 250//100 + 199.99//100
        "Транспорт (RUB)": 10.0,
        "Еда (USD)": 3.0,
    }


def test_cashback_by_category_empty_month(cashback_df: pd.DataFrame) -> None:
    assert services.cashback_by_category(cashback_df, 2020, 1) == {}
