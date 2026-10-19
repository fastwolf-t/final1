import os
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
import requests


@pytest.fixture
def transactions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Дата операции": [
                "05.03.2021 12:00:00",
                "06.03.2021 13:00:00",
                "07.03.2021 14:00:00",
                "08.03.2021 15:00:00",
                "09.03.2021 16:00:00",
                "01.10.2020 10:00:00",
            ],
            "Номер карты": [
                "*7197",
                "*7197",
                "*5091",
                "*5091",
                "*5091",
                "*7197",
            ],
            "Сумма платежа": [-500.0, -250.0, -1000.0, 3000.0, -20.0, -100.0],
            "Валюта платежа": ["RUB", "RUB", "RUB", "RUB", "USD", "RUB"],
            "Сумма операции": [-500.0, -250.0, -1000.0, 3000.0, -20.0, -100.0],
            "Валюта операции": ["RUB", "RUB", "RUB", "RUB", "USD", "RUB"],
            "Категория": [
                "Супермаркеты",
                "Супермаркеты",
                "Переводы",
                "Пополнения",
                "Фастфуд",
                "Супермаркеты",
            ],
            "Описание": [
                "Колхоз",
                "Магнит",
                "Валерий А.",
                "Зарплата",
                "Burger",
                "Старый магазин",
            ],
        }
    )


@pytest.fixture
def in_tmp_dir(tmp_path: Path) -> Iterator[Path]:
    old_dir = Path.cwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(old_dir)


@pytest.fixture(autouse=True)
def no_network() -> Iterator[None]:
    with patch(
        "requests.sessions.Session.request",
        side_effect=requests.ConnectionError("no network in tests"),
    ):
        yield