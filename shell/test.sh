# runs test in console
poetry run pytest -v

# generates feedback on tests in htmlcov/ folder
poetry run pytest --cov=src --cov-report=html