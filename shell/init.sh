mkdir src
mkdir tests
mkdir data

touch src/main.py
touch src/__init__,py
touch tests/__init__.py

poetry init

poetry env use python3
poetry env info

poetry add pandas openpyxl
poetry add --group dev flake8 black isort mypy
poetry add requests
poetry add --group dev pytest pytest-cov