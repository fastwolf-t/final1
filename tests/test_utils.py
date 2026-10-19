import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import requests

import utils


class FakeResponse:
    def __init__(self, data: Any = None, error: bool = False) -> None:
        self._data = data
        self._error = error

    def raise_for_status(self) -> None:
        if self._error:
            raise requests.RequestException("boom")

    def json(self) -> Any:
        return self._data


def fake_get(*responses: FakeResponse) -> Any:
    """Отдаёт ответы по очереди: первый вызов — первый ответ и т.д."""

    queue = list(responses)

    def get(*args: Any, **kwargs: Any) -> FakeResponse:
        return queue.pop(0)

    return get


def test_load_operations(tmp_path: Path) -> None:
    path = tmp_path / "ops.xlsx"
    pd.DataFrame({"a": [1, 2]}).to_excel(path, index=False)
    assert list(utils.load_operations(path)["a"]) == [1, 2]


def test_load_settings(tmp_path: Path) -> None:
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"user_currencies": ["USD"]}))
    assert utils.load_settings(path) == {"user_currencies": ["USD"]}


def test_load_settings_missing_file(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        utils.load_settings(tmp_path / "nope.json")


def test_rates_from_main_site(monkeypatch: pytest.MonkeyPatch) -> None:
    data = {
        "Valute": {
            "USD": {"Value": 90.0, "Nominal": 1},
            "JPY": {"Value": 60.0, "Nominal": 100},
        }
    }
    monkeypatch.setattr(utils.requests, "get", fake_get(FakeResponse(data)))
    result = utils.get_currency_rates(["usd", "JPY", "RUB", "XXX"])
    assert result == [
        {"currency": "USD", "rate": 90.0},
        {"currency": "JPY", "rate": 0.6},
        {"currency": "RUB", "rate": 1.0},
        {"currency": "XXX", "rate": None},
    ]


def test_rates_from_backup_site(monkeypatch: pytest.MonkeyPatch) -> None:
    backup = {"rates": {"USD": 0.01, "ZERO": 0}}
    monkeypatch.setattr(
        utils.requests,
        "get",
        fake_get(FakeResponse(error=True), FakeResponse(backup)),
    )
    result = utils.get_currency_rates(["USD", "ZERO"])
    assert result == [
        {"currency": "USD", "rate": 100.0},
        {"currency": "ZERO", "rate": None},
    ]


def test_rates_both_sites_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        utils.requests,
        "get",
        fake_get(FakeResponse(error=True), FakeResponse(error=True)),
    )
    result = utils.get_currency_rates(["USD", "rub"])
    assert result == [
        {"currency": "USD", "rate": None},
        {"currency": "RUB", "rate": 1.0},
    ]


def test_rates_broken_currency_data(monkeypatch: pytest.MonkeyPatch) -> None:
    data = {
        "Valute": {"USD": {"Value": 90.0}, "EUR": {"Value": 1, "Nominal": 0}}
    }
    monkeypatch.setattr(utils.requests, "get", fake_get(FakeResponse(data)))
    result = utils.get_currency_rates(["USD", "EUR"])
    assert [r["rate"] for r in result] == [None, None]
