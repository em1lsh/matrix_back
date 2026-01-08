@echo off
REM Quick UoW performance test (1 minute)

echo ================================================================================
echo Quick UoW Performance Test
echo ================================================================================
echo.

REM Создание/обновление тестового пользователя и токена
echo Step 1: Creating/refreshing test user token...
echo.
cd ..\..
poetry run python tests/load/create_test_user.py
if errorlevel 1 (
    echo ERROR: Failed to create test user
    pause
    exit /b 1
)

echo.
echo Step 2: Running load test (20 users, 1 minute)...
echo.

REM Создание директории для результатов
if not exist "tests\load\results\uow" mkdir tests\load\results\uow

poetry run locust -f tests/load/locustfile_uow.py ^
    --headless ^
    --users=20 ^
    --spawn-rate=5 ^
    --run-time=1m ^
    --host=http://127.0.0.1:8000 ^
    --html=tests/load/results/uow/quick_report.html ^
    --csv=tests/load/results/uow/quick_stats

echo.
echo ================================================================================
echo Test completed!
echo ================================================================================
echo.
echo Report: tests\load\results\uow\quick_report.html
echo.

REM Открыть отчет в браузере
start tests\load\results\uow\quick_report.html

pause
