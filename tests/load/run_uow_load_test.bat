@echo off
REM Quick load test for UoW performance

echo ================================================================================
echo UoW Load Test
echo ================================================================================
echo.

REM Проверка что приложение запущено
echo Checking if application is running...
curl -s http://localhost:8000/docs > nul 2>&1
if errorlevel 1 (
    echo ERROR: Application is not running on http://localhost:8000
    echo Please start the application first:
    echo   cd backend
    echo   poetry run uvicorn project.app.main:app --reload
    pause
    exit /b 1
)
echo ✓ Application is running
echo.

REM Создание директории для результатов
if not exist "tests\load\results\uow" mkdir tests\load\results\uow

echo ================================================================================
echo Test 1: Light Load (10 users, 2 min)
echo ================================================================================
echo.

poetry run locust -f tests/load/locustfile_uow.py ^
    --headless ^
    --users=10 ^
    --spawn-rate=2 ^
    --run-time=2m ^
    --host=http://localhost:8000 ^
    --html=tests/load/results/uow/report_10users.html ^
    --csv=tests/load/results/uow/stats_10users

echo.
echo ================================================================================
echo Test 2: Medium Load (50 users, 3 min)
echo ================================================================================
echo.

poetry run locust -f tests/load/locustfile_uow.py ^
    --headless ^
    --users=50 ^
    --spawn-rate=5 ^
    --run-time=3m ^
    --host=http://localhost:8000 ^
    --html=tests/load/results/uow/report_50users.html ^
    --csv=tests/load/results/uow/stats_50users

echo.
echo ================================================================================
echo Test 3: High Load (100 users, 3 min)
echo ================================================================================
echo.

poetry run locust -f tests/load/locustfile_uow.py ^
    --headless ^
    --users=100 ^
    --spawn-rate=10 ^
    --run-time=3m ^
    --host=http://localhost:8000 ^
    --html=tests/load/results/uow/report_100users.html ^
    --csv=tests/load/results/uow/stats_100users

echo.
echo ================================================================================
echo Results saved to: tests\load\results\uow\
echo ================================================================================
echo.
echo Open reports:
echo   tests\load\results\uow\report_10users.html
echo   tests\load\results\uow\report_50users.html
echo   tests\load\results\uow\report_100users.html
echo.

pause
