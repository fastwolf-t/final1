import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pandas as pd
import pytest
import requests

import utils


def make_response(data: Any = None, error: bool = False) -> Mock:
    response = Mock()
    response.json.return_value = data
    if error:
        response.raise_for_status.side_effect = requests.RequestException(
            "boom"
        )
    return response


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


def test_rates_from_main_site() -> None:
    data = {
        "Valute": {
            "USD": {"Value": 90.0, "Nominal": 1},
            "JPY": {"Value": 60.0, "Nominal": 100},
        }
    }
    with patch.object(
        utils.requests, "get", side_effect=[make_response(data)]
    ):
        result = utils.get_currency_rates(["usd", "JPY", "RUB", "XXX"])
    assert result == [
        {"currency": "USD", "rate": 90.0},
        {"currency": "JPY", "rate": 0.6},
        {"currency": "RUB", "rate": 1.0},
        {"currency": "XXX", "rate": None},
    ]


def test_rates_from_backup_site() -> None:
    backup = {"rates": {"USD": 0.01, "ZERO": 0}}
    answers = [make_response(error=True), make_response(backup)]
    with patch.object(utils.requests, "get", side_effect=answers):
        result = utils.get_currency_rates(["USD", "ZERO"])
    assert result == [
        {"currency": "USD", "rate": 100.0},
        {"currency": "ZERO", "rate": None},
    ]


def test_rates_both_sites_down() -> None:
    answers = [make_response(error=True), make_response(error=True)]
    with patch.object(utils.requests, "get", side_effect=answers):
        result = utils.get_currency_rates(["USD", "rub"])
    assert result == [
        {"currency": "USD", "rate": None},
        {"currency": "RUB", "rate": 1.0},
    ]


def test_rates_broken_currency_data() -> None:
    data = {
        "Valute": {
            "USD": {"Value": 90.0},
            "EUR": {"Value": 1, "Nominal": 0},
        }
    }
    with patch.object(
        utils.requests, "get", side_effect=[make_response(data)]
    ):
        result = utils.get_currency_rates(["USD", "EUR"])
    assert [r["rate"] for r in result] == [None, None]