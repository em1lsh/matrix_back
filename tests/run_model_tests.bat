@echo off
REM Скрипт для запуска тестов моделей с очисткой БД

cd %~dp0\..\project

echo Cleaning test data...
set ENV=test
poetry run python ../tests/clean_all_test_data.py

echo.
echo Running model tests...
poetry run pytest ../tests/test_models_complete.py -v

echo.
echo Cleaning test data after tests...
poetry run python ../tests/clean_all_test_data.py
