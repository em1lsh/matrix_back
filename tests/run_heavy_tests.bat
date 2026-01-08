@echo off
REM Скрипт для запуска тестов тяжелых эндпоинтов
REM Использование: run_heavy_tests.bat [options]

echo ========================================
echo HEAVY ENDPOINTS TESTS
echo ========================================
echo.

REM Проверка что мы в правильной директории
if not exist "pyproject.toml" (
    echo ERROR: pyproject.toml not found!
    echo Please run this script from backend/ directory
    exit /b 1
)

REM Проверка что тестовая БД настроена
if not exist ".env.test" (
    echo WARNING: .env.test not found!
    echo Please create .env.test with test database configuration
    pause
)

echo Running tests...
echo.

REM Запуск тестов
poetry run pytest tests/test_heavy_endpoints.py -v %*

echo.
echo ========================================
echo Tests completed!
echo ========================================
